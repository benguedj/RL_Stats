"""Trophees (debloques une fois) et records personnels, calcules sur l'historique.

Les evenements du fil du jeu (EventName de StatfeedEvent) sont comptes par match dans
match["me"]["feed"] : AerialGoal, BicycleGoal, FlipReset, HatTrick, EpicSave...
"""

from collections import Counter

# (id, (francais, anglais), type, parametre, seuil)
ACHIEVEMENTS = [
    ("first_win", ("Première victoire", "First win"), "wins", None, 1),
    ("aerial", ("But aérien", "Aerial goal"), "feed", "AerialGoal", 1),
    ("bicycle", ("Retourné gagnant", "Bicycle goal"), "feed", "BicycleGoal", 1),
    ("flip_reset", ("Flip reset", "Flip reset"), "feed", "FlipReset", 1),
    ("hat_trick", ("Coup du chapeau", "Hat trick"), "feed", "HatTrick", 1),
    ("epic_save", ("Arrêt épique", "Epic save"), "feed", "EpicSave", 1),
    ("savior", ("Sauveur", "Savior"), "feed", "Savior", 1),
    ("turtle", ("Coup de la tortue", "Turtle goal"), "feed", "TurtleGoal", 1),
    ("long_goal", ("But lointain", "Long goal"), "feed", "LongGoal", 1),
    ("overtime", ("But en prolongation", "Overtime goal"), "feed", "OvertimeGoal", 1),
    ("playmaker", ("Meneur de jeu", "Playmaker"), "feed", "Playmaker", 1),
    ("demolisher", ("Démolisseur : 50 démos", "Demolisher: 50 demos"), "feed", "Demolish", 50),
    ("aerial_10", ("Pilote : 10 buts aériens", "Pilot: 10 aerial goals"), "feed", "AerialGoal", 10),
    ("mvp_1", ("Premier MVP", "First MVP"), "mvp", None, 1),
    ("mvp_10", ("10 fois MVP", "10× MVP"), "mvp", None, 10),
    ("mvp_50", ("50 fois MVP", "50× MVP"), "mvp", None, 50),
    ("streak_5", ("Série de 5 victoires", "5 win streak"), "streak", None, 5),
    ("streak_10", ("Série de 10 victoires", "10 win streak"), "streak", None, 10),
    ("games_100", ("100 matchs", "100 games"), "games", None, 100),
    ("games_500", ("500 matchs", "500 games"), "games", None, 500),
    ("wins_50", ("50 victoires", "50 wins"), "wins", None, 50),
    ("wins_250", ("250 victoires", "250 wins"), "wins", None, 250),
    ("rocket", ("Fusée : but à 120 km/h", "Rocket: 120 km/h goal"), "speed", None, 120),
    ("cannon", ("Canon : but à 140 km/h", "Cannon: 140 km/h goal"), "speed", None, 140),
    ("five_goals", ("5 buts en un match", "5 goals in one game"), "match", "goals", 5),
    ("wall", ("Mur : 5 arrêts en un match", "Wall: 5 saves in one game"), "match", "saves", 5),
]

# (id, (francais, anglais), cle de match["me"], format de valeur)
RECORDS = [
    ("goals", ("Buts en un match", "Goals in a game"), "goals", "{:d}"),
    ("saves", ("Arrêts en un match", "Saves in a game"), "saves", "{:d}"),
    ("assists", ("Passes D. en un match", "Assists in a game"), "assists", "{:d}"),
    ("score", ("Meilleur score", "Best score"), "score", "{:d}"),
    ("fastest", ("But le plus rapide", "Fastest goal"), "fastest", "{:.0f} km/h"),
    ("streak", ("Plus longue série", "Longest win streak"), None, "{:d}"),
]


def label(entry, lang):
    return entry[1][0 if lang == "fr" else 1]


def totals(matches):
    played = [m.get("me") or {} for m in matches if not m.get("forfeit")]
    feed = Counter()
    for me in played:
        feed.update(me.get("feed") or {})
    best = cur = 0
    for m in matches:
        cur = cur + 1 if m["won"] else 0
        best = max(best, cur)
    return {
        "games": len(matches), "wins": sum(1 for m in matches if m["won"]),
        "mvp": sum(1 for me in played if me.get("mvp")), "streak": best, "feed": feed,
        "speed": max((me.get("fastest") or 0 for me in played), default=0),
        "match": {key: max((me.get(key) or 0 for me in played), default=0) for key in ("goals", "saves")},
    }


def progress(entry, t):
    """(valeur actuelle, seuil) d'un trophee."""
    _, _, kind, param, goal = entry
    if kind == "feed":
        value = t["feed"].get(param, 0)
    elif kind == "match":
        value = t["match"][param]
    else:
        value = t[kind]
    return value, goal


def unlocked(matches):
    t = totals(matches)
    return {e[0] for e in ACHIEVEMENTS if progress(e, t)[0] >= progress(e, t)[1]}


def records(matches):
    """{id: (valeur, horodatage du match)}."""
    out = {}
    played = [m for m in matches if m.get("me") and not m.get("forfeit")]
    for rid, _, key, _ in RECORDS:
        if key is None:
            continue
        best = max(played, key=lambda m: m["me"].get(key) or 0, default=None)
        if best and (best["me"].get(key) or 0) > 0:
            out[rid] = (best["me"][key], best["t"])
    best = cur = 0
    when = None
    for m in matches:
        cur = cur + 1 if m["won"] else 0
        if cur > best:
            best, when = cur, m["t"]
    if best:
        out["streak"] = (best, when)
    return out


def broken_records(before, after):
    """Records battus par le dernier match (seulement s'il y avait deja un record)."""
    return [rid for rid, (value, _) in after.items() if rid in before and value > before[rid][0]]
