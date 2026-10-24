"""Historique des matchs (matches.json) et statistiques calculees dessus.

Un match enregistre :
  {"t": horodatage, "guid": ..., "mode": "2v2", "won": bool, "forfeit": bool,
   "score": [buts de mon equipe, buts adverses],
   "me": {"goals", "assists", "saves", "shots", "demos", "score", "mvp", "fastest"},
   "with": [[id, pseudo], ...], "against": [[id, pseudo], ...]}
"""

import csv
import datetime
import json
import os

MAX_MATCHES = 20000
MODES = ("1v1", "2v2", "3v3", "4v4")


def day_of(t):
    return datetime.date.fromtimestamp(t)


class History:
    def __init__(self, path, log=print):
        self.path = path
        self.log = log
        self.matches = []
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    self.matches = [m for m in json.load(f) if isinstance(m, dict) and "won" in m]
            except (OSError, ValueError):
                log("matches.json illisible, historique vide")
                os.replace(path, path + ".bad")
        self._index()

    def _index(self):
        self.players = self.players_of(self.matches)

    @staticmethod
    def players_of(matches):
        """Joueurs croises : id -> {"name", "with": [V, D], "against": [V, D], "n", "last"}."""
        players = {}
        for m in matches:
            History._index_match(m, players)
        return players

    @staticmethod
    def _index_match(m, players):
        for side in ("with", "against"):
            for pid, name in m.get(side, []):
                p = players.setdefault(pid, {"name": name, "with": [0, 0], "against": [0, 0], "n": 0, "last": 0})
                p["name"] = name  # garde le pseudo le plus recent
                p[side][0 if m["won"] else 1] += 1
                p["n"] += 1
                p["last"] = max(p["last"], m["t"])

    def add(self, match):
        self.matches.append(match)
        self.matches = self.matches[-MAX_MATCHES:]
        self._index_match(match, self.players)
        self.save()

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.matches, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as e:
            self.log(f"Impossible d'enregistrer l'historique : {e}")

    # --- Requetes -----------------------------------------------------------

    def filter(self, period="all", mode=None):
        """period : "today", "7d", "30d" ou "all" (jours calendaires, aujourd'hui compris)."""
        days = {"today": 1, "7d": 7, "30d": 30}.get(period)
        since = datetime.date.today() - datetime.timedelta(days=days - 1) if days else None
        return [m for m in self.matches
                if (since is None or day_of(m["t"]) >= since) and (mode is None or m.get("mode") == mode)]

    @staticmethod
    def summary(matches):
        w = sum(1 for m in matches if m["won"])
        n = len(matches)
        best = cur = 0
        for m in matches:
            cur = cur + 1 if m["won"] else 0
            best = max(best, cur)
        played = [m["me"] for m in matches if m.get("me") and not m.get("forfeit")]

        def avg(key):
            return sum(p.get(key, 0) for p in played) / len(played) if played else 0

        return {"n": n, "w": w, "l": n - w, "pct": round(w * 100 / n) if n else 0, "best_streak": best,
                "mvp": sum(1 for p in played if p.get("mvp")),
                "goals": avg("goals"), "assists": avg("assists"), "saves": avg("saves"),
                "fastest": max((p.get("fastest", 0) for p in played), default=0)}

    @staticmethod
    def per_day(matches, period):
        """[(date, V, D)] pour chaque jour de la periode (jours sans match compris)."""
        counts = {}
        for m in matches:
            d = day_of(m["t"])
            c = counts.setdefault(d, [0, 0])
            c[0 if m["won"] else 1] += 1
        if not counts:
            return []
        today = datetime.date.today()
        days = {"today": 1, "7d": 7, "30d": 30}.get(period)
        start = today - datetime.timedelta(days=days - 1) if days else min(counts)
        out = []
        d = start
        while d <= today:
            w, l = counts.get(d, (0, 0))
            out.append((d, w, l))
            d += datetime.timedelta(days=1)
        return out[-90:]  # au-dela, les barres deviennent illisibles

    @staticmethod
    def teammates(matches):
        """Coequipiers : [{"id", "name", "w", "l", "last"}], les plus frequents d'abord."""
        mates = {}
        for m in matches:
            for pid, name in m.get("with", []):
                p = mates.setdefault(pid, {"id": pid, "name": name, "w": 0, "l": 0, "last": 0})
                p["name"] = name  # garde le pseudo le plus recent
                p["w" if m["won"] else "l"] += 1
                p["last"] = max(p["last"], m["t"])
        return sorted(mates.values(), key=lambda p: (-(p["w"] + p["l"]), -p["last"]))

    @staticmethod
    def by_hour(matches):
        """[[V, D]] pour chaque heure de la journee (0 a 23), heure de fin du match."""
        hours = [[0, 0] for _ in range(24)]
        for m in matches:
            hours[datetime.datetime.fromtimestamp(m["t"]).hour][0 if m["won"] else 1] += 1
        return hours

    @staticmethod
    def by_weekday(matches):
        """[[V, D]] pour chaque jour de la semaine (0 = lundi)."""
        days = [[0, 0] for _ in range(7)]
        for m in matches:
            days[day_of(m["t"]).weekday()][0 if m["won"] else 1] += 1
        return days

    @staticmethod
    def slots(matches, width=2, min_games=6):
        """Creneaux de `width` heures [(heure de debut, V, D)] qui ont au moins min_games matchs,
        du meilleur au moins bon taux de victoire (a egalite, le plus joue d'abord)."""
        hours = History.by_hour(matches)
        out = []
        for h in range(24):
            w = sum(hours[(h + i) % 24][0] for i in range(width))
            l = sum(hours[(h + i) % 24][1] for i in range(width))
            if w + l >= min_games:
                out.append((h, w, l))
        return sorted(out, key=lambda s: (-s[1] / (s[1] + s[2]), -(s[1] + s[2])))

    def met(self, pid):
        return self.players.get(pid)

    def export_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["date", "mode", "result", "forfeit", "my_team", "opponents", "goals", "assists",
                        "saves", "shots", "demos", "score", "mvp", "fastest_goal_kmh", "teammates", "opponents_names"])
            for m in self.matches:
                me = m.get("me") or {}
                score = m.get("score") or ["", ""]
                w.writerow([datetime.datetime.fromtimestamp(m["t"]).strftime("%Y-%m-%d %H:%M"), m.get("mode", ""),
                            "W" if m["won"] else "L", int(bool(m.get("forfeit"))), score[0], score[1],
                            me.get("goals", ""), me.get("assists", ""), me.get("saves", ""), me.get("shots", ""),
                            me.get("demos", ""), me.get("score", ""), int(bool(me.get("mvp"))),
                            round(me.get("fastest", 0)) or "",
                            ", ".join(n for _, n in m.get("with", [])),
                            ", ".join(n for _, n in m.get("against", []))])
