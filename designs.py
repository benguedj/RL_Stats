"""Designs de l'overlay, dessines avec Pillow (bords lisses, transparence par pixel).

Chaque design est une fonction render(state, k, hover) qui renvoie :
  - l'image RGBA,
  - le point d'ancrage (x, y) dans l'image,
  - les boutons {nom: (x0, y0, x1, y1)} en pixels de l'image.

Ancrage : pour les formes arrondies, c'est le centre de la jauge de boost ; pour
les formes droites, c'est le milieu du bas de l'image, place juste au-dessus ;
pour les formes verticales, c'est le milieu du bord droit, colle au bord de l'ecran.
`k` = echelle (1.0 sur un ecran 1440p).
"""

import math
import os
import random
import re
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

FONT_FILE = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "bahnschrift.ttf")
SS = 3  # sur-echantillonnage

PANEL = (11, 19, 34, 228)
PANEL_MID = (20, 31, 54, 228)
EDGE = (52, 70, 102, 255)
FG = (241, 245, 249, 255)
MUTED = (140, 152, 173, 255)
GREEN = (46, 230, 107, 255)
RED = (255, 77, 77, 255)
FLASH_WIN = (14, 84, 40, 235)
FLASH_LOSS = (100, 20, 20, 235)
BTN_GREEN = (21, 128, 61, 240)
BTN_RED = (185, 28, 28, 240)

AMBER = (245, 158, 11, 255)
GOLD = (250, 204, 21, 255)
SKY = (56, 189, 248, 255)


def _scaled(color, f, alpha):
    return tuple(round(c * f) for c in color[:3]) + (alpha,)


def set_colors(win, loss):
    """Couleurs des victoires / defaites choisies par le joueur (tuples RGB)."""
    global GREEN, RED, FLASH_WIN, FLASH_LOSS, BTN_GREEN, BTN_RED, CONFETTI, SHARDS
    GREEN, RED = tuple(win[:3]) + (255,), tuple(loss[:3]) + (255,)
    FLASH_WIN, FLASH_LOSS = _scaled(GREEN, 0.36, 235), _scaled(RED, 0.36, 235)
    BTN_GREEN, BTN_RED = _scaled(GREEN, 0.6, 240), _scaled(RED, 0.6, 240)
    CONFETTI = [GREEN, GOLD, FG, SKY, (167, 243, 208, 255)]
    SHARDS = [RED, _scaled(RED, 0.6, 255), (71, 85, 105, 255), (30, 41, 59, 255)]


BOLD = "SemiBold Condensed"
SEMI = "SemiBold SemiCondensed"

_fonts = {}


def font(px, style=BOLD):
    key = (px, style)
    if key not in _fonts:
        try:
            f = ImageFont.truetype(FONT_FILE, px)
            f.set_variation_by_name(style)
        except (OSError, ValueError):
            f = ImageFont.truetype("segoeuib.ttf", px)
        _fonts[key] = f
    return _fonts[key]


def text_img(parts, shear=0.18):
    """parts = [(texte, police, couleur, dy)] cote a cote -> image RGBA rognee au texte."""
    gap = parts[0][1].size // 5
    boxes = [f.getbbox(t) for t, f, _, _ in parts]
    w = sum(b[2] - b[0] for b in boxes) + gap * (len(parts) - 1)
    h = max(b[3] + dy for b, (_, _, _, dy) in zip(boxes, parts))
    extra = int(shear * h) + 8
    img = Image.new("RGBA", (w + 2 * extra, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = extra
    for (t, f, color, dy), b in zip(parts, boxes):
        d.text((x - b[0], dy + 4), t, font=f, fill=color)
        x += b[2] - b[0] + gap
    if shear:  # italique
        W, H = img.size
        img = img.transform((W, H), Image.AFFINE, (1, shear, -shear * H / 2, 0, 1, 0), Image.BICUBIC)
    # Rogne au contenu reel : le centrage se fait sur les glyphes, pas sur la boite de la police
    return img.crop(img.getbbox() or (0, 0, 1, 1))


_blurs = {}


def _blur_cached(shadow, radius):
    """Ombre floutee, gardee en cache : le flou est la partie la plus lente d'un rendu, et l'ombre ne
    change presque jamais d'un rendu a l'autre (survol, bandeaux, nouveaux matchs...)."""
    key = (shadow.size, radius, hash(shadow.getchannel("A").tobytes()))
    if key not in _blurs:
        if len(_blurs) > 40:
            _blurs.clear()
        _blurs[key] = shadow.filter(ImageFilter.GaussianBlur(radius))
    return _blurs[key]


def paste_center(base, img, center, angle=0):
    if angle:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    base.alpha_composite(img, (round(center[0] - img.width / 2), round(center[1] - img.height / 2)))


BUTTONS_W = 6 * 40 + 5 * 5 + 8  # largeur de la rangee de boutons a l'echelle 1


def draw_buttons(d, cx, y1, s):
    """Rangee de boutons centree sur cx, bas a y1 (pixels sur-echantillonnes)."""
    labels = [("+W", "w+", BTN_GREEN), ("-W", "w-", PANEL_MID), ("+L", "l+", BTN_RED),
              ("-L", "l-", PANEL_MID), ("", "menu", PANEL_MID), ("X", "quit", PANEL_MID)]
    bw, bh, gap, sl = 40 * s, 24 * s, 5 * s, 6 * s
    x = cx - (len(labels) * bw + (len(labels) - 1) * gap + 8 * s) / 2
    y0 = y1 - bh
    bf = font(round(13 * s), SEMI)
    buttons = {}
    for i, (label, key, fill) in enumerate(labels):
        if i in (2, 4):
            x += 4 * s
        d.polygon([(x + sl, y0), (x + bw, y0), (x + bw - sl, y1), (x, y1)], fill=fill, outline=EDGE,
                  width=max(1, round(1.2 * s)))
        if key == "menu":  # trois traits
            for dy in (-5, 0, 5):
                ly = (y0 + y1) / 2 + dy * s
                d.line([(x + bw / 2 - 7 * s, ly), (x + bw / 2 + 7 * s, ly)], fill=FG, width=max(1, round(2 * s)))
        else:
            bb = bf.getbbox(label)
            d.text((x + bw / 2 - (bb[0] + bb[2]) / 2, (y0 + y1) / 2 - (bb[1] + bb[3]) / 2), label, font=bf, fill=FG)
        buttons[key] = tuple(round(v / SS) for v in (x, y0, x + bw, y1))
        x += bw + gap
    return buttons


BUTTONS_H = 6 * 24 + 5 * 5 + 8  # hauteur de la colonne de boutons (formes verticales)


def draw_buttons_column(d, x0, cy, s):
    """Colonne de boutons centree sur cy, bord gauche a x0 (pixels sur-echantillonnes)."""
    labels = [("+W", "w+", BTN_GREEN), ("-W", "w-", PANEL_MID), ("+L", "l+", BTN_RED),
              ("-L", "l-", PANEL_MID), ("", "menu", PANEL_MID), ("X", "quit", PANEL_MID)]
    bw, bh, gap, sl = 40 * s, 24 * s, 5 * s, 6 * s
    y = cy - BUTTONS_H * s / 2
    bf = font(round(13 * s), SEMI)
    buttons = {}
    for i, (label, key, fill) in enumerate(labels):
        if i in (2, 4):
            y += 4 * s
        x, y1 = x0, y + bh
        d.polygon([(x + sl, y), (x + bw, y), (x + bw - sl, y1), (x, y1)], fill=fill, outline=EDGE,
                  width=max(1, round(1.2 * s)))
        if key == "menu":
            for dy in (-5, 0, 5):
                ly = (y + y1) / 2 + dy * s
                d.line([(x + bw / 2 - 7 * s, ly), (x + bw / 2 + 7 * s, ly)], fill=FG, width=max(1, round(2 * s)))
        else:
            bb = bf.getbbox(label)
            d.text((x + bw / 2 - (bb[0] + bb[2]) / 2, (y + y1) / 2 - (bb[1] + bb[3]) / 2), label, font=bf, fill=FG)
        buttons[key] = tuple(round(v / SS) for v in (x, y, x + bw, y1))
        y += bh + gap
    return buttons


def finish(img, k_w, k_h, opacity=1.0):
    out = img.convert("RGBa").resize((k_w, k_h), Image.LANCZOS).convert("RGBA")
    if opacity < 1:
        a = out.getchannel("A").point(lambda v: round(v * opacity))
        out.putalpha(a)
    return out


_CLOCK = re.compile(r"\d+(?::\d\d){1,2}$")  # chrono de session en fin de sous-titre ("12:34", "1:02:03")


def _stopwatch(size, color):
    """Petite icone de chronometre (cadran, bouton, aiguille), carree, de cote `size` pixels."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(1, round(size * 0.11))
    r = size * 0.36
    cx, cy = size / 2, size * 0.58
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    d.rectangle([cx - size * 0.09, cy - r - size * 0.17, cx + size * 0.09, cy - r - size * 0.05], fill=color)
    d.line([(cx, cy), (cx + r * 0.5, cy - r * 0.6)], fill=color, width=w)
    return img


def _sub_img(text, px, max_w=None):
    """Image du sous-titre ; un chrono en fin de texte est precede d'une icone de chronometre, pour
    qu'on comprenne que c'est le temps de session. Reduit la police jusqu'a tenir dans max_w."""
    while True:
        fnt = font(px, SEMI)
        m = _CLOCK.search(text)
        if m is None:
            img = text_img([(text, fnt, MUTED, 0)], shear=0)
        else:
            clock = text_img([(m.group(), fnt, MUTED, 0)], shear=0)
            pieces = [_stopwatch(round(clock.height * 1.35), FG), clock]
            prefix = text[:m.start()].strip()
            if prefix:
                pieces.insert(0, text_img([(prefix, fnt, MUTED, 0)], shear=0))
            gap = round(px * 0.3)
            img = Image.new("RGBA", (sum(i.width for i in pieces) + gap * (len(pieces) - 1),
                                     max(i.height for i in pieces)), (0, 0, 0, 0))
            x = 0
            for i in pieces:
                img.alpha_composite(i, (x, (img.height - i.height) // 2))
                x += i.width + gap
        if not max_w or img.width <= max_w or px <= 6:
            return img
        px -= 1


def _sub(img, state, px, center, opacity=1.0, max_w=None):
    """Sous-titre (mode, matchs ou chrono). Avec state["sub_slot"] (une liste), il n'est pas dessine :
    sa place et sa police y sont notees, et paste_sub l'ajoute ensuite. L'appli peut ainsi redessiner
    le chrono seul chaque seconde au lieu de tout l'overlay."""
    slot = state.get("sub_slot")
    if slot is not None:
        slot.append((px, max_w, center, opacity))
        return
    paste_center(img, _sub_img(state["sub"], px, max_w), center)


def paste_sub(base, slot, text):
    """Ajoute le sous-titre a un rendu fait avec state["sub_slot"] : meme place, meme police et meme
    lissage que dans le rendu complet (le texte est dessine en sur-echantillonne puis reduit sur une
    grille alignee sur celle du rendu). Renvoie une copie ; base sans emplacement = inchangee."""
    if not slot:
        return base
    px, max_w, (cx, cy), opacity = slot[0]
    t = _sub_img(text, px, max_w)
    x0, y0 = round(cx - t.width / 2), round(cy - t.height / 2)  # comme paste_center
    gx, gy = x0 - x0 % SS, y0 - y0 % SS
    w, h = math.ceil((x0 + t.width - gx) / SS), math.ceil((y0 + t.height - gy) / SS)
    patch = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    patch.alpha_composite(t, (x0 - gx, y0 - gy))
    out = base.copy()
    out.alpha_composite(finish(patch, w, h, opacity), (gx // SS, gy // SS))
    return out


def pct_of(state):
    total = state["w"] + state["l"]
    return (round(state["w"] * 100 / total) if total else 0), total


# --------------------------------------------------------------------------
# Tableau des scores, forme arrondie : arc autour du haut de la jauge de boost
# --------------------------------------------------------------------------

GAUGE_R = 172          # rayon exterieur de la jauge de boost, barres du haut comprises (1440p, interface a 100 %)
R_IN = GAUGE_R + 10
R_OUT = R_IN + 42
STRIP_IN = R_OUT + 5
STRIP_OUT = STRIP_IN + 19
A_LEFT, A_RIGHT = 145, 35
SECTORS = [(145, 109), (106, 74), (71, 35)]  # W, centre, L
STRIP_SPAN = (116, 64)
CTRL_H = 24


def _pt(cx, cy, r, a):
    a = math.radians(a)
    return cx + r * math.cos(a), cy - r * math.sin(a)


def _annulus(cx, cy, r0, r1, a0, a1):
    steps = max(8, int(abs(a0 - a1) * 2))
    outer = [_pt(cx, cy, r1, a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]
    inner = [_pt(cx, cy, r0, a1 + (a0 - a1) * i / steps) for i in range(steps + 1)]
    return outer + inner


def _arc_text(img, text, fnt, color, cx, cy, r, center=90):
    """Ecrit le texte le long d'un arc (lettre par lettre), centre sur l'angle `center`."""
    asc, desc = fnt.getmetrics()
    top = asc // 2  # marge pour les accents (É) qui depassent l'ascendante
    h = top + asc + desc
    # Image de hauteur fixe : toutes les lettres partagent la meme ligne de base.
    # On decale pour que le milieu des majuscules tombe sur r (le bas de l'image
    # pointe vers le centre de la jauge une fois tournee).
    caps_mid = top + (fnt.getbbox("E")[1] + asc) / 2
    r_img = r + (caps_mid - h / 2)
    advances = [fnt.getlength(ch) for ch in text]
    angle = center + math.degrees(sum(advances) / 2 / r)
    for ch, adv in zip(text, advances):
        mid = angle - math.degrees(adv / 2 / r)
        if ch.strip():
            g = Image.new("RGBA", (math.ceil(adv) + 4, h), (0, 0, 0, 0))
            ImageDraw.Draw(g).text((2, top), ch, font=fnt, fill=color)
            paste_center(img, g, _pt(cx, cy, r_img, mid), mid - 90)
        angle -= math.degrees(adv / r)


def _arc_text_span(text, fnt, r, pad, min_half):
    half = math.degrees((fnt.getlength(text) / 2 + pad) / r)
    half = max(min_half, half)
    return 90 + half, 90 - half


def _arc_canvas(k, r_out, strip_out, low_angle, r_in, pad=22):
    """Image pour un design arrondi. Renvoie (w_px, h_px, cx, cy) ; cy = centre de la jauge."""
    top = strip_out + pad + CTRL_H + 8                         # du centre de la jauge au haut de l'image
    bottom = r_in * math.sin(math.radians(low_angle)) - pad    # du centre de la jauge au bas de l'image
    w_px, h_px = round(2 * (r_out + pad) * k), round((top - bottom) * k)
    return w_px, h_px, w_px * SS / 2, top * k * SS


def _arc_strip(img, info, cx, cy, s, r_in, r_out, min_half):
    """Bandeau d'info courbe : s'allonge selon le texte, qui suit l'arc."""
    text, color, filled = info
    fnt = font(round(12 * s), SEMI)
    r_mid = (r_in + r_out) / 2 * s
    span = _arc_text_span(text, fnt, r_mid, 12 * s, min_half)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon(_annulus(cx, cy, r_in * s, (r_out + 6) * s, span[0] + 3, span[1] - 3),
                                   fill=(0, 0, 0, 150))
    img.alpha_composite(_blur_cached(shadow, 7 * s))
    ImageDraw.Draw(img).polygon(_annulus(cx, cy, r_in * s, r_out * s, *span), fill=color if filled else PANEL,
                                outline=None if filled else EDGE, width=max(1, round(1.2 * s)))
    _arc_text(img, text, fnt, PANEL[:3] + (255,) if filled else color, cx, cy, r_mid)


def render_arc(state, k, hover=False):
    s = k * SS
    w_px, h_px, cx, cy = _arc_canvas(k, R_OUT, STRIP_OUT, A_RIGHT, R_IN)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Ombre douce, comme celle de la jauge
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon(_annulus(cx, cy, (R_IN - 6) * s, (R_OUT + 8) * s, A_LEFT + 4, A_RIGHT - 4),
                                   fill=(0, 0, 0, 150))
    img.alpha_composite(_blur_cached(shadow, 9 * s))

    d = ImageDraw.Draw(img)
    flash = state.get("flash")
    fills = [FLASH_WIN if flash == "w" else PANEL, PANEL_MID, FLASH_LOSS if flash == "l" else PANEL]
    lw = max(1, round(1.2 * s))
    for (a0, a1), fill in zip(SECTORS, fills):
        d.polygon(_annulus(cx, cy, R_IN * s, R_OUT * s, a0, a1), fill=fill, outline=EDGE, width=lw)
    accent = 4
    d.polygon(_annulus(cx, cy, (R_OUT - accent) * s, R_OUT * s, *SECTORS[0]), fill=GREEN)
    d.polygon(_annulus(cx, cy, (R_OUT - accent) * s, R_OUT * s, *SECTORS[2]), fill=RED)

    # Chiffres centres dans la partie sombre (sous le lisere), legerement vers l'interieur
    r_text = (R_IN + R_OUT - accent) / 2 * s - 1 * s
    big, small = font(round(28 * s)), font(round(14 * s))
    win_col = GREEN if flash == "w" else FG
    loss_col = RED if flash == "l" else FG
    am = sum(SECTORS[0]) / 2
    paste_center(img, text_img([("W", small, GREEN, round(11 * s)), (str(state["w"]), big, win_col, 0)]),
                 _pt(cx, cy, r_text, am), am - 90)
    am = sum(SECTORS[2]) / 2
    paste_center(img, text_img([(str(state["l"]), big, loss_col, 0), ("L", small, RED, round(11 * s))]),
                 _pt(cx, cy, r_text, am), am - 90)

    pct, total = pct_of(state)
    top_y = cy - R_OUT * s
    paste_center(img, text_img([(f"{pct}%", font(round(21 * s)), FG, 0)]), (cx, top_y + 16 * s))
    _sub(img, state, round(10 * s), (cx, top_y + 32 * s))

    if state.get("info"):
        _arc_strip(img, state["info"], cx, cy, s, STRIP_IN, STRIP_OUT, (STRIP_SPAN[0] - STRIP_SPAN[1]) / 2)

    buttons = draw_buttons(d, cx, cy - (STRIP_OUT + 8) * s, s) if hover else {}
    return finish(img, w_px, h_px), (w_px / 2, cy / SS), buttons


# --------------------------------------------------------------------------
# Minimal, forme arrondie : fine bande courbe autour de la jauge
# --------------------------------------------------------------------------

MINI_R_IN = GAUGE_R + 10
MINI_R_OUT = MINI_R_IN + 30
MINI_SPAN = (128, 52)
MINI_STRIP_IN = MINI_R_OUT + 5
MINI_STRIP_OUT = MINI_STRIP_IN + 19


def _rounded_arc(d, cx, cy, r0, r1, a0, a1, fill):
    """Bande courbe aux extremites arrondies."""
    d.polygon(_annulus(cx, cy, r0, r1, a0, a1), fill=fill)
    rad = (r1 - r0) / 2
    for a in (a0, a1):
        px, py = _pt(cx, cy, (r0 + r1) / 2, a)
        d.ellipse([px - rad, py - rad, px + rad, py + rad], fill=fill)


def render_mini_arc(state, k, hover=False):
    s = k * SS
    end_r = (MINI_R_OUT - MINI_R_IN) / 2
    low = math.degrees(math.asin(max(0.0, (MINI_R_IN * math.sin(math.radians(MINI_SPAN[1])) - end_r) / MINI_R_IN)))
    w_px, h_px, cx, cy = _arc_canvas(k, MINI_R_OUT, MINI_STRIP_OUT, low, MINI_R_IN)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r0, r1 = MINI_R_IN * s, MINI_R_OUT * s
    a0, a1 = MINI_SPAN

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _rounded_arc(ImageDraw.Draw(shadow), cx, cy, r0 - 4 * s, r1 + 4 * s, a0, a1, (0, 0, 0, 140))
    img.alpha_composite(_blur_cached(shadow, 6 * s))

    d = ImageDraw.Draw(img)
    flash = state.get("flash")
    fill = FLASH_WIN if flash == "w" else FLASH_LOSS if flash == "l" else PANEL
    lw = max(1, round(1.2 * s))
    _rounded_arc(d, cx, cy, r0 - lw, r1 + lw, a0, a1, EDGE)  # contour
    _rounded_arc(d, cx, cy, r0, r1, a0, a1, fill)

    r_mid = (r0 + r1) / 2
    big = font(round(24 * s))
    for angle, value, color in ((a0 - 12, state["w"], GREEN), (a1 + 12, state["l"], RED)):
        paste_center(img, text_img([(str(value), big, color, 0)]), _pt(cx, cy, r_mid, angle), angle - 90)
    pct, _ = pct_of(state)
    paste_center(img, text_img([(f"{pct}%", font(round(17 * s)), FG, 0)]), _pt(cx, cy, r_mid, 90))
    for angle in (a0 - 24, a1 + 24):  # separateurs radiaux
        d.line([_pt(cx, cy, r0 + 8 * s, angle), _pt(cx, cy, r1 - 8 * s, angle)], fill=EDGE,
               width=max(1, round(1.5 * s)))

    if state.get("info"):
        _arc_strip(img, state["info"], cx, cy, s, MINI_STRIP_IN, MINI_STRIP_OUT, 18)

    buttons = draw_buttons(d, cx, cy - (MINI_STRIP_OUT + 8) * s, s) if hover else {}
    return finish(img, w_px, h_px), (w_px / 2, cy / SS), buttons


# --------------------------------------------------------------------------
# Tableau des scores, forme droite : blocs biseautes facon score RL
# --------------------------------------------------------------------------

def render_score(state, k, hover=False):
    u = 0.96  # memes proportions que la version Tk d'origine
    s = k * SS * u
    BW, BH, STRIP, CTRL = 300, 46, 20, 22
    top_u = CTRL + 8
    w_px = round(BW * k * u)
    h_px = round((top_u + BH + 3 + STRIP + 2) * k * u)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, round(1.2 * s))

    top = top_u * s
    bh, slant, third, gap, right = BH * s, 14 * s, 100 * s, 3 * s, BW * s
    flash = state.get("flash")
    panel = (11, 19, 34, 255)
    mid = (20, 31, 54, 255)

    d.polygon([(0, top), (third, top), (third, top + bh), (slant, top + bh)],
              fill=FLASH_WIN[:3] + (255,) if flash == "w" else panel, outline=EDGE, width=lw)
    d.polygon([(lw, top), (third - lw, top), (third - lw, top + 4 * s), (lw + 1.2 * s, top + 4 * s)], fill=GREEN)
    paste_center(img, text_img([("W", font(round(16 * s)), GREEN, 0)]), (30 * s, top + bh / 2 + 2 * s))
    paste_center(img, text_img([(str(state["w"]), font(round(34 * s)), FG, 0)]), (66 * s, top + bh / 2 + 2 * s))

    cx0, cx1 = third + gap, right - third - gap
    d.rectangle([cx0, top, cx1, top + bh], fill=mid, outline=EDGE, width=lw)
    pct, total = pct_of(state)
    paste_center(img, text_img([(f"{pct}%", font(round(24 * s)), FG, 0)]), ((cx0 + cx1) / 2, top + 18 * s))
    _sub(img, state, round(11 * s), ((cx0 + cx1) / 2, top + 37 * s), opacity=0.88)

    rx = right - third
    d.polygon([(rx, top), (right, top), (right - slant, top + bh), (rx, top + bh)],
              fill=FLASH_LOSS[:3] + (255,) if flash == "l" else panel, outline=EDGE, width=lw)
    d.polygon([(rx + lw, top), (right - lw, top), (right - lw - 1.2 * s, top + 4 * s), (rx + lw, top + 4 * s)],
              fill=RED)
    paste_center(img, text_img([(str(state["l"]), font(round(34 * s)), FG, 0)]), (right - 66 * s, top + bh / 2 + 2 * s))
    paste_center(img, text_img([("L", font(round(16 * s)), RED, 0)]), (right - 30 * s, top + bh / 2 + 2 * s))

    info = state.get("info")
    if info:
        text, color, filled = info
        sy0 = top + bh + gap
        sy1 = sy0 + STRIP * s
        inset = 8 * s
        d.polygon([(cx0 - 10 * s, sy0), (cx1 + 10 * s, sy0), (cx1 + 10 * s - inset, sy1), (cx0 - 10 * s + inset, sy1)],
                  fill=color if filled else panel, outline=None if filled else EDGE, width=lw)
        paste_center(img, text_img([(text, font(round(12 * s), SEMI), panel if filled else color, 0)], shear=0),
                     ((cx0 + cx1) / 2, (sy0 + sy1) / 2))

    buttons = draw_buttons(d, W / 2, top - 6 * s, k * SS) if hover else {}
    return finish(img, w_px, h_px, opacity=0.88), (w_px / 2, h_px), buttons


# --------------------------------------------------------------------------
# Minimal, forme droite : pastille
# --------------------------------------------------------------------------

def render_mini(state, k, hover=False):
    s = k * SS
    BW, BH, CTRL = 170, 34, 24
    top_u = CTRL + 10
    w_px = round(max(BW, BUTTONS_W + 4) * k)  # assez large pour la rangee de boutons
    h_px = round((top_u + BH + 22) * k)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, top = W / 2, top_u * s
    x0, x1, y0, y1 = cx - BW / 2 * s, cx + BW / 2 * s, top, top + BH * s

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([x0, y0, x1, y1], radius=BH / 2 * s, fill=(0, 0, 0, 140))
    img.alpha_composite(_blur_cached(shadow, 6 * s))

    d = ImageDraw.Draw(img)
    flash = state.get("flash")
    fill = FLASH_WIN if flash == "w" else FLASH_LOSS if flash == "l" else PANEL
    d.rounded_rectangle([x0, y0, x1, y1], radius=BH / 2 * s, fill=fill, outline=EDGE, width=max(1, round(1.2 * s)))
    mid_y = (y0 + y1) / 2
    big = font(round(24 * s))
    paste_center(img, text_img([(str(state["w"]), big, GREEN, 0)]), (x0 + 30 * s, mid_y))
    paste_center(img, text_img([(str(state["l"]), big, RED, 0)]), (x1 - 30 * s, mid_y))
    pct, _ = pct_of(state)
    paste_center(img, text_img([(f"{pct}%", font(round(17 * s)), FG, 0)]), (cx, mid_y))
    for sx in (x0 + 55 * s, x1 - 55 * s):
        d.line([(sx + 3 * s, y0 + 8 * s), (sx - 3 * s, y1 - 8 * s)], fill=EDGE, width=max(1, round(1.5 * s)))

    info = state.get("info")
    if info:
        text, color, filled = info
        t = text_img([(text, font(round(11 * s), SEMI), PANEL[:3] + (255,) if filled else color, 0)], shear=0)
        ty = y1 + 12 * s
        d.rounded_rectangle([cx - t.width / 2 - 8 * s, ty - 8 * s, cx + t.width / 2 + 8 * s, ty + 8 * s],
                            radius=8 * s, fill=color if filled else PANEL)
        paste_center(img, t, (cx, ty))

    buttons = draw_buttons(d, cx, top - 8 * s, s) if hover else {}
    return finish(img, w_px, h_px), (w_px / 2, h_px), buttons


# --------------------------------------------------------------------------
# Formes verticales : collees au bord droit de l'ecran, independantes de
# l'echelle de l'interface du jeu
# --------------------------------------------------------------------------

V_SIDE = 40 + 8  # colonne de boutons + marge, a gauche
V_BAND = 20      # bandeau d'info vertical, entre les boutons et le panneau


def _fit_font(text, px, style, max_w):
    """Police la plus grande (<= px) pour que le texte tienne dans max_w."""
    while px > 6 and font(px, style).getlength(text) > max_w:
        px -= 1
    return font(px, style)


def _v_strip_len(info, s):
    """Longueur du bandeau d'info vertical (pixels sur-echantillonnes)."""
    return font(round(12 * s), SEMI).getlength(info[0]) + 24 * s if info else 0


def _v_strip(img, info, x0, cy, s, rounded):
    """Bandeau d'info vertical (texte de bas en haut), centre sur cy."""
    text, color, filled = info
    half = _v_strip_len(info, s) / 2
    box = [x0, cy - half, x0 + V_BAND * s, cy + half]
    d = ImageDraw.Draw(img)
    fill = color if filled else PANEL
    if rounded:
        d.rounded_rectangle(box, radius=V_BAND / 2 * s, fill=fill)
    else:
        sl = 6 * s
        d.polygon([(box[0], box[1] + sl), (box[2], box[1]), (box[2], box[3]), (box[0], box[3] - sl)], fill=fill,
                  outline=None if filled else EDGE, width=max(1, round(1.2 * s)))
    t = text_img([(text, font(round(12 * s), SEMI), PANEL[:3] + (255,) if filled else color, 0)], shear=0)
    paste_center(img, t, ((box[0] + box[2]) / 2, cy), 90)


def render_vscore(state, k, hover=False):
    """Tableau des scores vertical : W / % / L empiles, colles au bord droit."""
    s = k * SS
    PW, WB, MB, G, sl = 96, 64, 58, 3, 14
    PH = 2 * WB + MB + 2 * G
    info = state.get("info")
    h_u = max(PH, BUTTONS_H, _v_strip_len(info, s) / s) + 8
    w_u = V_SIDE + V_BAND + 5 + PW
    w_px, h_px = round(w_u * k), round(h_u * k)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, round(1.2 * s))
    flash = state.get("flash")
    panel, mid = (11, 19, 34, 255), (20, 31, 54, 255)

    x0, xr = W - PW * s, W
    cy = H / 2
    top = cy - PH / 2 * s
    a = 4 * s

    # Victoires : coin haut-gauche biseaute, lisere vert cote ecran
    y0, y1 = top, top + WB * s
    d.polygon([(x0 + sl * s, y0), (xr, y0), (xr, y1), (x0, y1), (x0, y0 + sl * s)],
              fill=FLASH_WIN[:3] + (255,) if flash == "w" else panel, outline=EDGE, width=lw)
    d.polygon([(x0 + sl * s, y0), (x0 + sl * s + a, y0), (x0 + a, y0 + sl * s), (x0 + a, y1), (x0, y1),
               (x0, y0 + sl * s)], fill=GREEN)
    paste_center(img, text_img([("W", font(round(16 * s)), GREEN, round(12 * s)),
                                (str(state["w"]), font(round(34 * s)), FG, 0)]), (x0 + (PW / 2 + 2) * s, (y0 + y1) / 2))

    # Pourcentage
    y0 = y1 + G * s
    y1 = y0 + MB * s
    d.rectangle([x0, y0, xr, y1], fill=mid, outline=EDGE, width=lw)
    pct, _ = pct_of(state)
    paste_center(img, text_img([(f"{pct}%", font(round(24 * s)), FG, 0)]), (x0 + PW / 2 * s, y0 + 23 * s))
    _sub(img, state, round(11 * s), (x0 + PW / 2 * s, y0 + 44 * s), opacity=0.88, max_w=(PW - 12) * s)

    # Defaites : coin bas-gauche biseaute, lisere rouge
    y0 = y1 + G * s
    y1 = y0 + WB * s
    d.polygon([(x0, y0), (xr, y0), (xr, y1), (x0 + sl * s, y1), (x0, y1 - sl * s)],
              fill=FLASH_LOSS[:3] + (255,) if flash == "l" else panel, outline=EDGE, width=lw)
    d.polygon([(x0, y0), (x0 + a, y0), (x0 + a, y1 - sl * s), (x0 + sl * s + a, y1), (x0 + sl * s, y1),
               (x0, y1 - sl * s)], fill=RED)
    paste_center(img, text_img([(str(state["l"]), font(round(34 * s)), FG, 0),
                                ("L", font(round(16 * s)), RED, round(12 * s))]), (x0 + (PW / 2 + 2) * s, (y0 + y1) / 2))

    if info:
        _v_strip(img, info, x0 - (5 + V_BAND) * s, cy, s, rounded=False)
    buttons = draw_buttons_column(d, 0, cy, s) if hover else {}
    return finish(img, w_px, h_px, opacity=0.88), (w_px, h_px / 2), buttons


def render_mini_v(state, k, hover=False):
    """Minimal vertical : languette arrondie qui sort du bord droit."""
    s = k * SS
    PW, PH = 50, 176
    info = state.get("info")
    h_u = max(PH + 24, BUTTONS_H, _v_strip_len(info, s) / s) + 8
    w_u = V_SIDE + V_BAND + 8 + PW
    w_px, h_px = round(w_u * k), round(h_u * k)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cy = H / 2
    box = [W - PW * s, cy - PH / 2 * s, W + PW * s, cy + PH / 2 * s]  # deborde a droite : bord droit plat
    r = PW / 2 * s

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(box, radius=r, fill=(0, 0, 0, 140))
    img.alpha_composite(_blur_cached(shadow, 6 * s))

    d = ImageDraw.Draw(img)
    flash = state.get("flash")
    fill = FLASH_WIN if flash == "w" else FLASH_LOSS if flash == "l" else PANEL
    d.rounded_rectangle(box, radius=r, fill=fill, outline=EDGE, width=max(1, round(1.2 * s)))
    cx = W - PW / 2 * s
    big = font(round(24 * s))
    paste_center(img, text_img([(str(state["w"]), big, GREEN, 0)]), (cx, cy - 58 * s))
    paste_center(img, text_img([(str(state["l"]), big, RED, 0)]), (cx, cy + 58 * s))
    pct, _ = pct_of(state)
    paste_center(img, text_img([(f"{pct}%", _fit_font(f"{pct}%", round(17 * s), BOLD, (PW - 8) * s), FG, 0)]), (cx, cy))
    for sy in (cy - 31 * s, cy + 31 * s):
        d.line([(cx - 13 * s, sy + 3 * s), (cx + 13 * s, sy - 3 * s)], fill=EDGE, width=max(1, round(1.5 * s)))

    if info:
        _v_strip(img, info, W - (PW + 8 + V_BAND) * s, cy, s, rounded=True)
    buttons = draw_buttons_column(d, 0, cy, s) if hover else {}
    return finish(img, w_px, h_px), (w_px, h_px / 2), buttons


# --------------------------------------------------------------------------
# Animations de fin de match : jouees par-dessus n'importe quel design
# --------------------------------------------------------------------------

set_colors(GREEN, RED)  # CONFETTI, SHARDS...


def _ease_out(p):
    return 1 - (1 - p) ** 3


def _pulse(t, at, width):
    return math.exp(-((t - at) / width) ** 2)


class MatchAnimation:
    """Victoire : l'overlay rebondit, halo vert, onde de choc et confettis.
    Defaite : l'overlay tremble et rougit, halo rouge, eclats qui tombent.

    frame(base) renvoie l'image de l'overlay agrandie d'une marge `pad` de chaque
    cote (place pour les effets) ; l'ancre se decale donc de (pad, pad).
    """

    DURATION = {"w": 2.8, "l": 2.4}

    def __init__(self, kind, k):
        self.kind, self.k = kind, k
        self.win = kind == "w"
        self.pad = round(110 * k)
        self.duration = self.DURATION[kind]
        self.t0 = time.monotonic()
        self.cache = None       # (base, masque du halo, base toute rouge, contour de l'overlay)
        self.particles = None   # creees au premier frame : il faut connaitre la taille de l'overlay

    def elapsed(self):
        return time.monotonic() - self.t0

    def done(self):
        return self.elapsed() >= self.duration

    def _prepare(self, base):
        p = self.pad
        alpha = base.getchannel("A")
        mask = Image.new("L", (base.width + 2 * p, base.height + 2 * p), 0)
        mask.paste(alpha, (p, p))
        mask = mask.filter(ImageFilter.GaussianBlur(16 * self.k)).point(lambda v: min(255, v * 2.2))
        red = Image.new("RGBA", base.size, RED)
        red.putalpha(alpha)
        x0, y0, x1, y1 = alpha.point(lambda v: 255 if v > 100 else 0).getbbox() or (0, 0, *base.size)
        self.cache = (base, mask, red, (x0 + p, y0 + p, x1 + p, y1 + p))

    def _spawn(self, box):
        rnd = random.Random()
        k = self.k
        x0, y0, x1, y1 = box
        mx = (x1 - x0) * 0.2
        parts = []
        if self.win:  # gerbe de confettis vers le haut
            for _ in range(70):
                a = math.radians(rnd.uniform(25, 155))
                v = rnd.uniform(260, 620) * k
                parts.append({"x": rnd.uniform(x0 + mx, x1 - mx), "y": rnd.uniform(y0, (y0 + y1) / 2),
                              "vx": v * math.cos(a), "vy": -v * math.sin(a), "drag": 2.5, "g": 820 * k,
                              "rot": rnd.uniform(0, 360), "spin": rnd.uniform(-720, 720),
                              "flip": rnd.uniform(4, 12), "phase": rnd.uniform(0, 6.3),
                              "w": rnd.uniform(5, 9) * k, "h": rnd.uniform(2.5, 4.5) * k,
                              "color": rnd.choice(CONFETTI), "delay": rnd.uniform(0, 0.25)})
        else:  # eclats qui se detachent et tombent
            for _ in range(28):
                parts.append({"x": rnd.uniform(x0 + mx, x1 - mx), "y": rnd.uniform((y0 + y1) / 2, y1),
                              "vx": rnd.uniform(-90, 90) * k, "vy": rnd.uniform(-160, 20) * k,
                              "drag": 0.6, "g": 900 * k,
                              "rot": rnd.uniform(0, 360), "spin": rnd.uniform(-300, 300),
                              "flip": 0, "phase": 0,
                              "w": rnd.uniform(4, 9) * k, "h": rnd.uniform(4, 9) * k,
                              "color": rnd.choice(SHARDS), "delay": rnd.uniform(0.05, 0.35)})
        return parts

    def _particle(self, q, t):
        """Polygone de la particule a l'instant t (chute avec frottement de l'air)."""
        c, g = q["drag"], q["g"]
        e = 1 - math.exp(-c * t)
        x = q["x"] + q["vx"] / c * e
        y = q["y"] + g / c * t + (q["vy"] - g / c) / c * e
        if self.win:
            x += math.sin(t * 6 + q["phase"]) * 6 * self.k  # les confettis flottent
            hw, hh = q["w"] / 2, q["h"] / 2 * abs(math.cos(t * q["flip"])) + 0.5
            pts = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        else:
            pts = [(0, -q["w"]), (q["w"] * 0.8, q["h"]), (-q["w"] * 0.6, q["h"] * 0.7)]
        a = math.radians(q["rot"] + q["spin"] * t)
        ca, sa = math.cos(a), math.sin(a)
        return [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]

    def frame(self, base):
        t = self.elapsed()
        k, p = self.k, self.pad
        if self.cache is None or self.cache[0] is not base:
            self._prepare(base)
        _, mask, red, box = self.cache
        if self.particles is None:
            self.particles = self._spawn(box)
        W, H = mask.size
        fade = min(1.0, max(0.0, (self.duration - t) / 0.7))
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # Halo : scintille en cas de victoire, bat deux fois (coeur) en cas de defaite
        if self.win:
            glow = (0.6 + 0.4 * math.sin(t * 9)) * min(1.0, t / 0.15) * fade
        else:
            beat = _pulse(t, 0.12, 0.22) + 0.6 * _pulse(t, 0.8, 0.25)
            glow = min(1.0, beat + 0.25) * fade
        halo = Image.new("RGBA", (W, H), (GREEN if self.win else RED)[:3] + (0,))
        halo.putalpha(mask.point(lambda v: round(v * glow)))
        out.alpha_composite(halo)

        # L'overlay lui-meme : rebond (victoire) ou secousse + teinte rouge (defaite)
        img, dx, dy = base, 0.0, 0.0
        if self.win:
            if t < 0.45:
                sc = 1 + 0.12 * math.sin(math.pi * t / 0.45)
            elif t < 0.75:
                sc = 1 - 0.03 * math.sin(math.pi * (t - 0.45) / 0.3)
            else:
                sc = 1
            if sc != 1:
                img = base.convert("RGBa").resize((round(base.width * sc), round(base.height * sc)),
                                                  Image.BICUBIC).convert("RGBA")
        else:
            dx = 9 * k * math.sin(t * 2 * math.pi * 7) * math.exp(-t * 3.5)
            dy = 4 * k * math.sin(math.pi * min(t / 0.5, 1.0))
            tint = 0.45 * (_pulse(t, 0.12, 0.22) + 0.6 * _pulse(t, 0.8, 0.25))
            if tint > 0.01:
                img = Image.blend(base, red, min(1.0, tint))
        out.alpha_composite(img, (round(p + (base.width - img.width) / 2 + dx),
                                  round(p + (base.height - img.height) / 2 + dy)))

        fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(fx)
        if self.win:  # deux ondes de choc qui partent du contour de l'overlay
            x0, y0, x1, y1 = box
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            for start in (0.0, 0.15):
                q = (t - start) / 0.8
                if 0 < q < 1:
                    grow = 4 * k + _ease_out(q) * p * 0.9
                    d.ellipse([cx - (x1 - x0) / 2 - grow, cy - (y1 - y0) / 2 - grow,
                               cx + (x1 - x0) / 2 + grow, cy + (y1 - y0) / 2 + grow],
                              outline=GREEN[:3] + (round(220 * (1 - q)),), width=max(1, round(3 * k * (1 - q) + 1)))
        alpha = round(255 * fade)
        for q in self.particles:
            tt = t - q["delay"]
            if tt > 0:
                d.polygon(self._particle(q, tt), fill=q["color"][:3] + (alpha,))
        out.alpha_composite(fx)
        return out, (p, p)


class GoalAnimation:
    """Animations de but, volontairement differentes de celles de fin de match.
    But marque ("gw") : eclair de lumiere qui balaie l'overlay, rayons et etincelles en etoile
    (comme une explosion de but), petit "pop".
    But encaisse ("gl") : un ballon arrive dans l'overlay et un filet de but, dessine par-dessus,
    ondule depuis le point d'impact ; l'overlay recule et rougit un instant.
    Tous les effets sont dessines par-dessus l'overlay.
    Meme interface que MatchAnimation : frame(base) -> (image agrandie de pad, (pad, pad))."""

    DURATION = {"gw": 1.5, "gl": 1.4}

    def __init__(self, kind, k):
        self.kind, self.k = kind, k
        self.scored = kind == "gw"
        self.pad = round(90 * k)
        self.duration = self.DURATION[kind]
        self.t0 = time.monotonic()
        self.cache = None
        self.sparks = None

    def elapsed(self):
        return time.monotonic() - self.t0

    def done(self):
        return self.elapsed() >= self.duration

    def _prepare(self, base):
        alpha = base.getchannel("A")
        x0, y0, x1, y1 = alpha.point(lambda v: 255 if v > 100 else 0).getbbox() or (0, 0, *base.size)
        red = Image.new("RGBA", base.size, RED[:3] + (255,))
        red.putalpha(alpha)
        self.solid = alpha.point(lambda v: 255 if v > 150 else 0)  # panneaux seuls, sans l'ombre autour
        self.cache = (base, alpha, red, (x0, y0, x1, y1))
        rnd = random.Random()
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.sparks = [{"a": rnd.uniform(0, 2 * math.pi), "v": rnd.uniform(220, 480) * self.k,
                        "r": rnd.uniform(1.6, 3.2) * self.k, "color": rnd.choice((GREEN, GOLD, FG)),
                        "delay": rnd.uniform(0, 0.12), "x": cx, "y": cy} for _ in range(26)]
        # But encaisse : point d'impact du ballon et direction d'ou il arrive
        self.impact = ((x0 + x1) / 2, (y0 + y1) / 2)
        for _ in range(40):  # un point sur un panneau (pas dans le vide sous l'arc)
            ix, iy = x0 + (x1 - x0) * rnd.uniform(0.3, 0.7), y0 + (y1 - y0) * rnd.uniform(0.25, 0.75)
            if self.solid.getpixel((min(int(ix), base.width - 1), min(int(iy), base.height - 1))):
                self.impact = (ix, iy)
                break
        self.ball_from = rnd.uniform(-2.6, -0.5)  # angle : le ballon vient d'en haut

    def frame(self, base):
        t = self.elapsed()
        if self.cache is None or self.cache[0] is not base:
            self._prepare(base)
        return self._scored(base, t) if self.scored else self._conceded(base, t)

    def _scaled(self, base, sc, out):
        """Colle l'overlay (agrandi ou reduit de sc) au centre de out ; renvoie son decalage."""
        p = self.pad
        img = base
        if sc != 1:
            img = base.convert("RGBa").resize((round(base.width * sc), round(base.height * sc)),
                                              Image.BICUBIC).convert("RGBA")
        ox, oy = round(p + (base.width - img.width) / 2), round(p + (base.height - img.height) / 2)
        out.alpha_composite(img, (ox, oy))
        return img

    def _scored(self, base, t):
        k, p = self.k, self.pad
        _, alpha, _, (x0, y0, x1, y1) = self.cache
        W, H = base.width + 2 * p, base.height + 2 * p
        fade = min(1.0, max(0.0, (self.duration - t) / 0.4))
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cx, cy = p + (x0 + x1) / 2, p + (y0 + y1) / 2

        # "Pop" : agrandissement bref et sec
        self._scaled(base, 1 + 0.07 * math.sin(math.pi * t / 0.28) if t < 0.28 else 1, out)

        # Eclair de lumiere en biais qui traverse l'overlay de gauche a droite
        q = (t - 0.08) / 0.5
        if 0 < q < 1:
            bw = (x1 - x0) * 0.22
            x = x0 - bw + q * (x1 - x0 + 2 * bw)
            band = Image.new("L", base.size, 0)
            sk = (y1 - y0) * 0.35
            ImageDraw.Draw(band).polygon([(x, y0), (x + bw, y0), (x + bw - sk, y1), (x - sk, y1)], fill=210)
            band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(bw * 0.25)), alpha)
            shine = Image.new("RGBA", base.size, (255, 255, 255, 0))
            shine.putalpha(band)
            out.alpha_composite(shine, (p, p))

        # Rayons en etoile qui partent du centre, par-dessus l'overlay
        q = t / 0.6
        if q < 1:
            fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(fx)
            reach = max(x1 - x0, y1 - y0) / 2 + p * 0.95
            for i in range(14):
                a = 2 * math.pi * i / 14 + 0.2
                r0, r1 = reach * (0.25 + 0.55 * _ease_out(q)), reach * (0.45 + 0.55 * _ease_out(q))
                color = (GOLD if i % 2 else GREEN)[:3] + (round(230 * (1 - q)),)
                d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))],
                       fill=color, width=max(1, round(4 * k * (1 - q) + 1)))
            out.alpha_composite(fx.filter(ImageFilter.GaussianBlur(1.2 * k)))

        # Etincelles projetees
        d = ImageDraw.Draw(out)
        for sp in self.sparks:
            tt = t - sp["delay"]
            if tt <= 0:
                continue
            dist = sp["v"] / 3 * (1 - math.exp(-3 * tt))
            x, y = p + sp["x"] + dist * math.cos(sp["a"]), p + sp["y"] + dist * math.sin(sp["a"]) + 60 * k * tt * tt
            r = sp["r"] * (1 - min(1, tt / self.duration))
            if r > 0.3:
                d.ellipse([x - r, y - r, x + r, y + r], fill=sp["color"][:3] + (round(255 * fade),))
        return out, (p, p)

    def _conceded(self, base, t):
        k, p = self.k, self.pad
        _, alpha, red, (x0, y0, x1, y1) = self.cache
        W, H = base.width + 2 * p, base.height + 2 * p
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ix, iy = self.impact
        hit = 0.2  # le ballon touche le filet
        fade = 1.0 if t < 0.9 else max(0.0, 1 - (t - 0.9) / (self.duration - 0.9))

        # L'overlay recule sous le choc et rougit un instant
        tt = t - hit
        sc = 1 - 0.05 * math.sin(math.pi * tt / 0.35) if 0 < tt < 0.35 else 1
        tint = 0.28 * _pulse(t, hit + 0.05, 0.2)
        img = Image.blend(base, red, tint) if tint > 0.01 else base
        self._scaled(img, sc, out)

        # Filet de but par-dessus l'overlay : il ondule depuis l'impact, puis se calme
        if t >= hit:
            amp = 7 * k * math.exp(-(t - hit) * 3.2)
            mesh = 11 * k
            lam, speed = 26 * k, 160 * k

            def warp(x, y):
                dx, dy = x - ix, y - iy
                dist = math.hypot(dx, dy) or 1
                front = (t - hit) * speed
                wave = amp * math.exp(-max(0, dist - front) / (18 * k)) * math.sin((dist - front) / lam * 2 * math.pi)
                return x + dx / dist * wave, y + dy / dist * wave

            layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            step = 5 * k
            color = (255, 255, 255, 150)
            w = max(1, round(1.1 * k))
            y = y0 - (iy - y0) % mesh
            while y <= y1:
                pts, x = [], x0
                while x <= x1 + step:
                    pts.append(warp(x, y))
                    x += step
                d.line(pts, fill=color, width=w)
                y += mesh
            x = x0 - (ix - x0) % mesh
            while x <= x1:
                pts, y = [], y0
                while y <= y1 + step:
                    pts.append(warp(x, y))
                    y += step
                d.line(pts, fill=color, width=w)
                x += mesh
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), self.solid).point(lambda v: round(v * fade)))
            out.alpha_composite(layer, (p, p))

        # Le ballon arrive vers le point d'impact en rapetissant (il rentre dans le filet)
        fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(fx)
        if t < hit + 0.12:
            q = min(1.0, t / hit)
            dist = (1 - _ease_out(q)) * (p + max(x1 - x0, y1 - y0) / 2)
            bx, by = p + ix + dist * math.cos(self.ball_from), p + iy + dist * math.sin(self.ball_from)
            r = (11 - 5 * q) * k
            a = round(255 * (1 - max(0.0, t - hit) / 0.12))
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=(235, 240, 245, a), outline=(30, 40, 60, a),
                      width=max(1, round(1.5 * k)))
            d.ellipse([bx - r * 0.35, by - r * 0.35, bx + r * 0.35, by + r * 0.35], fill=(30, 40, 60, a))
        # Onde rouge a l'impact
        q = (t - hit) / 0.45
        if 0 < q < 1:
            r = (6 + 34 * _ease_out(q)) * k
            d.ellipse([p + ix - r, p + iy - r, p + ix + r, p + iy + r], outline=RED[:3] + (round(230 * (1 - q)),),
                      width=max(1, round(3 * k * (1 - q) + 1)))
        out.alpha_composite(fx)
        return out, (p, p)


def animation(kind, k):
    """Animation de fin de match ("w", "l") ou de but ("gw", "gl")."""
    return GoalAnimation(kind, k) if kind in GoalAnimation.DURATION else MatchAnimation(kind, k)


# --------------------------------------------------------------------------
# Adversaires deja croises (affiches pendant le match)
# --------------------------------------------------------------------------

def render_met_chips(players, k, title, letters, align="center"):
    """players = [(pseudo, V, D)] -> titre et une pastille par joueur, empiles.
    letters = ("V", "D") dans la langue active ; align = "center" ou "right"."""
    s = k * SS
    pad, ch, gap = 14 * s, 26 * s, 5 * s  # marge (ombre), hauteur d'une pastille, ecart
    head = text_img([(title, font(round(11 * s), SEMI), AMBER, 0)], shear=0)
    name_f, rec_f = font(round(14 * s)), font(round(13 * s), SEMI)
    sep = 10 * s  # entre le pseudo et le bilan
    chips = [(text_img([(name, name_f, FG, 0)], shear=0),
              text_img([(f"{w}{letters[0]}", rec_f, GREEN, 0), (f"{l}{letters[1]}", rec_f, RED, 0)], shear=0))
             for name, w, l in players]
    widths = [n.width + sep + r.width + 24 * s for n, r in chips]
    inner_w = max([head.width] + widths)
    inner_h = head.height + 6 * s + len(chips) * (ch + gap) - gap
    w_px, h_px = math.ceil((inner_w + 2 * pad) / SS), math.ceil((inner_h + 2 * pad) / SS)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    def x_of(width):
        return W - pad - width if align == "right" else (W - width) / 2

    boxes, y = [], pad + head.height + 6 * s
    for bw in widths:
        boxes.append([x_of(bw), y, x_of(bw) + bw, y + ch])
        y += ch + gap
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for box in boxes:
        sd.rounded_rectangle(box, radius=ch / 2, fill=(0, 0, 0, 150))
    img.alpha_composite(_blur_cached(shadow, 6 * s))
    img.alpha_composite(head, (round(x_of(head.width)), round(pad)))
    d = ImageDraw.Draw(img)
    for box, (name, rec) in zip(boxes, chips):
        d.rounded_rectangle(box, radius=ch / 2, fill=PANEL[:3] + (240,), outline=AMBER, width=max(1, round(1.2 * s)))
        cy = (box[1] + box[3]) / 2
        paste_center(img, name, (box[0] + 12 * s + name.width / 2, cy))
        paste_center(img, rec, (box[2] - 12 * s - rec.width / 2, cy))
    return finish(img, w_px, h_px)


# --------------------------------------------------------------------------
# Resume de fin de match
# --------------------------------------------------------------------------

def render_summary(info, k, T):
    """Carte affichee apres un match. info = {"won", "mode", "score", "me"} ; T = traduction."""
    s = k * SS
    BW, BH, slant = 340, 150, 14
    pad = 18  # place pour l'ombre
    w_px, h_px = round((BW + 2 * pad) * k), round((BH + 2 * pad) * k)
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, y0, x1, y1 = pad * s, pad * s, (pad + BW) * s, (pad + BH) * s
    shape = [(x0 + slant * s, y0), (x1, y0), (x1 - slant * s, y1), (x0, y1)]

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon(shape, fill=(0, 0, 0, 160))
    img.alpha_composite(_blur_cached(shadow, 8 * s))

    d = ImageDraw.Draw(img)
    color = GREEN if info["won"] else RED
    d.polygon(shape, fill=(11, 19, 34, 240), outline=EDGE, width=max(1, round(1.2 * s)))

    # En-tete : resultat, mode, score final
    hh = 40 * s
    d.polygon([(x0 + slant * s, y0), (x1, y0), (x1 - slant * s * hh / (y1 - y0), y0 + hh),
               (x0 + slant * s * (1 - hh / (y1 - y0)), y0 + hh)], fill=_scaled(color, 0.36, 255))
    d.polygon([(x0 + slant * s, y0), (x1, y0), (x1 - 0.5 * s, y0 + 4 * s), (x0 + (slant - 0.5) * s, y0 + 4 * s)],
              fill=color)
    title = T("sum_win" if info["won"] else "sum_loss")  # un match quitte est une defaite, sans plus
    t = text_img([(title, font(round(24 * s)), FG, 0)])
    img.alpha_composite(t, (round(x0 + 24 * s), round(y0 + hh / 2 + 2 * s - t.height / 2)))
    right = x1 - 22 * s
    score = info.get("score")
    if score and None not in score:
        t = text_img([(f"{score[0]} – {score[1]}", font(round(24 * s)), FG, 0)])
        right -= t.width
        img.alpha_composite(t, (round(right), round(y0 + hh / 2 + 2 * s - t.height / 2)))
        right -= 12 * s
    if info.get("mode"):
        t = text_img([(info["mode"].upper(), font(round(15 * s), SEMI), FG, 0)], shear=0)
        right -= t.width
        img.alpha_composite(t, (round(right), round(y0 + hh / 2 + 2 * s - t.height / 2)))
        right -= 12 * s
    me = info.get("me") or {}
    if me.get("mvp"):
        t = text_img([(T("sum_mvp"), font(round(13 * s)), (11, 19, 34, 255), 0)], shear=0)
        bw, bh = t.width + 14 * s, 20 * s
        bx, by = right - bw, y0 + hh / 2 + 2 * s - bh / 2
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=4 * s, fill=GOLD)
        paste_center(img, t, (bx + bw / 2, by + bh / 2))

    # Statistiques du joueur
    cells = [("sum_score", me.get("score")), ("sum_goals", me.get("goals")), ("sum_assists", me.get("assists")),
             ("sum_saves", me.get("saves")), ("sum_shots", me.get("shots")), ("sum_demos", me.get("demos"))]
    cw = (BW - 2 * slant - 12) * s / len(cells)
    cx = x0 + (slant + 6) * s + cw / 2
    for key, value in cells:
        paste_center(img, text_img([("–" if value is None else str(value), font(round(26 * s)), FG, 0)]),
                     (cx, y0 + 72 * s))
        paste_center(img, text_img([(T(key), font(round(10 * s), SEMI), MUTED, 0)], shear=0), (cx, y0 + 96 * s))
        cx += cw

    # Pied : precision et but le plus rapide
    foot = []
    if me.get("shots"):
        foot.append(T("sum_accuracy", p=round(me.get("goals", 0) * 100 / me["shots"])))
    if me.get("fastest"):
        foot.append(T("sum_fastest", v=round(me["fastest"])))
    if foot:
        d.line([(x0 + 26 * s, y0 + 112 * s), (x1 - 26 * s, y0 + 112 * s)], fill=EDGE, width=max(1, round(s)))
        paste_center(img, text_img([("   ·   ".join(foot), font(round(11 * s), SEMI), MUTED, 0)], shear=0),
                     ((x0 + x1) / 2, y0 + 128 * s))
    return finish(img, w_px, h_px)


# --------------------------------------------------------------------------
# Carte de session a partager (copiee dans le presse-papiers)
# --------------------------------------------------------------------------

def render_session_card(info, T):
    """info = {"w", "l", "modes": {mode: [V, D]}, "best_streak", "mvp", "goals", "assists", "saves",
    "fastest", "minutes", "date"}. Image 760 x 400 sur fond opaque (pour Discord)."""
    k = 1.0
    s = k * SS
    w_px, h_px = 760, 400
    W, H = w_px * SS, h_px * SS
    img = Image.new("RGBA", (W, H), (7, 12, 24, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, H, SS * 2):  # leger degrade
        t = y / H
        d.rectangle([0, y, W, y + SS * 2], fill=(int(9 + 14 * t), int(15 + 18 * t), int(30 + 22 * t), 255))
    pad = 34 * s
    # bandeau victoires / defaites en haut
    w, l = info["w"], info["l"]
    total = w + l
    split = W * (w / total if total else 0.5)
    d.rectangle([0, 0, split, 8 * s], fill=GREEN)
    d.rectangle([split, 0, W, 8 * s], fill=RED)

    t = text_img([("RL STATS", font(round(16 * s)), MUTED, 0), ("·  " + T("card_session"), font(round(16 * s), SEMI),
                                                                   MUTED, 0)], shear=0)
    img.alpha_composite(t, (round(pad), round(30 * s)))
    t = text_img([(info["date"], font(round(16 * s), SEMI), MUTED, 0)], shear=0)
    img.alpha_composite(t, (round(W - pad - t.width), round(30 * s)))

    # Grand score
    pct = round(w * 100 / total) if total else 0
    big = text_img([(str(w), font(round(96 * s)), GREEN, 0), ("–", font(round(70 * s)), MUTED, round(14 * s)),
                    (str(l), font(round(96 * s)), RED, 0)])
    img.alpha_composite(big, (round(pad - 10 * s), round(62 * s)))
    t = text_img([(f"{pct}%", font(round(64 * s)), FG, 0)])
    img.alpha_composite(t, (round(W - pad - t.width), round(76 * s)))
    t = text_img([(T("card_winrate"), font(round(14 * s), SEMI), MUTED, 0)], shear=0)
    img.alpha_composite(t, (round(W - pad - t.width), round(150 * s)))

    # Modes
    x = pad
    y = 196 * s
    for mode, (mw, ml) in sorted(info["modes"].items()):
        if mode == "?" or mw + ml == 0:
            continue
        t = text_img([(mode.upper(), font(round(18 * s)), FG, 0), (f"{mw}–{ml}", font(round(18 * s), SEMI), MUTED, 0)])
        bw = t.width + 24 * s
        d.rounded_rectangle([x, y, x + bw, y + 36 * s], radius=6 * s, fill=(20, 31, 54, 255), outline=EDGE,
                            width=max(1, round(s)))
        img.alpha_composite(t, (round(x + 12 * s), round(y + 18 * s - t.height / 2)))
        x += bw + 10 * s

    # Statistiques
    cells = [(T("card_streak"), str(info["best_streak"])), (T("sum_mvp"), str(info["mvp"])),
             (T("sum_goals"), str(info["goals"])), (T("sum_assists"), str(info["assists"])),
             (T("sum_saves"), str(info["saves"])),
             (T("card_fastest"), f"{round(info['fastest'])}" if info["fastest"] else "–")]
    cw = (W - 2 * pad) / len(cells)
    y = 262 * s
    d.line([(pad, y - 10 * s), (W - pad, y - 10 * s)], fill=EDGE, width=max(1, round(s)))
    for i, (lab, value) in enumerate(cells):
        cx = pad + cw * i + cw / 2
        paste_center(img, text_img([(value, font(round(40 * s)), FG, 0)]), (cx, y + 34 * s))
        paste_center(img, text_img([(lab, font(round(12 * s), SEMI), MUTED, 0)], shear=0), (cx, y + 72 * s))
    foot = text_img([(T("card_footer", min=info["minutes"]), font(round(12 * s), SEMI), MUTED, 0)], shear=0)
    img.alpha_composite(foot, (round((W - foot.width) / 2), round(H - 30 * s)))
    return img.resize((w_px, h_px), Image.LANCZOS)


# Deux reglages independants : le design (style) et la forme (libelles : i18n style_* / shape_*)
STYLES = ("tableau", "minimal")
SHAPES = ("arrondi", "droit", "vertical")

# (design, forme) -> (cle de position, fonction de rendu, ancre)
# Ancre : "gauge" = centre de la jauge de boost, "above" = juste au-dessus,
# "edge" = milieu du bord droit de l'ecran
RENDERERS = {
    ("tableau", "arrondi"): ("arc", render_arc, "gauge"),
    ("tableau", "droit"): ("score", render_score, "above"),
    ("tableau", "vertical"): ("vscore", render_vscore, "edge"),
    ("minimal", "arrondi"): ("mini_arc", render_mini_arc, "gauge"),
    ("minimal", "droit"): ("mini", render_mini, "above"),
    ("minimal", "vertical"): ("mini_v", render_mini_v, "edge"),
}
