"""Manette (XInput) : etat lu en continu pour analyser le speed flip de chaque essai du defi d'engagements.

On lit la manette comme un afficheur d'inputs pour streamers : rien n'est injecte dans le jeu. Seuls les
changements d'etat des dernieres secondes restent en memoire ; seule l'analyse de chaque essai est gardee.
Les manettes Xbox (et celles que Steam Input fait passer pour une manette Xbox) sont reconnues.
"""

import bisect
import ctypes
import math
import threading
import time
from collections import deque

# Boutons XInput ; LT / RT (gachettes) traites comme des boutons au-dela d'un quart de course
BUTTONS = {"A": 0x1000, "B": 0x2000, "X": 0x4000, "Y": 0x8000, "LB": 0x0100, "RB": 0x0200, "LT": 0x10000,
           "RT": 0x20000, "L3": 0x0040, "R3": 0x0080, "Up": 0x0001, "Down": 0x0002, "Left": 0x0004,
           "Right": 0x0008, "Start": 0x0010, "Back": 0x0020}
DEFAULT_BINDINGS = {"jump": "A", "boost": "B", "roll": "X", "roll_l": "", "roll_r": ""}
KEEP = 6.0  # secondes d'historique


class _Gamepad(ctypes.Structure):
    _fields_ = [("wButtons", ctypes.c_ushort), ("bLeftTrigger", ctypes.c_ubyte), ("bRightTrigger", ctypes.c_ubyte),
                ("sThumbLX", ctypes.c_short), ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
                ("sThumbRY", ctypes.c_short)]


class _State(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_uint), ("Gamepad", _Gamepad)]


def _xinput():
    for name in ("xinput1_4", "xinput9_1_0", "xinput1_3"):
        try:
            return ctypes.WinDLL(name)
        except OSError:
            continue
    return None


class Pad(threading.Thread):
    """Changements d'etat de la premiere manette branchee : (instant perf_counter, boutons, stick X, stick Y)."""

    def __init__(self):
        super().__init__(daemon=True)
        self.dll = _xinput()
        self.slot = None
        self.samples = deque()
        self.lock = threading.Lock()

    @property
    def connected(self):
        return self.slot is not None

    def _read(self, slot):
        state = _State()
        if self.dll.XInputGetState(slot, ctypes.byref(state)) != 0:
            return None
        g = state.Gamepad
        buttons = g.wButtons | (BUTTONS["LT"] if g.bLeftTrigger > 64 else 0) | (BUTTONS["RT"] if g.bRightTrigger > 64
                                                                               else 0)
        return state.dwPacketNumber, buttons, max(-1.0, g.sThumbLX / 32767), max(-1.0, g.sThumbLY / 32767)

    def run(self):
        if not self.dll:
            return
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)  # sommeil de ~1 ms au lieu de 15,6 ms
        except (AttributeError, OSError):
            pass
        packet, next_scan = None, 0
        while True:
            now = time.perf_counter()
            if self.slot is None:
                # Interroger un emplacement vide est lent : on ne cherche une manette que toutes les 2 s
                if now >= next_scan:
                    self.slot = next((i for i in range(4) if self._read(i)), None)
                    next_scan = now + 2
                time.sleep(0.05 if self.slot is None else 0)
                continue
            state = self._read(self.slot)
            if state is None:
                self.slot = None
                continue
            if state[0] != packet:
                packet = state[0]
                with self.lock:
                    self.samples.append((now,) + state[1:])
                    while self.samples and self.samples[0][0] < now - KEEP:
                        self.samples.popleft()
            time.sleep(0.002)

    def window(self, t0, t1):
        """Etats de t0 a t1, precedes du dernier etat connu avant t0."""
        with self.lock:
            samples = list(self.samples)
        times = [s[0] for s in samples]
        i = max(0, bisect.bisect_left(times, t0) - 1)
        return [s for s in samples[i:] if s[0] <= t1]

    def held(self):
        """Noms des boutons enfonces en ce moment (pour assigner un bouton en appuyant dessus)."""
        if self.slot is None:
            return set()
        state = self._read(self.slot)
        return {name for name, bit in BUTTONS.items() if state and state[1] & bit}


def _state_at(samples, t):
    """Dernier etat connu a l'instant t."""
    state = samples[0]
    for s in samples:
        if s[0] > t:
            break
        state = s
    return state

def _intervals(samples, bit, go, t0, t1):
    """[(debut, fin)] ou le bouton `bit` est enfonce entre t0 et t1, en s relatives au depart go."""
    out, down = [], None
    for s in samples:
        if s[0] > t1:
            break
        pressed = bool(bit and s[1] & bit)
        if pressed and down is None:
            down = max(s[0], t0)
        elif not pressed and down is not None:
            if s[0] > t0:
                out.append((round(down - go, 3), round(s[0] - go, 3)))
            down = None
    if down is not None:
        out.append((round(down - go, 3), round(t1 - go, 3)))
    return out


def _tap_runs(samples, go, until):
    """Ecarts lateraux du stick (|x| >= 0,25) entre le depart et `until` : [[debut, fin, cote -1 | 1, amplitude]].
    Seuil bas : le guide conseille un petit decalage (35 degres sans aller a fond), pas un stick a fond."""
    runs, run = [], None
    for t, _, x, _ in samples:
        if t < go - 0.3:
            continue
        if t > until:
            break
        side = (x > 0) - (x < 0) if abs(x) >= 0.25 else 0
        if run and side != run[2]:
            run[1] = t
            runs.append(run)
            run = None
        if side and run is None:
            run = [t, t, side, 0.0]
        if run:
            run[3] = max(run[3], abs(x))
    if run:
        run[1] = until
        runs.append(run)
    return runs


def analyse(samples, go, end, bindings):
    """Speed flip d'un essai (go : depart, end : contact ou fin du tir) d'apres les inputs de la manette.
    Renvoie {"tap_t", "tap_dur", "tap_side", "tap_peak": coup de stick avant le saut (debut en s apres le
    depart, duree, cote -1 gauche | 1 droite, amplitude 0 a 1), "jump": 1er saut (s apres le depart), "hold":
    duree du 1er appui sur saut, "flip": delai entre les deux sauts (s), "angle": angle du stick au flip
    (degres, 0 = tout droit, < 0 a gauche), "cancel": delai du stick tire vers l'arriere apres le flip (s),
    "back": duree du stick tenu en arriere, "roll": air roll tenu autour du flip ("l", "r", "x" ou ""), "roll_t":
    son appui par rapport au flip (s, < 0 : avant), "boost": % du temps en boost, "path": trajet du stick autour
    du flip, "tl": frise des inputs (fenetre et carte, pas enregistree)}, ou None sans donnees."""
    if not samples:
        return None
    bit = {k: BUTTONS.get(v or "", 0) for k, v in bindings.items()}
    presses = [b[0] for a, b in zip(samples, samples[1:])
               if bit["jump"] and b[1] & bit["jump"] and not a[1] & bit["jump"] and go - 0.3 <= b[0] <= end]
    held = 0.0  # temps passe en boost entre le depart et la fin
    for a, b in zip(samples, samples[1:] + [(end,) + samples[-1][1:]]):
        lo, hi = max(a[0], go), min(b[0], end)
        if hi > lo and a[1] & bit["boost"]:
            held += hi - lo
    out = {"tap_t": None, "tap_dur": None, "tap_side": None, "tap_peak": None, "jump": None, "hold": None,
           "flip": None, "angle": None, "cancel": None, "back": None, "roll": "", "roll_t": None,
           "boost": round(held * 100 / (end - go)) if end > go and bit["boost"] else None, "path": [], "tl": None}
    j1 = presses[0] if presses else None
    j2 = presses[1] if len(presses) > 1 else None
    # Coup de stick : jusqu'au 2e saut, car le stick reste sur le cote pendant le 1er saut. Du cote oppose au
    # flip quand on le connait (le stick passe ensuite de l'autre cote pour le flip)
    runs = _tap_runs(samples, go, j2 if j2 is not None else end)
    x_flip = _state_at(samples, j2 + 0.004)[2] if j2 is not None else 0
    if x_flip:
        runs = [r for r in runs if r[2] * x_flip < 0]
    if runs:
        best = max(runs, key=lambda r: r[3])
        out["tap_t"], out["tap_dur"] = round(best[0] - go, 3), round(best[1] - best[0], 3)
        out["tap_side"], out["tap_peak"] = best[2], round(best[3], 2)
    if j1 is not None:
        out["jump"] = round(j1 - go, 3)
        release = next((s[0] for s in samples if s[0] > j1 and not s[1] & bit["jump"]), None)
        out["hold"] = round(release - j1, 3) if release else None
    cancel = None
    if j2 is not None:
        out["flip"] = round(j2 - j1, 3)
        _, _, x, y = _state_at(samples, j2 + 0.004)  # le stick bouge souvent dans la meme milliseconde
        if math.hypot(x, y) > 0.3:
            out["angle"] = round(math.degrees(math.atan2(x, y)))
        # Air roll : le premier bouton d'air roll enfonce autour du flip (un peu avant comme un peu apres)
        rolls = [(spans[0][0], code) for key, code in (("roll_l", "l"), ("roll_r", "r"), ("roll", "x"))
                 for spans in [_intervals(samples, bit[key], go, j2 - 0.3, j2 + 0.4)] if spans]
        if rolls:
            start, out["roll"] = min(rolls)
            out["roll_t"] = round(start - (j2 - go), 3)
        # Cancel : stick tire a plus de 80 % vers l'arriere, comme SpeedFlipTrainer
        cancel = next((s[0] for s in samples if j2 < s[0] <= j2 + 0.5 and s[3] < -0.8), None)
        if cancel:
            out["cancel"] = round(cancel - j2, 3)
            up = next((s[0] for s in samples if s[0] > cancel and s[3] >= -0.8), end)
            out["back"] = round(min(up, end) - cancel, 3)
        # Trajet du stick de peu avant le flip jusqu'apres le cancel : [(t relatif au flip, x, y)]
        stop = (cancel or j2) + 0.15
        out["path"] = [(round(s[0] - j2, 3), round(s[2], 2), round(s[3], 2)) for s in samples
                       if j2 - 0.15 <= s[0] <= stop]
    # Frise : du depart a un peu apres le cancel (ou le flip), en s relatives au depart
    t1 = min(end, max(go + 0.8, (cancel or j2 or j1 or go) + 0.45))
    first = _state_at(samples, go - 0.1)
    roll_spans = sorted(span for key in ("roll_l", "roll_r", "roll")
                        for span in _intervals(samples, bit[key], go, go - 0.1, t1))
    out["tl"] = {"t1": round(t1 - go, 3),
                 "stick": [(-0.1, first[2], first[3])] + [(round(s[0] - go, 3), s[2], s[3]) for s in samples
                                                          if go - 0.1 < s[0] <= t1],
                 "jump": _intervals(samples, bit["jump"], go, go - 0.1, t1),
                 "roll": roll_spans, "boost": _intervals(samples, bit["boost"], go, go - 0.1, t1),
                 "marks": [(round(t - go, 3), key) for t, key in ((j2, "flip"), (cancel, "cancel")) if t]}
    return out


# Reperes du plugin BakkesMod SpeedFlipTrainer (tynidev/SpeedFlipTrainer), en ticks de physique du jeu (120
# par seconde) : 1er saut entre 55 et 70 ticks apres le depart (jaune de 50 a 75), flip a 30 degres (vert a
# +/- 8, jaune a +/- 15), cancel en 7 ticks au plus (jaune jusqu'a 11). Son speed flip enregistre (flip a
# gauche) : stick a fond a droite juste avant le 1er saut (61 ticks), 2e saut 11 ticks plus tard, cancel 5 ticks
# apres, air roll gauche (cote du flip) 4 ticks apres le flip
TICK = 1 / 120


def grade(key, value):
    """"ok", "warn" ou "bad" pour une mesure, None sans repere."""
    if value is None:
        return "bad" if key in ("flip", "cancel") else None
    if key == "jump":
        ticks = value / TICK
        return "ok" if 55 <= ticks < 70 else "warn" if 50 <= ticks < 75 else "bad"
    if key == "angle":
        gap = abs(abs(value) - 30)
        return "ok" if gap <= 8 else "warn" if gap <= 15 else "bad"
    if key == "cancel":
        ticks = round(value / TICK)
        return "ok" if ticks <= 7 else "warn" if ticks <= 11 else "bad"
    if key == "boost":
        return "ok" if value >= 90 else "warn" if value >= 70 else "bad"
    return None


def tap_issue(flip):
    """Defaut du coup de stick (cle de texte), None s'il est bon ou pas mesure (anciens essais)."""
    if "tap_side" not in flip:
        return None
    if flip["tap_side"] is None:
        return "pf_no_tap"
    if flip["jump"] is not None and not flip["tap_t"] - 0.03 <= flip["jump"] <= flip["tap_t"] + flip["tap_dur"]:
        return "pf_tap_timing"  # le stick doit encore etre decale au moment du 1er saut
    if flip["tap_peak"] >= 0.85:
        return "pf_tap_hard"  # le guide conseille un petit decalage : un stick a fond tourne trop
    return None


def roll_issue(flip):
    """Defaut de l'air roll (cle de texte), None s'il est bon ou pas mesure. Air roll directionnel ("x") : le
    cote depend du stick, rien a en dire."""
    if flip["flip"] is None or "roll_t" not in flip:
        return None
    if not flip["roll"]:
        return "pf_no_roll"
    if flip["angle"] and flip["roll"] != "x" and (flip["roll"] == "l") != (flip["angle"] < 0):
        return "pf_roll_side"
    return None


def grade_tap(flip):
    if "tap_side" not in flip:
        return None
    return {None: "ok", "pf_tap_hard": "warn", "pf_tap_timing": "warn"}.get(tap_issue(flip), "bad")


def grade_roll(flip):
    if flip["flip"] is None or "roll_t" not in flip:
        return None
    return "ok" if roll_issue(flip) is None else "bad"


def advices(flip, n=2):
    """Cles de texte des `n` conseils les plus utiles pour ce speed flip, du plus important au moins important."""
    out = []
    if flip.get("boost") == 0:
        out.append("pf_check_buttons")  # boost jamais vu : presque toujours un bouton mal assigne
    if flip["jump"] is not None and grade("jump", flip["jump"]) != "ok":
        out.append("pf_jump_early" if flip["jump"] < 55 * TICK else "pf_jump_late")
    if flip["flip"] is None:
        out.append("pf_no_flip")
    else:
        if tap_issue(flip):
            out.append(tap_issue(flip))
        if flip["angle"] is None or abs(flip["angle"]) < 22:
            out.append("pf_straight")
        elif abs(flip["angle"]) > 38:
            out.append("pf_wide")
        if flip["cancel"] is None:
            out.append("pf_no_cancel")
        elif grade("cancel", flip["cancel"]) != "ok":
            out.append("pf_slow_cancel")
        if roll_issue(flip):
            out.append(roll_issue(flip))
    if flip.get("boost") and flip["boost"] < 90:
        out.append("pf_more_boost")
    return out[:n] or ["pf_good"]


def roll_advice_side(flip):
    """Air roll conseille pour ce flip : celui du cote du flip (gauche pour un flip a gauche)."""
    return "pf_left_full" if (flip.get("angle") or 0) < 0 else "pf_right_full"
