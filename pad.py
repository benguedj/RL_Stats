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


def analyse(samples, go, end, bindings):
    """Speed flip d'un essai (go : depart, end : contact ou fin du tir) d'apres les inputs de la manette.
    Renvoie {"jump": 1er saut (s apres le depart), "flip": delai entre les deux sauts (s), "angle": angle du
    stick au flip (degres, 0 = tout droit, < 0 a gauche), "cancel": delai du stick tire vers l'arriere apres le
    flip (s), "roll": air roll tenu au flip ("l", "r", "x" ou ""), "boost": % du temps en boost, "path": trajet
    du stick autour du flip}, ou None sans donnees."""
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
    out = {"jump": round(presses[0] - go, 3) if presses else None, "flip": None, "angle": None, "cancel": None,
           "roll": "",
           "boost": round(held * 100 / (end - go)) if end > go and bit["boost"] else None, "path": []}
    if len(presses) < 2:
        return out
    j1, j2 = presses[0], presses[1]
    out["flip"] = j2 - j1
    _, buttons, x, y = _state_at(samples, j2 + 0.004)  # le stick bouge souvent dans la meme milliseconde
    if math.hypot(x, y) > 0.3:
        out["angle"] = round(math.degrees(math.atan2(x, y)))
    for key in ("roll_l", "roll_r", "roll"):
        if bit[key] and buttons & bit[key]:
            out["roll"] = {"roll_l": "l", "roll_r": "r", "roll": "x"}[key]
            break
    cancel = next((s[0] for s in samples if j2 < s[0] <= j2 + 0.5 and s[3] < -0.5), None)
    out["cancel"] = cancel - j2 if cancel else None
    # Trajet du stick de peu avant le flip jusqu'apres le cancel : [(t relatif au flip, x, y)]
    stop = (cancel or j2) + 0.15
    out["path"] = [(round(s[0] - j2, 3), round(s[2], 2), round(s[3], 2)) for s in samples if j2 - 0.15 <= s[0] <= stop]
    for key in ("flip", "cancel"):
        if out[key] is not None:
            out[key] = round(out[key], 3)
    return out


# Reperes indicatifs (les guides disent : flip en diagonale, 20 a 45 degres ; cancel immediat)
def grade(key, value):
    """"ok", "warn" ou "bad" pour une mesure, None sans repere."""
    if value is None:
        return "bad" if key in ("flip", "cancel") else None
    if key == "angle":
        a = abs(value)
        return "ok" if 20 <= a <= 45 else "warn" if 10 <= a <= 60 else "bad"
    if key == "cancel":
        return "ok" if value <= 0.06 else "warn" if value <= 0.12 else "bad"
    if key == "boost":
        return "ok" if value >= 90 else "warn" if value >= 70 else "bad"
    return None


def advice(flip):
    """Cle de texte du conseil le plus utile pour ce speed flip."""
    if flip["flip"] is None:
        return "pf_no_flip"
    if flip["angle"] is None or abs(flip["angle"]) < 20:
        return "pf_straight"
    if abs(flip["angle"]) > 45:
        return "pf_wide"
    if flip["cancel"] is None:
        return "pf_no_cancel"
    if flip["cancel"] > 0.06:
        return "pf_slow_cancel"
    if flip["boost"] is not None and flip["boost"] < 90:
        return "pf_more_boost"
    return "pf_good"
