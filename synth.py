"""Sons de l'overlay, synthetises (aucun fichier a fournir).

render(kind) renvoie les echantillons (floats entre -1 et 1, 44,1 kHz, mono) :
  "w"  victoire      : fanfare de cuivres, arpege qui monte puis accord final qui vibre
  "l"  defaite       : impact, eclats de verre et second coup, cales sur l'animation
  "gw" but marque    : coup grave, corne de stade et clameur de la foule
  "gl" but encaisse  : choc sourd et deux notes graves qui grincent en descendant
Le calcul prend quelques dixiemes de seconde : il est fait une fois, en arriere-plan.
"""

import math
import random

RATE = 44100
TAU = 2 * math.pi


def _buffer(seconds):
    return [0.0] * int(RATE * seconds)


def _mix(buf, samples, start, gain=1.0):
    i0 = int(start * RATE)
    for i, v in enumerate(samples):
        if i0 + i < len(buf):
            buf[i0 + i] += v * gain


def _env(t, dur, attack, release):
    """Enveloppe : montee lineaire, plateau, descente lineaire en fin de note."""
    if t < attack:
        return t / attack
    if t > dur - release:
        return max(0.0, (dur - t) / release)
    return 1.0


def _tone(dur, freq, harmonics, attack=0.01, release=0.08, decay=0.0, vibrato=(0.0, 0.0), glide=None):
    """Note a timbre riche : harmonics = [(rang, amplitude)]. freq peut glisser vers glide
    pendant la note ; vibrato = (frequence en Hz, profondeur relative)."""
    out = []
    phase = 0.0
    vf, vd = vibrato
    n = int(dur * RATE)
    for i in range(n):
        t = i / RATE
        f = freq if glide is None else freq + (glide - freq) * (t / dur) ** 1.5
        if vd:
            f *= 1 + vd * math.sin(TAU * vf * t) * min(1.0, t / 0.15)
        phase += TAU * f / RATE
        v = 0.0
        for rank, amp in harmonics:
            v += amp * math.sin(rank * phase)
        out.append(v * _env(t, dur, attack, release) * (math.exp(-decay * t) if decay else 1.0))
    return out


def _noise(dur, cutoff, attack=0.01, release=0.1, seed=1):
    """Bruit filtre (passe-bas a un pole) : souffle, foule, eclat."""
    rnd = random.Random(seed)
    a = 1 - math.exp(-TAU * cutoff / RATE)
    y, out = 0.0, []
    for i in range(int(dur * RATE)):
        y += a * (rnd.uniform(-1, 1) - y)
        out.append(y * _env(i / RATE, dur, attack, release))
    return out


def _thud(dur, f0, f1, decay):
    """Coup grave dont la hauteur tombe (grosse caisse, impact)."""
    out, phase = [], 0.0
    for i in range(int(dur * RATE)):
        t = i / RATE
        phase += TAU * (f1 + (f0 - f1) * math.exp(-t * 18)) / RATE
        out.append(math.sin(phase) * math.exp(-decay * t) * min(1.0, t / 0.002))
    return out


BRASS = [(n, 1 / n ** 0.9) for n in range(1, 8)]          # cuivre brillant
HORN = [(n, 1 / n ** 0.7) for n in range(1, 11)]          # corne de stade, tres riche
BUZZ = [(1, 1.0), (3, 0.45), (5, 0.3), (7, 0.18), (9, 0.1)]    # son grinçant (harmoniques impaires)
SOFT = [(1, 1.0), (2, 0.28), (3, 0.1), (4, 0.04)]               # doux et rond (defaite)


def _victory():
    buf = _buffer(1.75)
    for i, f in enumerate((392.0, 523.25, 659.25)):  # sol, do, mi : montee rapide
        _mix(buf, _tone(0.13, f, BRASS, attack=0.012, release=0.05), 0.11 * i, 0.55)
    for f in (523.25, 659.25, 783.99, 1046.5):  # accord final de do majeur, qui vibre
        _mix(buf, _tone(1.3, f, BRASS, attack=0.02, release=0.45, vibrato=(5.5, 0.006)), 0.33, 0.3)
    _mix(buf, _noise(0.6, 6000, attack=0.005, release=0.5, seed=3), 0.33, 0.12)  # eclat de cymbale
    return buf


def _ping(dur, freq, decay):
    """Petit tintement de verre (aigu, tres court)."""
    return [math.sin(TAU * freq * i / RATE) * math.exp(-decay * i / RATE) * min(1.0, i / 40)
            for i in range(int(dur * RATE))]


def _defeat():
    """Cale sur l'animation de defaite (designs.MatchAnimation) : impact au debut de la secousse,
    tintements quand les eclats se detachent (0,05 a 0,35 s), second coup avec la seconde pulsation
    rouge (0,8 s). Une courte note grave qui descend donne la couleur "defaite"."""
    buf = _buffer(1.25)
    _mix(buf, _thud(0.4, 120, 42, 8), 0.04, 1.0)
    _mix(buf, _noise(0.16, 1600, attack=0.002, release=0.12, seed=11), 0.04, 0.45)  # craquement
    _mix(buf, _tone(0.6, 164.81, SOFT, attack=0.02, release=0.3, glide=130.81), 0.06, 0.3)
    rnd = random.Random(4)
    for _ in range(5):
        _mix(buf, _ping(0.12, rnd.uniform(2600, 4400), 38), rnd.uniform(0.12, 0.45), 0.07)
    _mix(buf, _thud(0.35, 85, 38, 9), 0.75, 0.55)
    return buf


def _goal_scored():
    buf = _buffer(1.5)
    _mix(buf, _thud(0.4, 140, 48, 7), 0.0, 0.9)
    for detune in (0.0, 1.6):  # deux cornes legerement desaccordees : son plus large
        _mix(buf, _tone(0.95, 233.08 + detune, HORN, attack=0.05, release=0.3), 0.04, 0.32)
    _mix(buf, _noise(1.4, 1400, attack=0.25, release=0.6, seed=7), 0.08, 0.35)  # clameur de la foule
    return buf


def _goal_conceded():
    buf = _buffer(1.0)
    _mix(buf, _thud(0.5, 110, 42, 6), 0.0, 1.0)
    _mix(buf, _noise(0.12, 900, attack=0.002, release=0.1, seed=5), 0.0, 0.35)  # le choc
    _mix(buf, _tone(0.22, 164.81, BUZZ, attack=0.01, release=0.06), 0.1, 0.22)
    _mix(buf, _tone(0.55, 155.56, BUZZ, attack=0.01, release=0.3, glide=146.0), 0.33, 0.22)
    return buf


SOUNDS = {"w": _victory, "l": _defeat, "gw": _goal_scored, "gl": _goal_conceded}


def render(kind):
    """Echantillons normalises sur le volume percu (niveau moyen commun aux quatre sons, crete au plus a 0,9)."""
    buf = SOUNDS[kind]()
    peak = max(1e-9, max(abs(v) for v in buf))
    rms = max(1e-9, (sum(v * v for v in buf) / len(buf)) ** 0.5)
    gain = min(0.9 / peak, 0.2 / rms)
    return [v * gain for v in buf]
