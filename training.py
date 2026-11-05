"""Fenetre Entrainement : chrono des engagements et guides des mecaniques.

L'API Stats du jeu ne donne ni la position de la voiture, ni son orientation, ni les touches
pressees : on ne peut mesurer que les engagements (temps entre le GO et le premier contact, et qui
touche en premier). Pour le reste, les guides expliquent et le joueur note lui-meme sa progression.

Texte des guides : "## " titre, "- " puce, "1. " etape, "> " conseil encadre, sinon paragraphe.
"""

import datetime
import math
import tkinter as tk
from time import perf_counter as time_now
import urllib.parse
import webbrowser
from tkinter import messagebox, ttk

import pad
from i18n import T, lang
from ui_windows import (BG, BODY_FONT, EDGE, FG, GRID, MUTED, NUM_FONT, OK, PANEL, TITLE_FONT, WARN, _button,
                        _dark_window)

LEVEL_COLORS = ("#2ee66b", "#38bdf8", "#f59e0b", "#ff4d4d")
STATUS_COLORS = (MUTED, WARN, OK)

# Positions de depart de l'equipe bleue (unites du jeu, X vers la droite du schema, Y vers notre cage)
SPAWNS = [(-2048, -2560, "tr_diag"), (2048, -2560, "tr_diag"), (-256, -3840, "tr_offc"), (256, -3840, "tr_offc"),
          (0, -4608, "tr_back")]
BIG_PADS = [(-3072, -4096), (3072, -4096), (-3584, 0), (3584, 0)]
SPAWN_KEYS = ("diag", "offc", "back")  # codes du tracker (kick_spawn) ; textes : T("tr_" + code)
KICKOFF_PACK = "A503-264C-A7EB-D282"  # pack d'entrainement personnalise d'engagements conseille
PAD_ACTIONS = ("jump", "boost", "roll", "roll_l", "roll_r")  # boutons a assigner ; textes : T("pad_" + action)
# Speed flip parfait : temps du GO au contact, par position. Estime avec la physique du jeu (constantes de RLBot :
# boost 991.7 uu/s2, accelerateur 1600 -> 0 a 1410 uu/s, impulsion du flip 500 uu/s) : boost seul en ligne droite
# 2.04 / 2.29 / 2.63 s, speed flip ideal 1.89 / 2.13 / 2.47 s. Parfait : a 0.06 s de l'ideal (precision de la
# mesure, trajectoire jamais tout a fait droite). Bon : plus rapide que sans flip (le flip fait gagner du temps).
# Presque : jusqu'a 0.1 s plus lent que sans flip. Lent : au-dela
PERFECT = {"diag": 1.95, "offc": 2.20, "back": 2.53}
NO_FLIP = {"diag": 2.05, "offc": 2.30, "back": 2.60}
CLOSE = 0.10
GRADE_TEXTS = {"perfect": "dr_perfect", "good": "dr_good", "close": "dr_close", "slow": "dr_slow"}
PERFECT_COLOR = "#facc15"  # or, comme le bandeau et la carte (designs.GOLD)
REF_COLOR = "#cbd5e1"  # geste parfait sur la frise (pointilles)


def kick_grade(attempt):
    """"perfect", "good", "close" ou "slow" pour un essai touche (seuils fixes par position)."""
    dt, spawn = attempt["dt"], attempt["spawn"]
    if dt <= PERFECT[spawn]:
        return "perfect"
    if dt <= NO_FLIP[spawn]:
        return "good"
    return "close" if dt <= NO_FLIP[spawn] + CLOSE else "slow"


def kick_records(store):
    """Record de chaque position {spawn: {"dt", "t"}} : ceux enregistres (gardes meme si on efface les essais),
    completes par les essais encore dans l'historique. Seuls les temps exacts comptent (pas les "≈")."""
    records = {k: dict(v) for k, v in store["kick_records"].items()}
    for a in store["drill"]:
        if a["miss"] or not a.get("exact", True) or a["spawn"] not in PERFECT:
            continue
        if a["spawn"] not in records or a["dt"] < records[a["spawn"]]["dt"]:
            records[a["spawn"]] = {"dt": a["dt"], "t": a["t"]}
    return records


def kick_gap_text(attempt):
    """Texte a cote du temps : parfait, ecart avec le parfait (bon), ou avec le temps sans flip (presque, lent)."""
    grade, spawn = kick_grade(attempt), attempt["spawn"]
    if grade == "perfect":
        return T("gap_perfect")
    if grade == "good":
        return T("gap_to_perfect", d=seconds_text(attempt["dt"] - PERFECT[spawn]))
    return T("gap_no_flip", d=seconds_text(attempt["dt"] - NO_FLIP[spawn]))


def diff_text(value):
    text = f"{value:+.2f}"
    return text.replace(".", ",") if lang() == "fr" else text


def flip_cells(flip):
    """[(libelle, valeur, note)] des mesures d'un speed flip (carte de l'overlay et fenetre)."""
    def ms(v):
        return f"{round(v * 1000)} ms" if v is not None else "–"

    def side(a):
        return T("pf_left") if a < 0 else T("pf_right")

    def signed_ms(v):
        return f"{round(v * 1000):+d} ms" if v is not None else ""

    flipped = flip["flip"] is not None
    tap = "–" if flip.get("tap_side") is None else side(flip["tap_side"])
    if flip.get("tap_side") is not None and flip["jump"] is not None:
        tap += " " + signed_ms(flip["tap_t"] - flip["jump"])  # debut par rapport au 1er saut
    roll = {"l": T("pf_left"), "r": T("pf_right"), "x": T("pf_yes")}.get(flip["roll"], "–")
    if flip["roll"] and flip.get("roll_t") is not None:
        roll += " " + signed_ms(flip["roll_t"])
    return [
        (T("pf_tap"), tap, pad.grade_tap(flip)),
        (T("pf_jump"), seconds_text(flip["jump"]) if flip["jump"] is not None else "–",
         pad.grade("jump", flip["jump"])),
        (T("pf_flip"), ms(flip["flip"]), pad.grade("flip", flip["flip"])),
        (T("pf_angle"), f"{abs(flip['angle'])}° {side(flip['angle'])}" if flip["angle"] is not None else "–",
         pad.grade("angle", flip["angle"]) if flipped else None),
        (T("pf_cancel"), ms(flip["cancel"]), pad.grade("cancel", flip["cancel"]) if flipped else None),
        (T("pf_roll"), roll, pad.grade_roll(flip)),
        (T("pf_boost"), f"{flip['boost']} %" if flip["boost"] is not None else "–",
         pad.grade("boost", flip["boost"])),
    ]


def flip_advices(flip, n=2):
    """Conseils les plus utiles pour ce speed flip, deja traduits."""
    side = T(pad.roll_advice_side(flip))
    return [T(key, side=side) for key in pad.advices(flip, n)]


def timeline_tracks(tl):
    """Pistes de la frise des inputs : [(libelle, "line" | "bars", donnees, couleur)] ; "line" : [(t, valeur
    -1 a 1)] en escalier, "bars" : [(debut, fin)]. Couleurs : "sky", "gold", "green", "violet", "amber"."""
    return [(T("tl_side"), "line", [(t, x) for t, x, _ in tl["stick"]], "sky"),
            (T("tl_front"), "line", [(t, y) for t, _, y in tl["stick"]], "gold"),
            (T("tl_jump"), "bars", tl["jump"], "green"),
            (T("tl_roll"), "bars", tl["roll"], "violet"),
            (T("tl_boost"), "bars", tl["boost"], "amber")]


def timeline_ticks(t1):
    """Graduations de la frise (secondes apres le depart) et leur texte."""
    step = 0.2 if t1 <= 1.2 else 0.4
    ticks, t = [], 0.0
    while t <= t1 + 1e-6:
        text = f"{t:.1f}"
        ticks.append((t, text.replace(".", ",") if lang() == "fr" else text))
        t += step
    return ticks


# Jauges de la carte (zones de SpeedFlipTrainer, voir pad.grade) : mesure, debut et fin de l'echelle, zones
GAUGES = [("jump", 0.3, 0.75, [(50 * pad.TICK, 75 * pad.TICK, "warn"), (55 * pad.TICK, 70 * pad.TICK, "ok")]),
          ("angle", 0, 60, [(15, 45, "warn"), (22, 38, "ok")]),
          ("cancel", 0, 0.15, [(0, 11.5 * pad.TICK, "warn"), (0, 7.5 * pad.TICK, "ok")])]


def flip_gauges(flip):
    """[(libelle, valeur, position 0 a 1 ou None, zones [(debut, fin, "ok" | "warn")] en 0 a 1, note)] : les
    trois mesures notees par SpeedFlipTrainer, sur une barre avec sa zone verte."""
    labels = {"jump": T("pf_jump"), "angle": T("pf_angle"), "cancel": T("pf_cancel")}
    texts = {cell[0]: cell[1] for cell in flip_cells(flip)}
    out = []
    for key, lo, hi, zones in GAUGES:
        value = flip[key]
        if key == "angle" and value is not None:
            value = abs(value)
        pos = None if value is None else min(1, max(0, (value - lo) / (hi - lo)))
        out.append((labels[key].upper(), texts[labels[key]], pos,
                    [((a - lo) / (hi - lo), (b - lo) / (hi - lo), note) for a, b, note in zones],
                    pad.grade(key, flip[key]) if key == "jump" or flip["flip"] is not None else None))
    return out


def reference_flip(side):
    """Geste conseille par le guide pour un flip du cote `side` (-1 gauche, 1 droite), sur les timings du speed
    flip enregistre de SpeedFlipTrainer (s apres le depart) : petit decalage du stick vers 35 degres de l'autre
    cote 25 ms avant le 1er saut (0,508 s), passage par le haut jusqu'a 30 degres au 2e saut (92 ms apres), puis
    par le cote du flip jusqu'en bas au cancel (42 ms apres), air roll du cote du flip 33 ms apres le flip. Meme
    forme que la frise de pad.analyse ("j1" : 1er saut)."""
    j1, flip, cancel = 0.508, 0.6, 0.642

    def edge(t, a, m=1.0):
        return round(t, 3), round(m * math.sin(math.radians(a)), 2), round(m * math.cos(math.radians(a)), 2)

    stick = [(-0.1, 0, 0), (0.45, 0, 0), edge(0.466, -35 * side, 0.3), edge(0.483, -35 * side, 0.6)]
    stick += [edge(0.525 + (flip - 0.525) * i / 6, -35 * side + 65 * side * i / 6, 0.6 + 0.4 * i / 6)
              for i in range(7)]
    stick += [edge(flip + (cancel - flip) * i / 6, 30 * side + 150 * side * i / 6) for i in range(1, 7)]
    return {"t1": 1.0, "stick": stick, "jump": [(j1, j1 + 0.042), (flip, 1.0)], "roll": [(flip + 0.033, 1.0)],
            "boost": [(0.0, 1.0)], "j1": j1, "marks": [(flip, "flip"), (cancel, "cancel")]}


def attempt_time_text(attempt):
    """Temps d'un essai : "> 2,00 s" si le tir s'est arrete avant le contact, "≈ 1,98 s" si le contact est
    deduit (precis a 0,05 s pres), sinon le temps exact."""
    if attempt["miss"]:
        return "> " + seconds_text(attempt["dt"])
    return ("" if attempt.get("exact", True) else "≈ ") + seconds_text(attempt["dt"])


def flip_card_info(attempt, record=None):
    """Textes de la carte affichee sur l'overlay apres un essai du defi (designs.render_flip_card)."""
    if attempt["miss"]:  # temps du tir ecoule : "> 2,00 s", pas un vrai temps de contact
        title, state, diff = T("dr_miss").upper(), "miss", T("gap_miss")
    else:
        title, state, diff = T("tr_" + attempt["spawn"]).upper(), kick_grade(attempt), kick_gap_text(attempt)
        if record is not None:  # record battu de `record` secondes
            gain = f"{record:.2f}".replace(".", "," if lang() == "fr" else ".")  # tiret simple, sans unite (titre en majuscules)
            title += " · " + T("dr_record_card", d=gain).upper()
    cells = flip_cells(attempt["flip"])
    return {"title": title, "time": attempt_time_text(attempt), "diff": diff, "state": state,
            # Coup de stick, delai du flip, air roll, boost : le saut, l'angle et le cancel sont en jauges
            "cells": [(label.upper(), value, note) for label, value, note in (cells[i] for i in (0, 2, 5, 6))],
            "gauges": flip_gauges(attempt["flip"]), "advices": flip_advices(attempt["flip"])}


def seconds_text(value):
    text = f"{value:.2f} s"
    return text.replace(".", ",") if lang() == "fr" else text


# --------------------------------------------------------------------------
# Guides
# --------------------------------------------------------------------------
# "skill" : mecanique dont le joueur peut noter sa progression ; "level" : 0 debutant a 3 expert

GUIDES = [
    {"key": "kick_positions", "group": "kick", "level": 0,
     "title": ("Positions de départ", "Kickoff spawns"),
     "query": ("rocket league tuto engagement positions", "rocket league kickoff spawns guide"),
     "body": ("""Il y a trois positions de départ, chacune en double (gauche et droite) sauf celle du centre. La position décide de qui y va en équipe et de la technique à utiliser.
## Diagonale
La plus proche du ballon : c'est elle qui arrive en premier. Boost dès le GO et vise un speed flip (ou un flip avant si tu débutes).
- Prends un angle très léger pour frapper le ballon un peu décentré : il part sur un côté au lieu de revenir vers toi.
## Décalée
Un peu plus loin, presque dans l'axe. Le trajet est presque droit : un speed flip ou deux flips avant marchent bien.
## Centre
La plus loin du ballon. En 1v1, c'est souvent la place où l'adversaire arrive le premier si tu ne te dépêches pas : boost tout du long et un speed flip font la différence.
> Le temps mesuré par l'app dépend beaucoup de la position : compare tes temps sur une même position.""",
              """There are three spawns, each one doubled (left and right) except the back center one. Your spawn decides who goes in a team and which technique to use.
## Diagonal
The closest to the ball: whoever spawns here gets there first. Boost from GO and aim for a speed flip (or a front flip if you are learning).
- Take a very slight angle to hit the ball a bit off-center: it goes to one side instead of coming back at you.
## Off-center
A bit further, almost straight on. The path is nearly straight: a speed flip or two front flips work well.
## Back center
The furthest from the ball. In 1v1, this is where the opponent often gets there first if you don't hurry: boosting all the way and a speed flip make the difference.
> The time measured by the app depends a lot on your spawn: compare your times from the same spawn.""")},

    {"key": "speedflip", "group": "kick", "level": 2, "skill": True,
     "title": ("Speed flip", "Speed flip"),
     "query": ("rocket league tuto speed flip", "rocket league speed flip tutorial"),
     "body": ("""Le flip le plus rapide du jeu : la voiture part en diagonale mais ne bascule pas, elle garde sa vitesse. C'est l'engagement des bons joueurs, et il sert aussi pour arriver vite sur un ballon au sol.
## Avant de commencer
- Assigne l'air roll gauche et l'air roll droite à des touches (Paramètres > Commandes). Ce sera aussi utile pour le half flip et les aériens.
## Les étapes (exemple : flip vers la gauche)
Timings du plugin BakkesMod SpeedFlipTrainer et de son speed flip enregistré : le jeu calcule à 120 ticks par seconde.
1. Accélère et boost dès le départ. Garde le boost jusqu'au contact.
2. Vers 0,5 s (entre 0,46 et 0,58 s après le départ), décale légèrement le stick en haut à droite, vers 35° de la verticale (« 1 h »), sans aller à fond : juste un petit décalage, pour tourner à peine. Saute dans la foulée : le stick doit encore être décalé au moment du saut. Appui court sur le saut.
3. Sans relâcher le stick, fais-le passer par le haut jusqu'en haut à gauche : environ 30° de la verticale (entre 22 et 38°), vers « 11 h ». Deuxième saut à ce moment, environ 90 ms après le premier.
4. Continue le même mouvement le long du bord : vers la gauche, puis tout en bas. C'est le flip cancel : stick tiré à fond vers l'arrière moins de 60 ms après le flip (le plugin tolère jusqu'à 90 ms). Garde-le en bas jusqu'à l'atterrissage.
5. Juste après le flip (environ 30 ms), appuie sur l'air roll gauche, du même côté que le flip, et garde-le jusqu'à l'atterrissage.
6. Atterris sur les roues, toujours en boost, puis flip avant dans le ballon à environ une longueur de voiture.
> Le stick fait donc un seul geste : petit décalage vers « 1 h », « 11 h », gauche, bas, sans repasser au centre. Un virage trop fort au départ fait partir la voiture de travers et passer à côté du ballon. Pour un flip à droite, inverse tout : décalage vers « 11 h », flip vers « 1 h », puis vers le bas par la droite, air roll droite.
## S'entraîner pas à pas
Si tu ne touches jamais le ballon, n'enchaîne pas tout d'un coup : ajoute un geste à la fois, et passe au suivant quand le précédent marche presque à chaque fois.
1. Entraînement libre, sans ballon, en ligne droite : saut, flip en diagonale et cancel en un seul arc de stick. La voiture doit rester presque à plat.
2. Ajoute l'air roll, jusqu'à atterrir sur les roues à chaque fois.
3. Ajoute le petit décalage du stick vers « 1 h » au moment du premier saut, puis le boost.
4. Seulement ensuite, l'engagement : pack d'entraînement personnalisé sans limite de temps, pour finir chaque essai jusqu'au ballon.
- Le guide du speed flip sur l'overlay (clic droit sur l'overlay) montre ton stick en direct à côté du geste conseillé.
- Match d'exhibition contre des bots ou match privé : chaque but relance un engagement, et l'app te donne ton temps dans « Tes engagements ».
- Le plugin BakkesMod « SpeedFlipTrainer » (hors ligne, sans lien avec RL Stats) analyse chaque tentative.""",
              """The fastest flip in the game: the car goes diagonally but does not tip over, so it keeps its speed. It is how good players take kickoffs, and it also helps you reach a ball on the ground quickly.
## Before you start
- Bind air roll left and air roll right (Settings > Controls). You will also need them for the half flip and aerials.
## Steps (example: flip to the left)
Timings from the BakkesMod plugin SpeedFlipTrainer and its recorded speed flip: the game runs at 120 ticks per second.
1. Throttle and boost from the start. Keep boosting until you touch the ball.
2. At about 0.5 s (between 0.46 and 0.58 s after the start), shift the stick slightly up-right, about 35° from vertical ("1 o'clock"), not all the way: just a small offset, to barely turn. Jump right away: the stick must still be offset when you jump. Short press on jump.
3. Without letting go, move it over the top to the top left: about 30° from vertical (22 to 38°), toward "11 o'clock". Second jump at that moment, about 90 ms after the first one.
4. Keep the same motion along the edge: to the left, then all the way down. That is the flip cancel: stick fully back less than 60 ms after the flip (the plugin accepts up to 90 ms). Keep it down until you land.
5. Right after the flip (about 30 ms), press air roll left, on the same side as the flip, and hold it until you land.
6. Land on your wheels, still boosting, then front flip into the ball about one car length away.
> So the stick makes one single motion: small offset toward "1 o'clock", "11 o'clock", left, down, without going back through the center. Turning too much at the start sends the car sideways past the ball. To flip right, mirror everything: offset toward "11 o'clock", flip toward "1 o'clock", then down through the right, air roll right.
## Practice step by step
If you never reach the ball, don't chain everything at once: add one move at a time, and move on when the previous one works almost every time.
1. Free play, no ball, in a straight line: jump, diagonal flip and cancel in one single stick arc. The car should stay almost flat.
2. Add air roll, until you land on your wheels every time.
3. Add the small stick offset toward "1 o'clock" as you do the first jump, then boost.
4. Only then, the kickoff: a custom training pack without a time limit, so every attempt goes all the way to the ball.
- The speed flip guide on the overlay (right-click the overlay) shows your live stick next to the recommended motion.
- Exhibition against bots or private match: every goal restarts a kickoff, and the app gives you your time in "Your kickoffs".
- The BakkesMod plugin "SpeedFlipTrainer" (offline, unrelated to RL Stats) analyzes every attempt.""")},

    {"key": "frontflip", "group": "kick", "level": 0, "skill": True,
     "title": ("Engagement classique (flip avant)", "Classic kickoff (front flip)"),
     "query": ("rocket league tuto engagement rapide débutant", "rocket league fast kickoff beginner"),
     "body": ("""L'engagement à apprendre en premier. Plus lent qu'un speed flip, mais bien plus rapide que d'arriver en roulant.
## Les étapes
1. Accélère et boost dès le GO.
2. À peu près à mi-chemin, fais un flip avant pour prendre de la vitesse. Garde le boost en l'air et à l'atterrissage.
3. À environ une longueur de voiture du ballon, saute et flip avant dans le ballon.
> Arriver sans flip final donne un contact mou : l'adversaire gagne presque à coup sûr.
## Bien viser
- Frappe le ballon un peu décentré pour l'envoyer sur un côté du terrain adverse plutôt que vers ton but.
- Après l'engagement, va chercher un gros boost dans un coin : tu en as dépensé beaucoup.""",
              """The first kickoff to learn. Slower than a speed flip, but much faster than driving in.
## Steps
1. Throttle and boost from GO.
2. About halfway, front flip to gain speed. Keep boosting in the air and when you land.
3. About one car length from the ball, jump and front flip into it.
> Arriving without a final flip gives a soft touch: the opponent almost always wins.
## Aim
- Hit the ball a bit off-center to send it to one side of the opponent's half rather than toward your goal.
- After the kickoff, grab a big boost in a corner: you used a lot.""")},

    {"key": "kick_fake", "group": "kick", "level": 1,
     "title": ("Feinte et engagement retardé", "Fake and delayed kickoffs"),
     "query": ("rocket league tuto fake kickoff", "rocket league fake kickoff delay guide"),
     "body": ("""Aller vite ne suffit pas : varier ses engagements empêche l'adversaire de prévoir.
## La feinte (fake)
Tu ne vas pas au ballon, ou tu prends juste un petit boost, et tu restes prêt à défendre.
- Utile en 1v1 contre un joueur qui frappe fort : sa frappe arrive vers toi, et toi tu as du boost.
- Risque : s'il touche doucement le ballon, il le récupère tout près de ton but.
## L'engagement retardé (delay)
Tu pars normalement, mais tu arrives une fraction de seconde après l'adversaire, pour réagir à sa frappe au lieu de faire un 50/50 à l'aveugle.
- Ne freine pas trop : si tu arrives trop tard, c'est une feinte ratée.
> Change de technique de temps en temps : un adversaire qui sait ce que tu vas faire gagne plus d'engagements.""",
              """Being fast is not enough: mixing up your kickoffs keeps the opponent guessing.
## The fake
You don't go for the ball, or you only grab a small pad, and stay ready to defend.
- Useful in 1v1 against a player who hits hard: the ball comes your way, and you have boost.
- Risk: if they touch it softly, they take it right in front of your goal.
## The delayed kickoff
You leave as usual but reach the ball a split second after the opponent, so you react to their hit instead of a blind 50/50.
- Don't slow down too much: if you arrive too late, it is just a failed fake.
> Switch techniques from time to time: an opponent who knows what you will do wins more kickoffs.""")},

    {"key": "kick_team", "group": "kick", "level": 0,
     "title": ("En équipe : qui y va ?", "In a team: who goes?"),
     "query": ("rocket league tuto engagement 2v2 3v3 rotation", "rocket league 2v2 3v3 kickoff positioning"),
     "body": ("""En 2v2 et 3v3, un seul joueur va au ballon. Le savoir à l'avance évite les doubles engagements et les buts gratuits.
## Qui va au ballon
- Le joueur en diagonale y va.
- Si deux joueurs sont en diagonale, l'usage veut que celui de gauche y aille.
- Annonce-le avec le chat rapide (« J'y vais ! ») si tu as un doute.
## Les autres
- 2v2 : le deuxième avance un peu vers le milieu (« cheat ») pour reprendre le ballon s'il sort de votre côté, sans laisser le but vide.
- 3v3 : le deuxième avance comme en 2v2, le troisième va prendre un gros boost dans un coin de votre camp et reste en défense.
> Si l'adversaire gagne nettement l'engagement, le joueur qui avançait doit vite revenir défendre.""",
              """In 2v2 and 3v3, only one player goes for the ball. Knowing who in advance avoids double commits and free goals.
## Who goes
- The diagonal player goes.
- If two players spawn diagonal, the usual rule is that the left one goes.
- Call it with quick chat ("I got it!") if in doubt.
## The others
- 2v2: the second player moves up a bit toward midfield ("cheat") to pick up the ball if it comes out on your side, without leaving the goal open.
- 3v3: the second player moves up like in 2v2, the third grabs a big boost in one of your corners and stays back.
> If the opponents clearly win the kickoff, the player who moved up must get back to defend quickly.""")},

    {"key": "halfflip", "group": "mech", "level": 1, "skill": True,
     "title": ("Half flip", "Half flip"),
     "query": ("rocket league tuto half flip", "rocket league half flip tutorial"),
     "body": ("""Un demi-tour très rapide quand tu roules dans le mauvais sens. Indispensable pour revenir en défense sans faire un grand virage.
## Les étapes
1. Roule en marche arrière, le ballon (ou ton but) derrière toi.
2. Saute, puis fais un backflip (stick vers l'arrière et deuxième saut).
3. Quand l'avant de la voiture monte, à peu près au milieu de la rotation, pousse le stick vers l'avant pour annuler le flip.
4. Maintiens l'air roll (gauche ou droite) pour faire pivoter la voiture et la remettre sur ses roues.
5. Atterris en avançant et boost aussitôt.
> Commence lentement, en décomposant : backflip, annulation, puis air roll. La vitesse vient ensuite.
## S'entraîner
- Entraînement libre : roule en marche arrière vers ton but et fais un half flip vers le ballon, encore et encore.""",
              """A very quick turnaround when you are driving the wrong way. Essential to get back on defense without a wide turn.
## Steps
1. Drive in reverse, with the ball (or your goal) behind you.
2. Jump, then backflip (stick back and second jump).
3. When the front of the car rises, about halfway through the rotation, push the stick forward to cancel the flip.
4. Hold air roll (left or right) to spin the car back onto its wheels.
5. Land driving forward and boost right away.
> Start slowly, one piece at a time: backflip, cancel, then air roll. Speed comes later.
## Practice
- Free play: reverse toward your goal and half flip toward the ball, over and over.""")},

    {"key": "wavedash", "group": "mech", "level": 1, "skill": True,
     "title": ("Wavedash", "Wavedash"),
     "query": ("rocket league tuto wavedash", "rocket league wavedash tutorial"),
     "body": ("""Un flip au moment où les roues touchent le sol : la voiture glisse et gagne de la vitesse sans boost. Pratique aussi pour repartir vite après un saut ou une chute.
## Les étapes
1. Saute (petit saut), ou tombe d'un mur.
2. Lève légèrement le nez de la voiture pour que les roues arrière touchent le sol en premier.
3. Juste au moment où les roues touchent, fais un flip (avant ou sur le côté).
> Trop tôt, tu fais un flip normal en l'air ; trop tard, il ne se passe rien. Le bon moment est très court.
## S'entraîner
- Entraînement libre : enchaîne les wavedashes en ligne droite sans boost.
- Ensuite, fais-en un à chaque fois que tu retombes d'un mur.""",
              """A flip right as your wheels touch the ground: the car slides and gains speed without boost. Also handy to get going again after a jump or a fall.
## Steps
1. Jump (small jump), or drop off a wall.
2. Tilt the nose up slightly so the rear wheels touch the ground first.
3. Right as the wheels touch, flip (forward or sideways).
> Too early and you do a normal flip in the air; too late and nothing happens. The window is very short.
## Practice
- Free play: chain wavedashes in a straight line without boost.
- Then do one every time you come down from a wall.""")},

    {"key": "recovery", "group": "mech", "level": 0, "skill": True,
     "title": ("Air roll et réception", "Air roll and recoveries"),
     "query": ("rocket league tuto air roll recovery", "rocket league air roll recovery tutorial"),
     "body": ("""Après un saut, un contact ou une démo évitée de justesse, retomber vite sur ses roues et dans la bonne direction fait gagner beaucoup de temps.
## Les bases
- Utilise l'air roll pour tourner la voiture et atterrir sur les roues : atterrir sur le toit ou sur le côté fait perdre une à deux secondes.
- Pendant la chute, oriente déjà l'avant de la voiture vers l'action.
- En retombant, un wavedash permet de repartir immédiatement.
> Évite les grands mouvements de stick : les corrections trop fortes sont l'erreur la plus courante.
## S'entraîner
- Entraînement libre : saute et pars dans tous les sens, puis force-toi à atterrir face au but adverse.""",
              """After a jump, a touch or a near demo, getting back on your wheels quickly and facing the right way saves a lot of time.
## Basics
- Use air roll to turn the car and land on your wheels: landing on your roof or side costs one or two seconds.
- While falling, already point the front of the car toward the play.
- When you land, a wavedash gets you going instantly.
> Avoid big stick movements: overcorrecting is the most common mistake.
## Practice
- Free play: jump and spin in every direction, then make yourself land facing the opponent's goal.""")},

    {"key": "ceiling", "group": "mech", "level": 2, "skill": True,
     "title": ("Ceiling shot", "Ceiling shot"),
     "query": ("rocket league tuto ceiling shot", "rocket league ceiling shot tutorial"),
     "body": ("""Tu montes au plafond, tu te laisses tomber et tu frappes le ballon avec ton flip. Le flip est gardé car tu quittes le plafond sans sauter.
## Les étapes
1. Monte au mur en poussant le ballon devant toi, puis continue jusqu'au plafond.
2. Une fois les quatre roues au plafond, relâche l'accélérateur pour te décrocher : la voiture tombe.
3. Tombe vers le ballon (boost si besoin) et utilise ton flip pour le frapper au bon moment.
> Le plus dur est de bien placer le ballon en montant au mur : il doit retomber là où tu vas tomber.
## S'entraîner
- Entraînement libre : d'abord monter au plafond et se décrocher proprement, sans ballon.""",
              """You drive up to the ceiling, drop off and hit the ball with your flip. You keep the flip because you leave the ceiling without jumping.
## Steps
1. Drive up the wall pushing the ball in front of you, then keep going up to the ceiling.
2. With all four wheels on the ceiling, let go of the throttle to drop off: the car falls.
3. Fall toward the ball (boost if needed) and use your flip to hit it at the right moment.
> The hard part is setting the ball up as you drive up the wall: it must come down where you will fall.
## Practice
- Free play: first just drive up to the ceiling and drop off cleanly, without the ball.""")},

    {"key": "musty", "group": "mech", "level": 3, "skill": True,
     "title": ("Musty flick", "Musty flick"),
     "query": ("rocket league tuto musty flick", "rocket league musty flick tutorial"),
     "body": ("""Un flick par backflip, du nom du joueur Musty qui l'a inventé : l'avant de la voiture frappe le ballon par en dessous et l'envoie haut et vers l'avant, souvent par-dessus l'adversaire.
## Les étapes
1. Mets le ballon en l'air devant toi : petit pop, ou ballon posé sur le capot en dribble.
2. Saute, puis baisse le nez de la voiture pour passer sous le ballon.
3. Fais un backflip (stick vers l'arrière et deuxième saut) : en tournant, l'avant de la voiture remonte et frappe le ballon.
> Tout se joue sur la position : le ballon doit être au-dessus de l'avant de la voiture au moment du backflip.
## Prérequis
- Savoir contrôler le ballon sur le capot (dribble) ou le soulever proprement.""",
              """A backflip flick named after Musty, the player who invented it: the front of the car hits the ball from below and sends it high and forward, often over the opponent.
## Steps
1. Get the ball in the air in front of you: a small pop, or the ball on your hood while dribbling.
2. Jump, then tilt the nose down to get under the ball.
3. Backflip (stick back and second jump): as the car rotates, its front swings up and hits the ball.
> It is all about position: the ball must be above the front of the car when you backflip.
## Requirements
- Being able to carry the ball on your hood (dribbling) or pop it up cleanly.""")},

    {"key": "breezi", "group": "mech", "level": 3, "skill": True,
     "title": ("Breezi flick", "Breezi flick"),
     "query": ("rocket league tuto breezi flick", "rocket league breezi flick tutorial"),
     "body": ("""Un musty flick précédé d'une rotation en « tornade », du nom du joueur Breezi. La rotation garde la voiture alignée sous le ballon et rend le flick plus dur à lire.
## Les étapes
1. Maîtrise d'abord le musty flick.
2. Mets le ballon en l'air devant toi et saute.
3. Maintiens l'air roll et fais tourner le stick en cercle : la voiture tourne en tornade sous le ballon.
4. Quand l'avant de la voiture est sous le ballon, fais le backflip comme pour un musty.
> Variante plus facile : relâche l'air roll et place la voiture à la main en position de musty avant le backflip.""",
              """A musty flick with a "tornado" spin first, named after the player Breezi. The spin keeps the car lined up under the ball and makes the flick harder to read.
## Steps
1. Master the musty flick first.
2. Get the ball in the air in front of you and jump.
3. Hold air roll and move the stick in a circle: the car spins like a tornado under the ball.
4. When the front of the car is under the ball, backflip like a musty.
> Easier variant: let go of air roll and steer the car into the musty position by hand before the backflip.""")},

    {"key": "flipreset", "group": "mech", "level": 3, "skill": True,
     "title": ("Flip reset", "Flip reset"),
     "query": ("rocket league tuto flip reset", "rocket league flip reset tutorial"),
     "body": ("""Quand les quatre roues touchent le ballon en l'air, tu récupères un flip. Tu peux t'en servir pour une frappe que le défenseur n'attend pas.
## Les étapes
1. En aérien, arrive sous le ballon et tourne le dessous de la voiture vers lui avec l'air roll.
2. Touche le ballon avec les quatre roues en même temps (contact doux, pas une frappe).
3. Tu as de nouveau un flip : garde le boost, suis le ballon et flip dedans au bon moment.
> Prérequis : des aériens et un air roll solides. Commence par réussir le contact des roues, le tir viendra après.""",
              """When all four wheels touch the ball in the air, you get your flip back. You can use it for a shot the defender doesn't expect.
## Steps
1. In an aerial, get under the ball and turn the underside of the car toward it with air roll.
2. Touch the ball with all four wheels at once (a soft touch, not a hit).
3. You have a flip again: keep boosting, follow the ball and flip into it at the right moment.
> Requirements: solid aerials and air roll. Learn the wheel contact first, the shot comes later.""")},
]


DRILL_HELP = ("""## Comment s'entraîner
1. Entraînement > Entraînement personnalisé : lance un pack d'engagements (voiture sur les vraies positions de départ, ballon au centre).
2. Le chrono part à ton premier mouvement et s'arrête au contact avec le ballon. L'app reconnaît la position de départ à la distance que ta voiture a parcourue.
3. Après chaque tir, l'overlay affiche ton temps et sa couleur : or si ton speed flip est parfait, vert s'il te fait gagner du temps, orange si tu es presque au temps sans flip, rouge si tu es plus lent.
- Ça marche aussi en match privé ou d'exhibition contre des bots : le chrono part alors au GO.
> Les packs avec une limite de temps (2 s pour celui de Musty) arrêtent le tir avant le contact s'il est trop lent : l'app le compte comme « pas touché ».
- Le vert commence au temps qu'on met en boostant tout droit, sans flip : au-dessus, ton flip te fait perdre du temps. Un speed flip parfait (en or) est environ 0,1 s plus rapide.
## Lire la frise de tes inputs
Sous ton dernier speed flip (et sur la carte de l'overlay), chaque ligne montre un input dans le temps, du départ au cancel. Un bon speed flip vers la gauche ressemble à ça, de gauche à droite :
1. Boost : la barre orange commence à 0 et ne s'arrête plus.
2. Stick G / D : monte un peu (petit décalage à droite) juste avant le premier saut, sans aller tout en haut, puis redescend en passant par le centre.
3. Saut : un premier appui court vers 0,5 s, puis le deuxième environ 90 ms après (trait FLIP).
4. Au trait FLIP, le stick G / D descend vers la gauche et le stick av. / arr. monte : c'est le flip en diagonale.
5. Moins de 60 ms après (trait CANCEL), le stick av. / arr. arrive tout en bas et y reste, pendant que le stick G / D passe par la gauche.
6. Air roll (gauche, côté du flip) : la barre violette commence environ 30 ms après le trait FLIP et dure jusqu'à l'atterrissage.
> Le geste parfait est dessiné en pointillés clairs sur ta frise : le premier input qui s'en écarte est celui à travailler. Les conseils sous les mesures le disent aussi, du plus important au moins important.""",
              """## How to practice
1. Training > Custom training: load a kickoff pack (car on the real kickoff spawns, ball in the center).
2. The timer starts on your first movement and stops when you touch the ball. The app recognizes your spawn from the distance your car traveled.
3. After each shot, the overlay shows your time and its color: gold when your speed flip is perfect, green when it saves time, orange when you are close to the no-flip time, red when you are slower.
- It also works in private matches or exhibitions against bots: the timer then starts at GO.
> Packs with a time limit (2 s in Musty's pack) end the shot before contact if you are too slow: the app counts it as "missed".
- Green starts at the time it takes to boost straight without a flip: above it, your flip loses time. A perfect speed flip (in gold) is about 0.1 s faster.
## Reading your input timeline
Under your latest speed flip (and on the overlay card), each line shows one input over time, from the start to the cancel. A good speed flip to the left looks like this, from left to right:
1. Boost: the orange bar starts at 0 and never stops.
2. Stick L / R: goes up a little (small offset to the right) just before the first jump, not all the way, then comes down through the center.
3. Jump: a short first press at about 0.5 s, then the second one about 90 ms later (FLIP line).
4. At the FLIP line, stick L / R drops to the left and stick fwd / back goes up: that is the diagonal flip.
5. Less than 60 ms later (CANCEL line), stick fwd / back reaches the bottom and stays there, while stick L / R goes through the left.
6. Air roll (left, the flip side): the purple bar starts about 30 ms after the FLIP line and lasts until you land.
> The perfect motion is drawn in light dotted lines on your timeline: the first input that drifts from it is the one to work on. The tips under the measures say it too, most important first.""")


# --------------------------------------------------------------------------
# Fenetre
# --------------------------------------------------------------------------

class PadSetup:
    """Fenetre "Boutons de la manette" : un bouton Changer par action (on appuie ensuite sur le bouton de la
    manette), Tout regler (les actions une par une), Reinitialiser. Ouverte depuis le menu, les Parametres ou la
    fenetre Entrainement, et toute seule quand les boutons n'ont jamais ete indiques (quiet : en jeu, sans
    prendre le focus ; la manette est lue quand meme et tout se regle d'affilee, sans souris)."""

    WAIT = 8  # secondes pour appuyer sur chaque bouton

    def __init__(self, app, quiet=False):
        self.app = app
        self.quiet = quiet
        self.capturing = None  # action dont on attend le bouton
        self.queue = []  # actions restantes de "Tout regler"
        self.all_done = False  # "Tout regler" lance : en jeu (quiet), la fenetre se ferme a la fin
        self.gen = 0  # capture en cours : les anciennes boucles s'arretent
        self.connected = app.pad.connected
        self.win = tk.Toplevel(app.root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=WARN)
        self.body = tk.Frame(self.win, bg=PANEL)
        self.body.pack(fill="both", expand=True, padx=2, pady=2)
        self.build()
        self._show(quiet)
        if quiet:
            self.capture_all()
        self.watch()

    def build(self):
        for child in self.body.winfo_children():
            child.destroy()
        body, connected = self.body, self.app.pad.connected
        title = T("pad_title" if self.app.pad_ready() else "pad_setup_title")
        tk.Label(body, text=title, bg=PANEL, fg=WARN, font=TITLE_FONT, anchor="w").pack(fill="x", padx=18,
                                                                                         pady=(14, 4))
        tk.Label(body, text=T("pad_setup_text"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w",
                 justify="left", wraplength=460).pack(fill="x", padx=18)
        tk.Label(body, text=T("pad_ok" if connected else "pad_missing"), bg=PANEL, fg=OK if connected else WARN,
                 font=("Segoe UI", 9), anchor="w", justify="left", wraplength=460).pack(fill="x", padx=18,
                                                                                       pady=(8, 0))
        grid = tk.Frame(body, bg=PANEL)
        grid.pack(fill="x", padx=14, pady=(10, 2))
        grid.columnconfigure(1, weight=1)
        bindings = self.app.store["pad"]
        for row, action in enumerate(PAD_ACTIONS):
            waiting = self.capturing == action
            tk.Label(grid, text=T("pad_" + action), bg=PANEL, fg=WARN if waiting else FG, font=BODY_FONT,
                     width=16, anchor="w").grid(row=row, column=0, sticky="w", padx=4, pady=2)
            tk.Label(grid, text=T("pad_press") if waiting else bindings.get(action) or "–", bg=PANEL,
                     fg=WARN if waiting else FG, font=("Bahnschrift SemiBold", 11),
                     anchor="w").grid(row=row, column=1, sticky="w")
            if connected and not waiting:
                _button(grid, T("pad_change"), lambda a=action: self.capture(a), bg=EDGE).grid(
                    row=row, column=2, sticky="e", padx=4, pady=2)
        tk.Label(body, text=T("pad_setup_skip"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w",
                 justify="left", wraplength=460).pack(fill="x", padx=18, pady=(4, 0))
        step = ""
        if self.capturing and self.all_done:  # "Tout regler" : ou on en est
            step = T("pad_setup_step", i=PAD_ACTIONS.index(self.capturing) + 1, n=len(PAD_ACTIONS),
                     action=T("pad_" + self.capturing))
        self.step = tk.Label(body, text=step, bg=PANEL, fg=WARN if step else OK, font=("Bahnschrift SemiBold", 13))
        self.step.pack(pady=(4, 0))
        buttons = tk.Frame(body, bg=PANEL)
        buttons.pack(fill="x", padx=18, pady=(6, 14))
        _button(buttons, T("pad_ok_button"), self.done, bg=EDGE).pack(side="right")
        if connected:
            _button(buttons, T("pad_setup_start"), self.capture_all, bg=EDGE).pack(side="left")
        _button(buttons, T("pad_reset"), self.reset, bg=BG).pack(side="left", padx=(8, 0))

    def _show(self, quiet):
        """En haut du jeu, centree. quiet : affichee sans devenir la fenetre active (le jeu garde le focus)."""
        self.win.update_idletasks()
        w, h = 520, self.win.winfo_reqheight()
        vx, vy, vw, vh = self.app.viewport
        self.win.geometry(f"{w}x{h}+{vx + (vw - w) // 2}+{vy + vh // 6}")
        if quiet:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
                user32.SetWindowLongW(hwnd, -20, user32.GetWindowLongW(hwnd, -20) | 0x08000000)  # WS_EX_NOACTIVATE
                user32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
                return
            except (AttributeError, OSError):
                pass
        self.win.deiconify()
        self.win.lift()

    def refresh(self):
        """Reconstruit le contenu, hauteur ajustee."""
        if not self.win.winfo_exists():
            return
        self.build()
        self.win.update_idletasks()
        x, y = self.win.winfo_x(), self.win.winfo_y()
        self.win.geometry(f"520x{self.win.winfo_reqheight()}+{x}+{y}")

    def watch(self):
        """Manette branchee ou debranchee pendant que la fenetre est ouverte."""
        if not self.win.winfo_exists():
            return
        if self.app.pad.connected != self.connected:
            self.connected = self.app.pad.connected
            self.refresh()
        self.win.after(500, self.watch)

    def capture(self, action):
        """Attend le prochain bouton presse pour `action` (8 s ; Back / View : aucun ; sans appui : garde)."""
        if not self.app.pad.connected:
            return
        self.gen += 1
        self.capturing = action
        self.refresh()
        gen, deadline, before = self.gen, time_now() + self.WAIT, self.app.pad.held()
        self.win.after(30, lambda: self.poll(gen, action, deadline, before))

    def poll(self, gen, action, deadline, before):
        if gen != self.gen or not self.win.winfo_exists():
            return
        held = self.app.pad.held()
        new = held - before  # un bouton deja enfonce ne compte pas : il faut un nouvel appui
        if not (new or time_now() > deadline):
            self.win.after(30, lambda: self.poll(gen, action, deadline, before & held))
            return
        if new:
            bindings = dict(self.app.store["pad"])
            pressed = sorted(new)[0]
            bindings[action] = "" if pressed == "Back" else pressed
            self.app.set_option("pad", bindings)
        self.capturing = None
        if self.queue:
            self.capture(self.queue.pop(0))
            return
        self.app.set_option("pad_checked", True)
        self._changed()
        self.refresh()
        if self.all_done:
            self.all_done = False
            self.step.configure(text=T("pad_setup_done"))
            if self.quiet:
                self.win.after(1500, self.close)

    def capture_all(self):
        """Toutes les actions une par une (marche a la manette seule)."""
        if not self.app.pad.connected:
            return
        self.queue = list(PAD_ACTIONS[1:])
        self.all_done = True
        self.capture(PAD_ACTIONS[0])

    def reset(self):
        """Boutons par defaut, puis on les redemande tous."""
        self.queue, self.capturing, self.all_done = [], None, False
        self.gen += 1
        self.app.set_option("pad", dict(pad.DEFAULT_BINDINGS))
        self.app.set_option("pad_checked", False)
        self._changed()
        self.refresh()
        self.capture_all()

    def done(self):
        """OK : les boutons affiches sont les bons (meme ceux par defaut)."""
        self.app.set_option("pad_checked", True)
        self._changed()
        self.close()

    def _changed(self):
        if self.app.training_window:
            self.app.training_window.show()

    def close(self):
        self.gen += 1
        self.app.pad_popup = None
        if self.win.winfo_exists():
            self.win.destroy()


class TrainingWindow:
    def __init__(self, app):
        self.app = app
        self.page = "kick_drill"
        self.replay_speed = 0.25  # vitesse de l'animation du stick (dernier essai et reference)
        self.replay_gen = 0  # animation en cours : les anciennes s'arretent quand la page est reconstruite
        self.win = _dark_window(app.root, T("tr_title"), (940, 680), app.viewport)
        self.win.minsize(780, 520)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.build()

    def close(self):
        self.app.training_window = None
        self.win.destroy()

    def refresh(self):
        """Appele a chaque engagement : seule la page Engagement rapide change."""
        if self.page == "kick_drill":
            top = self.canvas.yview()[0]
            self.show()
            self.canvas.yview_moveto(top)

    def build(self):
        for child in self.win.winfo_children():
            child.destroy()
        self.nav = tk.Frame(self.win, bg=BG, width=230)
        self.nav.pack(side="left", fill="y", padx=(14, 0), pady=14)
        self.nav.pack_propagate(False)

        right = tk.Frame(self.win, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)
        self.canvas = tk.Canvas(right, bg=BG, highlightthickness=0)
        self.bar = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview,
                                 style="Dark.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self._scrolled)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.content = None
        self.content_id = self.canvas.create_window(0, 0, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self._resized(e.width))
        self.win.bind("<MouseWheel>", self._wheel)
        self.wrapped = []  # labels dont la largeur suit celle de la fenetre
        self.show()

    def _resized(self, width):
        self.canvas.itemconfigure(self.content_id, width=width)
        for label, margin in self.wrapped:
            label.configure(wraplength=max(200, width - margin))

    def _scrolled(self, first, last):
        """Barre de defilement visible seulement quand la page depasse."""
        if float(first) <= 0 and float(last) >= 1:
            self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y", before=self.canvas)
        self.bar.set(first, last)

    def _wheel(self, e):
        if self.content and self.content.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def set_page(self, key):
        self.page = key
        self.show()
        self.canvas.yview_moveto(0)

    def show(self):
        self._fill_nav()
        # Nouvelle page construite a part puis echangee d'un coup : pas de clignotement a chaque engagement
        old, self.content = self.content, tk.Frame(self.canvas, bg=BG)
        self.content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.wrapped = []
        self.vars = []  # variables des cases a cocher : Tk les oublie si plus rien ne les reference
        if self.page == "kick_drill":
            self.show_drill()
        else:
            self.show_guide(next(g for g in GUIDES if g["key"] == self.page))
        self._resized(self.canvas.winfo_width())
        self.canvas.itemconfigure(self.content_id, window=self.content)
        if old:
            old.destroy()

    # --- Navigation ---------------------------------------------------------

    def _fill_nav(self):
        for child in self.nav.winfo_children():
            child.destroy()
        status = self.app.store["training"]
        tk.Label(self.nav, text=T("tr_beta"), bg=BG, fg=WARN, font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=210).pack(fill="x", pady=(0, 12))
        for group, title in (("kick", T("tr_kickoffs")), ("mech", T("tr_mechanics"))):
            tk.Label(self.nav, text=title.upper(), bg=BG, fg=MUTED, font=("Bahnschrift SemiBold", 10),
                     anchor="w").pack(fill="x", pady=(0 if group == "kick" else 14, 4))
            entries = [("kick_drill", T("dr_title"), None)] if group == "kick" else []
            entries += [(g["key"], self.text(g["title"]), status.get(g["key"], 0) if g.get("skill") else None)
                        for g in GUIDES if g["group"] == group]
            for key, label, state in entries:
                self._nav_button(key, label, state)

    def _nav_button(self, key, label, state):
        active = key == self.page
        row = tk.Frame(self.nav, bg=EDGE if active else BG, cursor="hand2")
        row.pack(fill="x", pady=1)
        dot = tk.Label(row, text="●" if state is not None else "", width=2, bg=row["bg"],
                       fg=STATUS_COLORS[state] if state is not None else BG, font=("Segoe UI", 8))
        dot.pack(side="left", padx=(6, 0))
        text = tk.Label(row, text=label, bg=row["bg"], fg=FG if active else MUTED, font=BODY_FONT, anchor="w")
        text.pack(side="left", fill="x", expand=True, pady=4)
        for w in (row, dot, text):
            w.bind("<Button-1>", lambda e, k=key: self.set_page(k))
            if not active:
                w.bind("<Enter>", lambda e, r=row: self._hover(r, PANEL))
                w.bind("<Leave>", lambda e, r=row: self._hover(r, BG))

    @staticmethod
    def _hover(row, color):
        for w in [row] + row.winfo_children():
            w.configure(bg=color)

    # --- Briques ------------------------------------------------------------

    @staticmethod
    def text(pair):
        return pair[0] if lang() == "fr" else pair[1]

    def _label(self, parent, text, fg=FG, font=BODY_FONT, bg=BG, margin=40, **pack):
        label = tk.Label(parent, text=text, bg=bg, fg=fg, font=font, justify="left", anchor="w")
        label.pack(fill="x", **pack)
        self.wrapped.append((label, margin))
        return label

    def _title(self, text):
        tk.Label(self.content, text=text, bg=BG, fg=FG, font=("Bahnschrift SemiBold", 18),
                 anchor="w").pack(fill="x")

    def _tiles(self, items):
        tiles = tk.Frame(self.content, bg=BG)
        tiles.pack(fill="x", pady=(10, 0))
        for col, (title, value, sub) in enumerate(items):
            tiles.grid_columnconfigure(col, weight=1, uniform="tile")
            tile = tk.Frame(tiles, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
            tile.grid(row=0, column=col, sticky="nsew", padx=(0, 6))
            for text, fg, font, pady in ((title, MUTED, ("Segoe UI", 9), (8, 0)), (value, FG, NUM_FONT, 0),
                                         (sub, MUTED, ("Segoe UI", 9), (0, 8))):
                tk.Label(tile, text=text, bg=PANEL, fg=fg, font=font, anchor="w", justify="left",
                         wraplength=130).pack(fill="x", padx=10, pady=pady)

    def _markup(self, body):
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("## "):
                tk.Label(self.content, text=line[3:], bg=BG, fg=FG, font=TITLE_FONT, anchor="w").pack(
                    fill="x", pady=(16, 4))
            elif line.startswith("> "):
                box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
                box.pack(fill="x", pady=8)
                tk.Frame(box, bg=WARN, width=4).pack(side="left", fill="y")
                self._label(box, line[2:], bg=PANEL, margin=70, padx=12, pady=8)
            elif line.startswith("- ") or line[:1].isdigit() and ". " in line[:4]:
                bullet, rest = ("•", line[2:]) if line.startswith("- ") else line.split(" ", 1)
                row = tk.Frame(self.content, bg=BG)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=bullet, bg=BG, fg=MUTED, font=("Bahnschrift SemiBold", 10), width=3,
                         anchor="ne").pack(side="left", anchor="n")
                label = tk.Label(row, text=rest, bg=BG, fg=FG, font=BODY_FONT, justify="left", anchor="w")
                label.pack(side="left", fill="x", expand=True, padx=(4, 0))
                self.wrapped.append((label, 70))
            else:
                self._label(self.content, line, pady=(4, 2))

    # --- Guides -------------------------------------------------------------

    def show_guide(self, guide):
        self._title(self.text(guide["title"]))
        head = tk.Frame(self.content, bg=BG)
        head.pack(fill="x", pady=(6, 4))
        level = guide["level"]
        tk.Label(head, text=T("tr_levels").split(",")[level].upper(), bg=BG, fg=LEVEL_COLORS[level],
                 font=("Bahnschrift SemiBold", 10)).pack(side="left")
        query = self.text(guide["query"])
        _button(head, T("tr_videos"), lambda: webbrowser.open(
            "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)), bg=PANEL).pack(
            side="right")
        if guide.get("skill"):
            self._status_chips(head, guide["key"])
        if guide["key"] == "kick_positions":
            self._spawn_map()
        self._markup(self.text(guide["body"]))

    def _status_chips(self, parent, key):
        current = self.app.store["training"].get(key, 0)
        bar = tk.Frame(parent, bg=BG)
        bar.pack(side="right", padx=(0, 12))
        for i, label in enumerate(T("tr_status").split(",")):
            active = i == current
            tk.Button(bar, text=label, command=lambda v=i: self.set_status(key, v), relief="flat", cursor="hand2",
                      bg=EDGE if active else PANEL, fg=STATUS_COLORS[i] if active else MUTED,
                      activebackground=EDGE, activeforeground=FG, font=("Bahnschrift SemiBold", 10), padx=10,
                      pady=2, bd=0).pack(side="left", padx=(0, 2))

    def set_status(self, key, value):
        status = dict(self.app.store["training"])
        status[key] = value
        self.app.store["training"] = status  # copie : l'affectation enregistre stats.json
        self.show()

    def _spawn_map(self):
        """Moitie de terrain de l'equipe bleue : positions de depart, ballon et gros boosts."""
        c = tk.Canvas(self.content, bg=PANEL, highlightthickness=1, highlightbackground=EDGE, height=280)
        c.pack(fill="x", pady=(8, 4))
        c.bind("<Configure>", lambda e: self._draw_spawns(c))

    def _draw_spawns(self, c):
        c.delete("all")
        W, H = c.winfo_width(), c.winfo_height()
        top_y, bottom_y = 600, -5120  # un peu au-dela de la ligne mediane, jusqu'a notre ligne de but
        scale = min((W - 40) / 8192, (H - 30) / (top_y - bottom_y))
        cx, cy = W / 2, 15 + top_y * scale

        def at(x, y):
            return cx + x * scale, cy - y * scale

        x0, y0 = at(-4096, top_y)
        x1, y1 = at(4096, bottom_y)
        c.create_rectangle(x0, y0, x1, y1, outline=EDGE, width=2)
        mx0, my = at(-4096, 0)
        c.create_line(mx0, my, x1, my, fill=EDGE, width=2)
        r = 1000 * scale
        c.create_oval(cx - r, my - r, cx + r, my + r, outline=GRID, width=2)
        gx0, gy = at(-893, bottom_y)
        gx1, _ = at(893, bottom_y)
        c.create_line(gx0, gy, gx1, gy, fill=self.app.store["win_color"], width=5)
        for x, y in BIG_PADS:
            px, py = at(x, y)
            c.create_oval(px - 7, py - 7, px + 7, py + 7, fill=WARN, outline="")
        px, py = at(3072, -4096)
        c.create_text(px, py + 16, text=T("tr_boost"), fill=MUTED, font=("Segoe UI", 8))
        for x, y, key in SPAWNS:
            sx, sy = at(x, y)
            c.create_line(sx, sy, cx, my, fill=GRID, dash=(4, 4), arrow="last")
            c.create_rectangle(sx - 7, sy - 10, sx + 7, sy + 10, fill="#3b82f6", outline=FG)
            side = -1 if x < 0 else 1
            c.create_text(sx + side * 14, sy, text=T(key), fill=FG, anchor="e" if x < 0 else "w",
                          font=("Segoe UI", 9))
        c.create_oval(cx - 11, my - 11, cx + 11, my + 11, fill=FG, outline=MUTED)
        c.create_text(cx + 18, my - 12, text=T("tr_ball"), fill=MUTED, anchor="w", font=("Segoe UI", 8))

    def _table(self, heads, rows):
        """Tableau [(texte, couleur)] par ligne, avec une ligne de titres."""
        table = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        table.pack(fill="x")
        for col, key in enumerate(heads):
            table.grid_columnconfigure(col, weight=1)
            tk.Label(table, text=T(key), bg=PANEL, fg=MUTED, font=("Bahnschrift SemiBold", 10), anchor="w").grid(
                row=0, column=col, sticky="we", padx=10, pady=(8, 4))
        for row, cells in enumerate(rows, start=1):
            for col, (text, color) in enumerate(cells):
                tk.Label(table, text=text, bg=PANEL, fg=color, font=BODY_FONT, anchor="w").grid(
                    row=row, column=col, sticky="we", padx=10, pady=2 if row < len(rows) else (2, 8))

    # --- Engagement rapide --------------------------------------------------

    def show_drill(self):
        self._title(T("dr_title"))
        self._label(self.content, T("dr_intro"), fg=MUTED, pady=(2, 0))
        self._pack_code()
        if self.app.pad.connected and not self.app.pad_ready():
            self._pad_setup()
        drill = self.app.store["drill"]
        records = kick_records(self.app.store)
        tiles = []
        for spawn in SPAWN_KEYS:
            tries = [a for a in drill if a["spawn"] == spawn]
            grades = [kick_grade(a) for a in tries]
            ok = sum(1 for g in grades if g in ("perfect", "good"))
            best = records[spawn]["dt"] if spawn in records else None
            tiles.append((T("tr_" + spawn), f"{round(ok * 100 / len(tries))} %" if tries else "–",
                          T("dr_tile_sub", ok=ok, n=len(tries), best=seconds_text(best) if best else "–",
                            p=grades.count("perfect"))))
        tiles.append((T("dr_missed"), str(sum(1 for a in drill if a["miss"])), T("dr_missed_sub")))
        self._tiles(tiles)

        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x", pady=(12, 0))
        tk.Label(box, text=T("dr_levels"), bg=PANEL, fg=FG, font=BODY_FONT, anchor="w").pack(
            fill="x", padx=12, pady=(8, 4))
        grid = tk.Frame(box, bg=PANEL)
        grid.pack(fill="x", padx=12)
        colors = self.grade_colors()
        heads = [("", MUTED), (T("dr_perfect"), colors["perfect"]), (T("dr_good"), colors["good"]),
                 (T("dr_close"), colors["close"]), (T("dr_slow"), colors["slow"])]
        for col, (text, color) in enumerate(heads):
            tk.Label(grid, text=text, bg=PANEL, fg=color, font=("Bahnschrift SemiBold", 11), anchor="w").grid(
                row=0, column=col, sticky="w", padx=(0, 18))
        for row, spawn in enumerate(SPAWN_KEYS, start=1):
            no_flip = NO_FLIP[spawn]
            cells = [T("tr_" + spawn), "≤ " + seconds_text(PERFECT[spawn]), "≤ " + seconds_text(no_flip),
                     "≤ " + seconds_text(no_flip + CLOSE), "> " + seconds_text(no_flip + CLOSE)]
            for col, text in enumerate(cells):
                tk.Label(grid, text=text, bg=PANEL, fg=MUTED if col == 0 else FG, font=BODY_FONT, anchor="w").grid(
                    row=row, column=col, sticky="w", padx=(0, 18))
        self._label(box, T("dr_levels_hint"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=70, padx=12,
                    pady=(6, 10))

        self._last_flip(drill)
        self._pad_box()
        self._match_timer()
        self._markup(self.text(DRILL_HELP))

        head = tk.Frame(self.content, bg=BG)
        head.pack(fill="x", pady=(16, 4))
        tk.Label(head, text=T("dr_attempts"), bg=BG, fg=FG, font=TITLE_FONT, anchor="w").pack(side="left")
        if drill:
            _button(head, T("dr_clear"), self.clear_drill, bg=PANEL).pack(side="right")
        recent = list(reversed(drill))[:15]
        if not recent:
            self._label(self.content, T("dr_none"), fg=MUTED)
            return
        win_c, loss_c = self.app.store["win_color"], self.app.store["loss_color"]
        colors = self.grade_colors()
        rows = []
        for a in recent:
            when = datetime.datetime.fromtimestamp(a["t"]).strftime("%H:%M")
            time_text = attempt_time_text(a)
            grade_colors = {"ok": win_c, "warn": WARN, "bad": loss_c, None: FG}
            flip = [(value, grade_colors[note]) for _, value, note in flip_cells(a["flip"])][3:5] \
                if a.get("flip") else [("–", MUTED)] * 2
            if a["miss"]:
                rows.append([(when, MUTED), ("–", MUTED), (time_text, FG), ("–", MUTED)] + flip
                            + [(T("dr_miss"), WARN)])
                continue
            grade = kick_grade(a)
            color = colors[grade]
            gap = diff_text(a["dt"] - PERFECT[a["spawn"]])
            rows.append([(when, MUTED), (T("tr_" + a["spawn"]), FG), (time_text, FG), (gap, color)] + flip
                        + [(T(GRADE_TEXTS[grade]), color)])
        self._table(("tr_col_time", "dr_col_spawn", "tr_col_dt", "dr_col_diff", "pf_angle", "pf_cancel",
                     "tr_col_result"), rows)

    # --- Speed flip (manette) -----------------------------------------------

    def _last_flip(self, drill):
        """Mesures du dernier speed flip, trajet du stick, et reperes tires des essais les plus rapides."""
        tk.Label(self.content, text=T("pf_last"), bg=BG, fg=FG, font=TITLE_FONT, anchor="w").pack(
            fill="x", pady=(16, 4))
        last = self.app.last_flip
        if not last:
            self._label(self.content, T("pf_none"), fg=MUTED)
            self._replay(None)
            self._timeline(None)
            return
        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x")
        stick = tk.Canvas(box, bg=PANEL, highlightthickness=0, width=170, height=170)
        stick.pack(side="left", padx=10, pady=10)
        self._draw_stick(stick, last)
        right = tk.Frame(box, bg=PANEL)
        right.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=10)
        cells = tk.Frame(right, bg=PANEL)
        cells.pack(fill="x")
        win_c, loss_c = self.app.store["win_color"], self.app.store["loss_color"]
        colors = {"ok": win_c, "warn": WARN, "bad": loss_c, None: FG}
        for i, (label, value, note) in enumerate(flip_cells(last)):
            row, col = divmod(i, 4)
            cells.grid_columnconfigure(col, weight=1, uniform="flip")
            tk.Label(cells, text=value, bg=PANEL, fg=colors[note], font=("Bahnschrift SemiBold", 15)).grid(
                row=2 * row, column=col, sticky="w", pady=(6 if row else 0, 0))
            tk.Label(cells, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).grid(row=2 * row + 1, column=col,
                                                                                    sticky="w")
        for i, text in enumerate(flip_advices(last)):
            self._label(right, text, bg=PANEL, fg=FG if i == 0 else MUTED, font=("Bahnschrift SemiBold", 11),
                        margin=260, pady=(12 if i == 0 else 0, 2))
        best = sorted((a for a in drill if a.get("flip") and not a["miss"] and a["flip"]["flip"] is not None),
                      key=lambda a: a["dt"] - PERFECT[a["spawn"]])[:5]
        if best:
            def mean(key):
                values = [abs(a["flip"][key]) for a in best if a["flip"][key] is not None]
                return sum(values) / len(values) if values else None
            angle, cancel, jump = mean("angle"), mean("cancel"), mean("jump")
            self._label(right, T("pf_best", n=len(best), a=round(angle) if angle is not None else "–",
                                 c=round(cancel * 1000) if cancel is not None else "–",
                                 j=seconds_text(jump) if jump is not None else "–"),
                        fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=260)
        self._label(right, T("pf_note"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=260, pady=(4, 0))
        if last.get("tl"):
            self._replay(last)
            self._timeline(last)

    def _flip_side(self, last):
        """Cote du geste parfait montre : celui choisi pour le guide, sinon celui du dernier essai (gauche par
        defaut)."""
        side = {"l": -1, "r": 1}.get(self.app.store["flip_side"])
        if side is None:
            side = 1 if last and (last.get("angle") or -1) > 0 else -1
        return side

    def _timeline(self, last):
        """Frise des inputs : ton dernier essai en plein, le geste parfait en pointilles par-dessus (meme axe de
        temps depuis le depart). Sans essai : le geste parfait seul."""
        ref = reference_flip(self._flip_side(last))
        tk.Label(self.content, text=T("tl_title" if last else "tl_ref_title"), bg=BG, fg=MUTED, font=BODY_FONT,
                 anchor="w").pack(fill="x", pady=(10, 2))
        frise = tk.Canvas(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1, height=190)
        frise.pack(fill="x")
        if last:
            frise.bind("<Configure>", lambda e: self._draw_timeline(frise, last["tl"], ref))
            self._label(self.content, T("tl_legend"), fg=MUTED, font=("Segoe UI", 9), pady=(2, 0))
        else:
            frise.bind("<Configure>", lambda e: self._draw_timeline(frise, ref))

    def _replay(self, last):
        """Ton dernier geste et le geste parfait, rejoues en boucle au ralenti, cales sur le 1er saut. Sans essai :
        le geste parfait seul."""
        side = self._flip_side(last)
        ref = reference_flip(side)
        head = tk.Frame(self.content, bg=BG)
        head.pack(fill="x", pady=(10, 2))
        tk.Label(head, text=T("rp_title" if last else "rp_ref_title"), bg=BG, fg=MUTED, font=BODY_FONT).pack(
            side="left")
        for speed in (1.0, 0.5, 0.25):
            active = self.replay_speed == speed
            text = "×" + (f"{speed:g}".replace(".", ",") if lang() == "fr" else f"{speed:g}")
            tk.Button(head, text=text, command=lambda v=speed: self.set_replay_speed(v), relief="flat",
                      cursor="hand2", bg=EDGE if active else BG, fg=FG if active else MUTED, activebackground=EDGE,
                      activeforeground=FG, font=("Bahnschrift SemiBold", 10), padx=8, pady=1, bd=0).pack(
                side="right", padx=(2, 0))
        tk.Label(head, text=T("rp_speed"), bg=BG, fg=MUTED, font=BODY_FONT).pack(side="right", padx=(0, 6))
        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x")
        row = tk.Frame(box, bg=PANEL)
        row.pack(pady=(10, 0))
        views = []
        shown = [(T("rp_ref"), ref, ref["j1"])]
        if last:
            shown.insert(0, (T("rp_you"), last["tl"], last["jump"] if last["jump"] is not None else ref["j1"]))
        for title, data, j1 in shown:
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", padx=28)
            tk.Label(col, text=title, bg=PANEL, fg=FG, font=("Bahnschrift SemiBold", 11)).pack()
            c = tk.Canvas(col, bg=PANEL, highlightthickness=0, width=200, height=236)
            c.pack()
            views.append((c, data, j1))
        clock = tk.Label(box, bg=PANEL, fg=FG, font=("Bahnschrift SemiBold", 11))
        clock.pack()
        self._label(box, T("rp_hint" if last else "rp_ref_hint"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=70, padx=12, pady=(2, 10))
        self.replay_gen += 1
        self._replay_step(self.replay_gen, views, clock, side, -0.35)

    def set_replay_speed(self, speed):
        self.replay_speed = speed
        self.show()

    def _replay_step(self, gen, views, clock, side, rel):
        """Une image de l'animation : `rel` secondes apres le 1er saut (de -0,35 a +0,45 s, puis on recommence)."""
        if gen != self.replay_gen or not clock.winfo_exists():
            return
        for c, data, j1 in views:
            self._draw_replay(c, data, j1, j1 + rel, side)
        clock.configure(text=T("rp_clock", t=f"{round(rel * 1000):+d} ms"))
        if rel >= 0.45:
            nxt, delay = -0.35, 900
        else:
            nxt, delay = min(0.45, rel + 0.033 * self.replay_speed), 33
        self.win.after(delay, lambda: self._replay_step(gen, views, clock, side, nxt))

    def _draw_replay(self, c, data, j1, t, side):
        """Stick a l'instant t (s apres le depart) : zone verte du flip, trajet complet en fond, trajet deja fait,
        position du stick, puis saut / air roll / boost allumes s'ils sont enfonces."""
        c.delete("all")
        cx, cy, r = 100, 92, 78
        win_c = self.app.store["win_color"]
        lo, hi = (22, 38) if side > 0 else (-38, -22)
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=90 - hi, extent=hi - lo, fill=GRID, outline="")
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=EDGE, width=2)
        c.create_line(cx - r, cy, cx + r, cy, fill=EDGE)
        c.create_line(cx, cy - r, cx, cy + r, fill=EDGE)
        c.create_text(cx, cy - r - 7, text="▲", fill=MUTED, font=("Segoe UI", 7))
        span = [s for s in data["stick"] if j1 - 0.35 <= s[0] <= j1 + 0.45]
        before = [s for s in data["stick"] if s[0] < j1 - 0.35]
        if before:
            span.insert(0, (j1 - 0.35,) + tuple(before[-1][1:]))

        def at(x, y):
            return cx + x * r, cy - y * r

        if len(span) > 1:
            c.create_line(*[v for s in span for v in at(s[1], s[2])], fill=EDGE, width=2)
        done = [s for s in span if s[0] <= t]
        if len(done) > 1:
            c.create_line(*[v for s in done for v in at(s[1], s[2])], fill="#38bdf8", width=3)
        now = done[-1] if done else (span[0] if span else (t, 0, 0))
        px, py = at(now[1], now[2])
        c.create_oval(px - 9, py - 9, px + 9, py + 9, fill=FG, outline=BG, width=2)
        x = 8
        for key, color in (("jump", win_c), ("roll", "#a78bfa"), ("boost", "#f59e0b")):
            on = any(a <= t <= b for a, b in data[key])
            c.create_rectangle(x, 200, x + 58, 224, fill=color if on else BG, outline=color if on else EDGE)
            c.create_text(x + 29, 212, text=T("tl_" + key), fill=BG if on else MUTED,
                          font=("Bahnschrift SemiBold", 9))
            x += 64

    def _draw_timeline(self, c, tl, ref=None):
        """Frise des inputs du dernier essai (meme contenu que sur la carte de l'overlay). ref : geste parfait,
        dessine en pointilles par-dessus (traits clairs, barres en contour)."""
        c.delete("all")
        colors = {"sky": "#38bdf8", "gold": "#facc15", "green": self.app.store["win_color"], "violet": "#a78bfa",
                  "amber": "#f59e0b"}
        tracks = timeline_tracks(tl)
        ref_tracks = timeline_tracks(ref) if ref else [None] * len(tracks)
        x0, y0, x1, y1 = 12, 22, int(c.winfo_width()) - 16, int(c["height"]) - 22
        left, t0, t1 = x0 + 120, -0.1, max(tl["t1"], ref["t1"] if ref else 0)
        weights = [2 if kind == "line" else 1 for _, kind, _, _ in tracks]
        unit = (y1 - y0) / sum(weights)

        def tx(t):
            return left + (min(max(t, t0), t1) - t0) / (t1 - t0) * (x1 - left)

        for t, text in timeline_ticks(t1):
            c.create_line(tx(t), y0, tx(t), y1, fill=GRID)
            c.create_text(tx(t), y1 + 10, text=text, fill=MUTED, font=("Segoe UI", 8))
        def steps(data, mid, row):
            points = []
            for t, v in data:
                if points:
                    points += [tx(t), points[-1]]
                points += [tx(t), mid - v * row * 0.42]
            return points + [x1, points[-1]] if points else []

        top = y0
        for (label, kind, data, color), ref_track, weight in zip(tracks, ref_tracks, weights):
            row = unit * weight
            mid = top + row / 2
            top += row
            c.create_text(x0, mid, text=label, fill=MUTED, font=("Segoe UI", 9), anchor="w")
            if kind == "bars":
                for a, b in data:
                    c.create_rectangle(tx(a), mid - row * 0.28, max(tx(b), tx(a) + 2), mid + row * 0.28,
                                       fill=colors[color], outline="")
                for a, b in ref_track[2] if ref_track else []:
                    c.create_rectangle(tx(a), mid - row * 0.36, max(tx(b), tx(a) + 2), mid + row * 0.36,
                                       outline=REF_COLOR, dash=(3, 2))
                continue
            c.create_line(left, mid, x1, mid, fill=EDGE)
            points = steps(data, mid, row)
            if points:
                c.create_line(*points, fill=colors[color], width=2)
            points = steps(ref_track[2], mid, row) if ref_track else []
            if points:
                c.create_line(*points, fill=REF_COLOR, width=2, dash=(4, 3))
        marks = [(t, key, FG, False) for t, key in tl["marks"]]
        marks += [(t, key, REF_COLOR, True) for t, key in (ref["marks"] if ref else [])]
        for t, key, color, is_ref in marks:
            if t0 <= t <= t1:
                c.create_line(tx(t), y0 - 4, tx(t), y1, fill=color, dash=(3, 3))
                if not is_ref:  # reperes du geste parfait sans libelle, pour ne pas chevaucher les tiens
                    first = key == "flip"
                    c.create_text(tx(t) + (-4 if first else 4), y0 - 12, anchor="e" if first else "w",
                                  text=T("pf_flip_label") if first else T("pf_cancel").upper(), fill=color,
                                  font=("Bahnschrift SemiBold", 9))

    def _draw_stick(self, c, flip):
        """Stick gauche vu de face (haut = avant) : zone 20-45 degres, trajet autour du flip, direction du flip
        et point du cancel."""
        size = int(c["width"])
        cx = cy = size / 2
        r = size / 2 - 12
        win_c, loss_c = self.app.store["win_color"], self.app.store["loss_color"]
        for lo, hi in ((22, 38), (-38, -22)):  # zones vertes de SpeedFlipTrainer pour le flip
            c.create_arc(cx - r, cy - r, cx + r, cy + r, start=90 - hi, extent=hi - lo, fill=GRID, outline="")
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=EDGE, width=2)
        c.create_line(cx - r, cy, cx + r, cy, fill=EDGE)
        c.create_line(cx, cy - r, cx, cy + r, fill=EDGE)
        c.create_text(cx, cy - r - 6, text="▲", fill=MUTED, font=("Segoe UI", 7))
        points = [(cx + x * r, cy - y * r) for _, x, y in flip.get("path", [])]
        if len(points) > 1:
            c.create_line(*[v for p in points for v in p], fill=MUTED, width=2, smooth=False)
        at_flip = next(((x, y) for t, x, y in flip.get("path", []) if t >= 0), None)
        if at_flip:
            color = {"ok": win_c, "warn": WARN}.get(pad.grade("angle", flip["angle"]), loss_c)
            c.create_line(cx, cy, cx + at_flip[0] * r, cy - at_flip[1] * r, fill=color, width=3, arrow="last")
        cancel = next(((x, y) for t, x, y in flip.get("path", []) if t > 0 and y < -0.5), None)
        if cancel:
            color = {"ok": win_c, "warn": WARN}.get(pad.grade("cancel", flip["cancel"]), loss_c)
            px, py = cx + cancel[0] * r, cy - cancel[1] * r
            c.create_oval(px - 6, py - 6, px + 6, py + 6, fill=color, outline="")

    def _pad_box(self):
        """Manette detectee ou non, et boutons utilises pour l'analyse (a assigner comme dans le jeu)."""
        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x", pady=(12, 0))
        connected = self.app.pad.connected
        tk.Label(box, text=T("pad_ok" if connected else "pad_missing"), bg=PANEL, fg=OK if connected else WARN,
                 font=BODY_FONT, anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        self._label(box, T("pad_hint"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=70, padx=12)
        guide = tk.Frame(box, bg=PANEL)
        guide.pack(fill="x", padx=12, pady=(6, 0))
        var = tk.BooleanVar(value=self.app.store["stick_guide"])
        self.vars.append(var)
        tk.Checkbutton(guide, text=T("sg_option"), variable=var, bg=PANEL, fg=FG, font=BODY_FONT, selectcolor=BG,
                       activebackground=PANEL, activeforeground=FG, anchor="w", highlightthickness=0, bd=0,
                       command=self.app.toggle_stick_guide).pack(side="left")
        for value, key in (("r", "sg_right"), ("l", "sg_left"), ("auto", "sg_auto")):
            active = self.app.store["flip_side"] == value
            tk.Button(guide, text=T(key), command=lambda v=value: self.set_flip_side(v), relief="flat",
                      cursor="hand2", bg=EDGE if active else BG, fg=FG if active else MUTED, activebackground=EDGE,
                      activeforeground=FG, font=("Bahnschrift SemiBold", 10), padx=8, pady=1, bd=0).pack(
                side="right", padx=(2, 0))
        tk.Label(guide, text=T("sg_side"), bg=PANEL, fg=MUTED, font=BODY_FONT).pack(side="right", padx=(0, 6))
        if self.app.store["guide_pos"]:
            _button(guide, T("sg_reset_pos"), self.reset_guide_position, bg=EDGE).pack(side="left", padx=(10, 0))
        auto = tk.BooleanVar(value=self.app.store["guide_auto"])
        self.vars.append(auto)
        tk.Checkbutton(box, text=T("sg_auto_option"), variable=auto, bg=PANEL, fg=FG, font=BODY_FONT, selectcolor=BG,
                       activebackground=PANEL, activeforeground=FG, anchor="w", highlightthickness=0, bd=0,
                       command=lambda: self.app.set_option("guide_auto", auto.get())).pack(fill="x", padx=12,
                                                                                           pady=(4, 0))
        self._label(box, T("sg_move_hint"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=70, padx=12)
        # Boutons utilises pour l'analyse : resume, reglage dans la fenetre Boutons de la manette
        bindings = self.app.store["pad"]
        summary = "   ".join(f"{T('pad_' + a)} : {bindings.get(a) or '–'}" for a in PAD_ACTIONS if bindings.get(a))
        row = tk.Frame(box, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(6, 10))
        _button(row, T("pad_open"), self.app.open_pad, bg=EDGE).pack(side="left")
        tk.Label(row, text=summary, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(side="left",
                                                                                         padx=(10, 0))

    def _match_timer(self):
        """Chrono de chaque engagement en match (en ligne ou contre des bots), sur l'overlay."""
        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x", pady=(12, 0))
        var = tk.BooleanVar(value=self.app.store["kick_card"])
        self.vars.append(var)
        tk.Checkbutton(box, text=T("tr_alert"), variable=var, bg=PANEL, fg=FG, font=BODY_FONT, selectcolor=BG,
                       activebackground=PANEL, activeforeground=FG, anchor="w", highlightthickness=0, bd=0,
                       command=lambda: self.app.set_option("kick_card", var.get())).pack(
            fill="x", padx=12, pady=(10, 2))
        self._label(box, T("tr_how"), fg=MUTED, font=("Segoe UI", 9), bg=PANEL, margin=70, padx=12, pady=(0, 10))

    def _pack_code(self):
        """Code du pack d'engagements conseille, a copier dans le jeu (Entrainement personnalise > Code)."""
        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x", pady=(12, 0))
        row = tk.Frame(box, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(8, 2))
        tk.Label(row, text=T("dr_pack"), bg=PANEL, fg=MUTED, font=BODY_FONT).pack(side="left")
        tk.Label(row, text=KICKOFF_PACK, bg=PANEL, fg=FG, font=("Bahnschrift SemiBold", 14)).pack(side="left",
                                                                                              padx=(8, 12))
        button = _button(row, T("dr_pack_copy"), None, bg=EDGE)
        button.configure(command=lambda: self.copy_pack(button))
        button.pack(side="left")
        self._label(box, T("dr_pack_hint"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=70, padx=12,
                    pady=(0, 8))

    def copy_pack(self, button):
        self.win.clipboard_clear()
        self.win.clipboard_append(KICKOFF_PACK)
        button.configure(text=T("dr_pack_copied"))
        self.win.after(1500, lambda: button.winfo_exists() and button.configure(text=T("dr_pack_copy")))

    def _pad_setup(self):
        """Assistant : demande les boutons du joueur un par un, tant qu'il ne les a pas indiques."""
        box = tk.Frame(self.content, bg=PANEL, highlightbackground=WARN, highlightthickness=1)
        box.pack(fill="x", pady=(12, 0))
        tk.Label(box, text=T("pad_setup_title"), bg=PANEL, fg=WARN, font=BODY_FONT, anchor="w").pack(
            fill="x", padx=12, pady=(8, 2))
        self._label(box, T("pad_setup_text"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=70, padx=12)
        row = tk.Frame(box, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(6, 10))
        _button(row, T("pad_setup_start"), self.app.open_pad, bg=EDGE).pack(side="left")

    def reset_guide_position(self):
        self.app.reset_guide_position()
        self.show()

    def set_flip_side(self, value):
        self.app.set_option("flip_side", value)
        self.show()

    def grade_colors(self):
        """Couleur de chaque palier d'un essai : or, vert et rouge du joueur, orange."""
        return {"perfect": PERFECT_COLOR, "good": self.app.store["win_color"], "close": WARN,
                "slow": self.app.store["loss_color"]}

    def clear_drill(self):
        if messagebox.askyesno(T("dr_title"), T("dr_clear_confirm"), parent=self.win):
            self.app.set_option("drill", [])
            self.show()

