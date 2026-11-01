"""Test de la fenetre Entrainement et du chrono des engagements, sans lancer Rocket League.

Lance l'overlay depuis les sources avec des donnees de test (dossier temporaire : ton vrai
historique n'est pas touche), ouvre la fenetre Entrainement et simule un match 2v2 en ligne avec
un engagement toutes les quelques secondes : tantot toi, tantot un coequipier ou un adversaire au
ballon, avec un resultat gagne / perdu / neutre. Le chrono sur l'overlay est active.

Fermer RL Stats avant (une seule instance a la fois), puis :  .venv\\Scripts\\python.exe tools\\training_test.py
Options : --lang fr|en (fr par defaut), --name "Pseudo", --every 6 (secondes entre deux engagements),
--drill (pack d'engagements en entrainement personnalise au lieu d'un match), --limit 2 (limite de temps du pack).
"""

import argparse
import contextlib
import importlib.machinery
import importlib.util
import json
import math
import os
import random
import shutil
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(tempfile.gettempdir(), "rl_stats_training_test")
# Config de l'app installee (.exe) et de l'app lancee depuis les sources : la plus recente sert
REAL_CONFIGS = [os.path.join(os.environ.get("APPDATA", ""), "RL Stats", "stats.json"), os.path.join(ROOT, "stats.json")]
PLACEMENT = ("offsets", "offsets_1440", "size", "hud_scale", "monitor", "design", "shape", "win_color", "loss_color")


def load_app():
    loader = importlib.machinery.SourceFileLoader("rl_stats_training_test", os.path.join(ROOT, "rl_stats.pyw"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    rl = importlib.util.module_from_spec(spec)
    loader.exec_module(rl)
    return rl


def fake_history():
    """Une vingtaine de matchs sur 30 jours, avec des engagements chronometres."""
    rnd = random.Random(3)
    now = time.time()
    matches = []
    for i in range(20):
        times = [round(rnd.uniform(2.15, 2.75), 2) for _ in range(rnd.randint(1, 4))]
        matches.append({
            "t": now - rnd.uniform(1, 29) * 86400, "guid": f"{rnd.getrandbits(128):032X}", "mode": "2v2",
            "won": rnd.random() < 0.5, "forfeit": False, "score": [2, 1], "with": [], "against": [],
            "me": {"goals": 1, "assists": 0, "saves": 1, "shots": 2, "demos": 0, "score": 300,
                   "kickoffs": [rnd.randint(1, 3), rnd.randint(0, 3), rnd.randint(0, 2)],
                   "kick_first": [len(times), rnd.randint(0, 2), rnd.randint(1, 4)], "kick_times": times}})
    return sorted(matches, key=lambda m: m["t"])


class FakeMatch:
    """Match 2v2 en ligne : etat du jeu 10 fois par seconde et un engagement toutes les `every` secondes."""

    def __init__(self, app, name, every):
        self.app, self.name, self.every = app, name, every
        self.guid = "7E57" + os.urandom(14).hex().upper()
        self.players = [{"Name": name, "PrimaryId": "Epic|7e57000000a1|0", "TeamNum": 0},
                        {"Name": "Kyrios", "PrimaryId": "Epic|7e57000000a2|0", "TeamNum": 0},
                        {"Name": "Zephyr", "PrimaryId": "Steam|76561198000000001|0", "TeamNum": 1},
                        {"Name": "NovaRL", "PrimaryId": "Epic|7e57000000a3|0", "TeamNum": 1}]
        self.ball_y = 0
        self.rnd = random.Random()

    def send(self, event, data=None):
        self.app.q.put(("event", (event, dict(data or {}, MatchGuid=self.guid), time.perf_counter())))

    def start(self):
        self.send("MatchCreated")
        self._state()
        self.app.root.after(1500, self.kickoff)

    def _state(self):
        players = [dict(p, Boost=50) if p["TeamNum"] == 0 else dict(p) for p in self.players]
        self.send("UpdateState", {"Players": players, "Game": {
            "Teams": [{"TeamNum": 0, "Score": 0}, {"TeamNum": 1, "Score": 0}], "TimeSeconds": 300,
            "bHasWinner": False, "bReplay": False, "bHasTarget": True, "Target": {"Name": self.name, "TeamNum": 0},
            "Ball": {"Location": {"X": 0, "Y": self.ball_y, "Z": 93}}}})
        self.app.root.after(100, self._state)

    def kickoff(self):
        self.ball_y = 0
        self.send("RoundStarted")
        toucher = self.rnd.choices(self.players, [5, 2, 3, 3])[0]
        delay = self.rnd.uniform(2.1, 2.8)
        hit = {"Players": [{"Name": toucher["Name"], "TeamNum": toucher["TeamNum"]}],
               "Ball": {"PreHitSpeed": 0, "PostHitSpeed": 60, "Location": {"X": 0, "Y": 0, "Z": 93}}}
        self.app.root.after(int(delay * 1000), lambda: self.send("BallHit", hit))
        ball_y = self.rnd.choice([2000, -2000, 0])  # chez l'adversaire, chez nous, au milieu
        self.app.root.after(int(delay * 1000) + 1000, lambda: setattr(self, "ball_y", ball_y))
        # Le resultat tombe 2,5 s apres le premier contact : le prochain engagement attend au moins ca
        self.app.root.after(int(max(self.every, delay + 3.5) * 1000), self.kickoff)


class FakePad:
    """Manette simulee : etats (instant, boutons, stick X, stick Y) que FakeDrill remplit a chaque tir."""

    connected = True

    def __init__(self, pad):
        self.buttons = pad.BUTTONS
        self.samples = []

    def window(self, t0, t1):
        before = [s for s in self.samples if s[0] < t0][-1:]
        return before + [s for s in self.samples if t0 <= s[0] <= t1]

    def held(self):
        return set()


class FakeDrill:
    """Pack d'engagements en entrainement personnalise, comme le jeu l'envoie : CountdownBegin a chaque tir,
    RoundStarted au premier mouvement, vitesse de la voiture (km/h) 10 fois par seconde, puis BallHit au
    contact, ou un faux but sans buteur quand la limite de temps du pack est atteinte (le ballon disparait)."""

    DISTANCES = {"diag": 3100, "offc": 3650, "back": 4400}  # distance parcourue jusqu'au contact

    def __init__(self, app, name, limit):
        self.app, self.name, self.limit = app, name, limit
        self.pad = app.pad if isinstance(app.pad, FakePad) else None
        self.rnd = random.Random()
        self.speed = 0.0
        self.ball = 0.0

    def send(self, event, data=None):
        self.app.q.put(("event", (event, dict(data or {}, MatchGuid=""), time.perf_counter())))

    def start(self):
        self.send("MatchCreated")
        self._state()
        self.app.root.after(1500, self.shot)

    def _state(self):
        self.send("UpdateState", {"Players": [{"Name": self.name, "TeamNum": 0, "Boost": 100, "Speed": self.speed}],
                                  "Game": {"TimeSeconds": 0, "bHasWinner": False, "bReplay": False,
                                           "Ball": {"Speed": self.ball, "TeamNum": 255}, "bHasTarget": True,
                                           "Target": {"Name": self.name, "TeamNum": 0}}})
        self.app.root.after(100, self._state)

    def inputs(self, go):
        """Speed flip simule (boutons par defaut : A saut, B boost, RB air roll droite) : angle, delai du
        cancel et oubli du cancel varient d'un tir a l'autre."""
        if not self.pad:
            return
        b = self.pad.buttons
        held = b["B"] | b["RT"]
        j1 = go + self.rnd.uniform(0.35, 0.6)
        j2 = j1 + self.rnd.uniform(0.06, 0.14)
        angle = math.radians(self.rnd.choice([-1, 1]) * self.rnd.uniform(8, 60))
        x, y = math.sin(angle), math.cos(angle)
        cancel = self.rnd.choice([None, 0.03, 0.05, 0.09, 0.16])
        self.pad.samples += [(go, held, 0.1, 0.0), (j1, held | b["A"], 0.1, 0.0), (j1 + 0.05, held, 0.1, 0.0),
                             (j2 - 0.01, held, x, y), (j2, held | b["A"] | b["RB"], x, y)]
        if cancel:
            self.pad.samples.append((j2 + cancel, held | b["RB"], -x * 0.3, -0.9))
        self.pad.samples.append((j2 + 0.4, held, 0.0, 0.0))

    @staticmethod
    def profile(t, skill):
        """Vitesse (km/h) a l'instant t : boost depuis l'arret, flip vers 0,7 s, plafond a 83 km/h."""
        return min(83.0, (8 + 52 * t) * skill + (18 if t > 0.7 else 0))

    def shot(self):
        spawn = self.rnd.choice(list(self.DISTANCES))
        skill = self.rnd.uniform(0.9, 1.15)
        t, dist = 0.0, 0.0
        while dist < self.DISTANCES[spawn]:  # instant du contact pour cette position et ce niveau
            t += 0.001
            dist += self.profile(t, skill) * 100000 / 3600 * 0.001
        contact = t
        self.send("CountdownBegin")
        self.speed, self.ball = 0.0, 0.0
        go = []  # instant du depart : le joueur bouge une seconde apres la remise en place

        def start():
            go.append(time.perf_counter())
            self.send("RoundStarted")
            self.inputs(go[0])
            drive()

        def drive():
            elapsed = time.perf_counter() - go[0]
            end = min(contact, self.limit) if self.limit else contact
            if elapsed < end:
                self.speed = self.profile(max(0.0, elapsed), skill)
                self.app.root.after(20, drive)
            elif self.limit and contact > self.limit:
                self.send("GoalScored", {"GoalSpeed": 0.0, "Scorer": {"Name": "", "TeamNum": 0}})
                self.speed = 0.0
                self.app.root.after(1500, self.shot)
            else:
                self.send("BallHit", {"Players": [{"Name": self.name, "TeamNum": 0}],
                                      "Ball": {"PreHitSpeed": 0, "PostHitSpeed": 70}})
                self.ball = 70.0
                self.app.root.after(2000, self.shot)
        self.app.root.after(1000, start)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("fr", "en"), default="fr")
    parser.add_argument("--name", default="Moi")
    parser.add_argument("--every", type=float, default=6)
    parser.add_argument("--drill", action="store_true", help="pack d'engagements en entrainement personnalise")
    parser.add_argument("--limit", type=float, default=0, help="limite de temps du pack (0 : aucune)")
    args = parser.parse_args()

    shutil.rmtree(TEST_DIR, ignore_errors=True)
    os.makedirs(TEST_DIR)
    with open(os.path.join(TEST_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(fake_history(), f)
    placement = {}
    configs = [p for p in REAL_CONFIGS if os.path.exists(p)]
    with contextlib.suppress(OSError, ValueError):
        with open(max(configs, key=os.path.getmtime), encoding="utf-8") as f:
            placement = {k: v for k, v in json.load(f).items() if k in PLACEMENT}
    placement.setdefault("hud_scale", 100)  # sans elle, l'app oublie les decalages (anciennes versions)
    with open(os.path.join(TEST_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump({**placement, "player_name": args.name, "lang": args.lang, "kickoff_alert": True,
                   "training": {"speedflip": 1, "frontflip": 2}, "summary": False, "met_alert": False,
                   "check_updates": False, "hotkeys": False, "obs": False,
                   "resume_session": False, "auto_hide": False}, f)

    rl = load_app()
    # Donnees de test, et rien qui touche au vrai jeu
    rl.DATA_DIR = TEST_DIR
    rl.DATA_FILE = os.path.join(TEST_DIR, "stats.json")
    rl.HISTORY_FILE = os.path.join(TEST_DIR, "matches.json")
    rl.LOG_FILE = os.path.join(TEST_DIR, "overlay.log")
    rl.ensure_stats_api_enabled = lambda: False

    class NoApi:
        def __init__(self, *a):
            pass

        def start(self):
            pass

    rl.ApiListener = NoApi
    with contextlib.suppress(AttributeError, OSError):
        rl.ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RLStats.TrainingTest")
    app = rl.Overlay(rl.socket.socket())
    app.q.put(("status", True))  # "connecte au jeu"
    app.root.after(800, app.open_training)
    if args.drill:
        app.root.after(900, lambda: app.training_window and app.training_window.set_page("kick_drill"))
        app.pad = FakePad(rl.pad)
        app.store.data["pad"] = dict(rl.pad.DEFAULT_BINDINGS, roll_r="RB")
        FakeDrill(app, args.name, args.limit).start()
    else:
        FakeMatch(app, args.name, args.every).start()
    app.run()


if __name__ == "__main__":
    main()
