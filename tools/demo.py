"""Demo automatique de RL Stats, pour enregistrer la video YouTube.

Lance l'overlay depuis les sources avec des donnees de demo (dossier temporaire : ton vrai
historique n'est pas touche), ignore la vraie connexion a Rocket League et joue un scenario
d'environ 3 minutes : trois matchs simules (buts, victoire, defaite, resume, adversaires deja
croises), le menu, l'historique, les parametres, les styles, les couleurs et la carte de session.
Des legendes en bas de l'ecran expliquent chaque fonction.

Avant de lancer :
  - fermer RL Stats s'il tourne (icone pres de l'horloge > Quitter) ;
  - Rocket League ouvert en "plein ecran fenetre" (pas plein ecran exclusif), en entrainement
    libre ou sur un replay, HUD visible ;
  - les positions, la taille et l'echelle du HUD sont reprises de ta config (deplace l'overlay a la
    main dans l'app normale, pour chaque style / forme, avant de lancer la demo) ;
  - lancer l'enregistrement de l'ecran, puis :  .venv\\Scripts\\python.exe tools\\demo.py
Options : --lang fr|en (en par defaut), --name "Pseudo", --sounds (sons actives),
--short (clip d'environ 25 s pour Reddit / le site).
"""

import argparse
import importlib.machinery
import importlib.util
import contextlib
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEMO_DIR = os.path.join(tempfile.gettempdir(), "rl_stats_demo")
# Config de l'app installee (.exe) et de l'app lancee depuis les sources : la plus recente sert
REAL_CONFIGS = [os.path.join(os.environ.get("APPDATA", ""), "RL Stats", "stats.json"), os.path.join(ROOT, "stats.json")]
PLACEMENT = ("offsets", "offsets_1440", "size", "hud_scale", "monitor")  # repris de ta config : l'overlay est place comme d'habitude

CAPTIONS = {
    "intro": ("RL Stats : l'overlay gratuit pour Rocket League", "RL Stats: a free overlay for Rocket League"),
    "session": ("Victoires / défaites de la session et chrono, en direct",
                "Session wins / losses and a live timer"),
    "met": ("Adversaires déjà croisés, avec ton bilan contre eux", "Opponents you've met before, with your record"),
    "goal_for": ("Une animation sous le score à chaque but…", "An animation under the score on every goal…"),
    "goal_against": ("…et quand tu en encaisses un", "…and when you concede one"),
    "win": ("Victoire : animation et résumé du match", "Win: animation and match summary"),
    "loss": ("Défaite : le compteur se met à jour tout seul", "Loss: the counter updates by itself"),
    "match3": ("Rien à faire : tout est lu depuis le jeu (Stats API officielle)",
               "Nothing to do: everything is read from the game (official Stats API)"),
    "menu": ("Tout se règle depuis le clic droit", "Everything is one right-click away"),
    "history": ("Chaque match est enregistré : progression jour par jour", "Every game is saved: day-by-day progress"),
    "matches": ("Liste des matchs, export CSV", "Game list, CSV export"),
    "players": ("Les joueurs que tu as croisés", "The players you've met"),
    "mates": ("Ton taux de victoire avec chaque coéquipier", "Your win rate with each teammate"),
    "hours": ("Tes meilleures heures pour jouer", "Your best time to play"),
    "analysis": ("Stats avancées : engagements, boost, où tes buts entrent",
                 "Advanced stats: kickoffs, boost, where your goals go in"),
    "settings": ("Paramètres : sons, alertes, mode streamer OBS, Discord…",
                 "Settings: sounds, alerts, OBS streamer mode, Discord…"),
    "styles": ("Plusieurs styles et formes", "Several styles and shapes"),
    "colors": ("Tes couleurs", "Your colors"),
    "card": ("Carte de session, à coller sur Discord", "Session card, ready to paste in Discord"),
    "outro": ("Gratuit et open source : github.com/benguedj/RL_Stats",
              "Free and open source: github.com/benguedj/RL_Stats"),
    "outro_short": ("Gratuit et open source : benguedj.github.io/RL_Stats",
                    "Free and open source: benguedj.github.io/RL_Stats"),
}

TEAMMATE = ("Kyrios", "Epic|5f1c2a9be0d4|0")
OPPONENTS = [("Zephyr", "Steam|76561198044210771|0"), ("NovaRL", "Epic|9a7e33c1b2f0|0")]
POOL = ["Vortex", "Flixy", "Mako.", "Saturn", "Rizzo", "Kaze", "Blitz", "Lumen", "Orbit", "Dusk", "Nyx", "Toast",
        "Pixel", "Raptor", "Echo", "Sora", "Jinx", "Frost", "Nimbus", "Taz", "Ghosty", "Pulse", "Arrow", "Kiwi"]


def load_app():
    loader = importlib.machinery.SourceFileLoader("rl_stats_demo", os.path.join(ROOT, "rl_stats.pyw"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    rl = importlib.util.module_from_spec(spec)
    loader.exec_module(rl)
    return rl


def fake_history(name):
    """~30 jours de matchs credibles (taux de victoire en hausse), dont quelques-uns contre Zephyr."""
    rnd = random.Random(7)
    now = time.time()
    matches = []
    pool = [(n, f"Epic|{rnd.getrandbits(48):012x}|0") for n in POOL]
    for day in range(30, 0, -1):
        if rnd.random() < 0.25:
            continue  # jours sans jouer
        t = now - day * 86400 - rnd.uniform(0, 3) * 3600
        for _ in range(rnd.randint(2, 9)):
            t += rnd.uniform(6, 11) * 60
            mode = rnd.choices(["2v2", "3v3", "1v1"], [6, 3, 1])[0]
            won = rnd.random() < 0.44 + (30 - day) * 0.006
            size = int(mode[0])
            mine = rnd.randint(1, 5) if won else rnd.randint(0, 3)
            theirs = rnd.randint(0, mine - 1) if won else rnd.randint(mine + 1, mine + 3)
            goals = rnd.randint(0, min(3, mine))
            spots = [[rnd.randint(-850, 850), rnd.randint(60, 600)] for _ in range(goals)]
            others = rnd.sample(pool, 2 * size - 1)
            mates = ([TEAMMATE] if size > 1 and rnd.random() < 0.6 else []) + others[:size - 1]
            mates = mates[:size - 1]
            against = others[size - 1:size - 1 + size]
            matches.append({
                "t": t, "start": round(t - 330), "guid": f"{rnd.getrandbits(128):032X}", "mode": mode, "won": won,
                "forfeit": False, "score": [mine, theirs],
                "me": {"goals": goals, "assists": rnd.randint(0, 2), "saves": rnd.randint(0, 4),
                       "shots": goals + rnd.randint(0, 4), "demos": rnd.randint(0, 2),
                       "score": 120 + goals * 110 + rnd.randint(0, 260), "mvp": won and rnd.random() < 0.35,
                       "fastest": round(rnd.uniform(70, 135), 1) if goals else 0, "feed": {}, "goal_spots": spots,
                       "kickoffs": [rnd.randint(0, 3), rnd.randint(0, 2), rnd.randint(0, 2)],
                       "boost": {"avg": round(rnd.uniform(32, 48), 1), "zero": round(rnd.uniform(6, 16), 1),
                                 "superso": round(rnd.uniform(8, 18), 1), "n": 3000}},
                "with": [[pid, n] for n, pid in mates], "against": [[pid, n] for n, pid in against],
            })
    # Zephyr croise 5 fois (3 V, 2 D), NovaRL 2 fois
    picks = rnd.sample([m for m in matches if m["mode"] == "2v2"], 7)
    for i, m in enumerate(picks):
        name, pid = OPPONENTS[0] if i < 5 else OPPONENTS[1]
        m["against"][0] = [pid, name]
        m["won"] = i in (0, 2, 3, 6)
        if m["won"] != (m["score"][0] > m["score"][1]):
            m["score"].reverse()
    return matches


class Caption:
    """Legende en bas au milieu du jeu (fenetre que les clics traversent)."""

    def __init__(self, rl, app):
        self.rl, self.app = rl, app
        tk = rl.tk
        self.top = tk.Toplevel(app.root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.geometry("1x1+0+0")
        self.layer = rl.LayeredWindow(self.top, click_through=True)
        self.img = None
        self.job = None

    def _render(self, text):
        d = self.rl.designs
        k = self.app.scale()
        label = d.text_img([(text, d.font(round(34 * k), d.SEMI), d.FG, 0)], shear=0)
        pad_x, pad_y, m = round(30 * k), round(16 * k), round(20 * k)
        w, h = label.width + 2 * pad_x, label.height + 2 * pad_y
        img = d.Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
        shadow = d.Image.new("RGBA", img.size, (0, 0, 0, 0))
        d.ImageDraw.Draw(shadow).rounded_rectangle([m, m + 4 * k, m + w, m + h + 4 * k], radius=h / 2, fill=(0, 0, 0, 150))
        img.alpha_composite(shadow.filter(d.ImageFilter.GaussianBlur(10 * k)))
        d.ImageDraw.Draw(img).rounded_rectangle([m, m, m + w, m + h], radius=h / 2, fill=(11, 19, 34, 235),
                                                outline=d.EDGE, width=max(1, round(1.5 * k)))
        img.alpha_composite(label, (m + pad_x, m + pad_y))
        return img

    def show(self, text):
        self.img = self._render(text)
        vx, vy, vw, vh = self.app.viewport
        self.pos = (round(vx + vw / 2 - self.img.width / 2), round(vy + vh * 0.80 - self.img.height / 2))
        self.rl.place_tk_window(self.top, self.img, *self.pos)
        self.top.lift()
        self._fade(0)

    def _fade(self, alpha, target=255):
        if self.job:
            self.app.root.after_cancel(self.job)
            self.job = None
        alpha = max(0, min(255, alpha))
        self.layer.show(self.img if alpha else self.rl.empty_image(), *self.pos, alpha=alpha)
        if alpha != target:
            step = 32 if target > alpha else -32
            self.job = self.app.root.after(16, lambda: self._fade(alpha + step, target))

    def hide(self):
        if self.img is not None:
            self._fade(255, 0)


class Picture:
    """Image affichee au centre du jeu (carte de session)."""

    def __init__(self, rl, app):
        self.rl, self.app = rl, app
        self.top = rl.tk.Toplevel(app.root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.geometry("1x1+0+0")
        self.layer = rl.LayeredWindow(self.top, click_through=True)

    def show(self, img):
        vx, vy, vw, vh = self.app.viewport
        k = vh * 0.55 / img.height
        img = img.convert("RGBA").resize((round(img.width * k), round(img.height * k)), self.rl.designs.Image.LANCZOS)
        x, y = round(vx + vw / 2 - img.width / 2), round(vy + vh * 0.42 - img.height / 2)
        self.rl.place_tk_window(self.top, img, x, y)
        self.top.lift()
        self.layer.show(img, x, y)
        self.pos = (x, y)

    def hide(self):
        self.layer.show(self.rl.empty_image(), *self.pos)


class Match:
    """Match simule : envoie a l'overlay les memes messages que la Stats API du jeu."""

    def __init__(self, demo, mode_size, result_team):
        self.demo = demo
        self.guid = f"{random.getrandbits(128):032X}"
        me = demo.name
        self.players = [{"Name": me, "PrimaryId": "Epic|0d3m0c0ffee1|0", "TeamNum": 0}]
        if mode_size > 1:
            self.players.append({"Name": TEAMMATE[0], "PrimaryId": TEAMMATE[1], "TeamNum": 0})
        self.players += [{"Name": n, "PrimaryId": pid, "TeamNum": 1} for n, pid in OPPONENTS[:mode_size]]
        for p in self.players:
            p.update({"Score": 0, "Goals": 0, "Assists": 0, "Saves": 0, "Shots": 0, "Demos": 0})
        self.score = [0, 0]
        self.clock = 300
        self.ball_y = 0
        self.running = False
        self.winner = result_team

    def send(self, event, data=None):
        self.demo.app.q.put(("event", (event, dict(data or {}, MatchGuid=self.guid))))

    def player(self, name):
        return next(p for p in self.players if p["Name"] == name)

    def _state(self):
        if not self.running:
            return
        t = time.monotonic()
        players = []
        for p in self.players:
            q = dict(p)
            if p["TeamNum"] == 0:  # le jeu n'envoie le boost que pour notre equipe
                q["Boost"] = max(0, round(50 + 45 * math.sin(t * 0.7 + len(p["Name"]))))
                q["bSupersonic"] = q["Boost"] > 85
            players.append(q)
        self.send("UpdateState", {"Players": players, "Game": {
            "Teams": [{"TeamNum": 0, "Score": self.score[0]}, {"TeamNum": 1, "Score": self.score[1]}],
            "TimeSeconds": self.clock, "bHasWinner": False, "bReplay": False,
            "bHasTarget": True, "Target": {"Name": self.demo.name, "TeamNum": 0},
            "Ball": {"Location": {"X": 0, "Y": self.ball_y, "Z": 93}}}})
        self.demo.app.root.after(100, self._state)

    def start(self):
        self.send("MatchCreated")
        self.running = True
        self._state()
        self.demo.after(600, self.kickoff)

    def kickoff(self):
        self.ball_y = 0
        self.send("RoundStarted")
        self.demo.after(1000, lambda: self.send("BallHit", {"Ball": {"Location": {"X": 0, "Y": 0, "Z": 93}}}))
        self.demo.after(1500, lambda: setattr(self, "ball_y", 1500))

    def goal(self, scorer, team, speed=105.0, assister=None):
        """But de `scorer` ; `team` = equipe qui marque (differente pour un but contre son camp)."""
        p = self.player(scorer)
        if p["TeamNum"] == team:
            p["Goals"] += 1
            p["Shots"] += 1
            p["Score"] += 110
            self.send("StatfeedEvent", {"EventName": "Goal", "MainTarget": {"Name": scorer, "TeamNum": team}})
        if assister:
            self.player(assister)["Assists"] += 1
            self.player(assister)["Score"] += 60
        self.send("GoalScored", {"GoalSpeed": speed, "GoalTime": 10, "Scorer": {"Name": scorer, "TeamNum": p["TeamNum"]},
                                 "ImpactLocation": {"X": random.uniform(-700, 700), "Y": 5200 if team == 0 else -5200,
                                                    "Z": random.uniform(100, 550)}})
        self.score[team] += 1
        self.clock -= 40

    def save(self, name):
        self.player(name)["Saves"] += 1
        self.player(name)["Score"] += 50

    def end(self, mvp=None):
        if mvp:
            self.send("StatfeedEvent", {"EventName": "MVP", "MainTarget": {"Name": mvp, "TeamNum": 0}})
        self.send("MatchEnded", {"WinnerTeamNum": self.winner})
        self.demo.after(9000, self.destroy)

    def destroy(self):
        self.running = False
        self.send("MatchDestroyed")


class Demo:
    def __init__(self, rl, app, lang, name, speed=1.0):
        self.rl, self.app, self.name, self.speed = rl, app, name, speed
        self.fr = lang == "fr"
        self.caption = Caption(rl, app)
        self.picture = Picture(rl, app)
        self.steps = []
        self.at = 0.0

    def after(self, ms, fn):
        """root.after au rythme de la demo (--speed)."""
        self.app.root.after(int(ms / self.speed), fn)

    def text(self, key):
        return CAPTIONS[key][0 if self.fr else 1]

    def then(self, delay, fn, *args):
        """Planifie fn(*args) `delay` secondes apres l'etape precedente."""
        self.at += delay

        def run():
            try:
                fn(*args)
            except Exception as e:  # une etape ratee ne doit pas arreter la demo
                print(f"Etape {getattr(fn, '__name__', fn)} : {e!r}")
        self.app.root.after(int(self.at * 1000 / self.speed), run)

    def say(self, delay, key):
        self.then(delay, self.caption.show, self.text(key))

    def open_history(self):
        self.app.open_history()

    def history(self, method, value):
        getattr(self.app.history_window, method)(value)

    def close_history(self):
        if self.app.history_window:
            self.app.history_window.close()

    def open_settings(self):
        self.app.open_settings()

    def close_settings(self):
        if self.app.settings_window:
            self.app.settings_window.close()

    def open_menu(self):
        self.app.open_menu_from_game()  # comme le raccourci clavier : navigation au clavier visible

    def menu_down(self):
        if self.app.popup.is_open:
            self.app.popup.move(1)

    def close_menu(self):
        if self.app.popup.is_open:
            self.app.popup.close()

    def style(self, design, shape):
        self.app.store.data["design"], self.app.store.data["shape"] = design, shape
        self.app.store.save()
        self.app.draw()

    def colors(self, win, loss):
        self.app.set_option("win_color", win)
        self.app.set_option("loss_color", loss)

    def goal_alerts(self, enabled):
        self.app.store.data["goal_alert"] = enabled

    def card(self):
        self.picture.show(self.app.share_card())

    def script(self):
        app = self.app
        self.say(0.5, "intro")
        self.then(1.5, app.q.put, ("status", True))  # "connecte au jeu" : le chrono demarre
        self.say(3.5, "session")

        # --- Match 1 (2v2) : victoire 3-1
        m1 = Match(self, 2, 0)
        self.then(3.5, m1.start)
        self.say(1.5, "met")
        self.then(5.5, m1.goal, self.name, 0, 112.4, TEAMMATE[0])
        self.say(0.2, "goal_for")
        self.then(5.0, m1.kickoff)
        self.then(2.0, m1.goal, OPPONENTS[0][0], 1, 96.0)
        self.say(0.2, "goal_against")
        self.then(3.0, self.goal_alerts, False)  # chaque animation de but n'est montree qu'une fois
        self.then(2.0, m1.kickoff)
        self.then(1.5, m1.save, self.name)
        self.then(1.5, m1.goal, TEAMMATE[0], 0, 88.3, self.name)
        self.then(4.0, m1.kickoff)
        self.then(1.5, m1.goal, self.name, 0, 127.9)
        self.then(3.5, m1.end, self.name)
        self.say(0.2, "win")
        self.then(11.0, self.caption.hide)

        # --- Match 2 (2v2) : defaite 1-2
        m2 = Match(self, 2, 1)
        self.then(1.0, m2.start)
        self.then(3.0, m2.goal, self.name, 0, 101.2)
        self.then(4.0, m2.kickoff)
        self.then(1.5, m2.goal, OPPONENTS[1][0], 1, 93.5, OPPONENTS[0][0])
        self.then(4.0, m2.kickoff)
        self.then(1.5, m2.goal, OPPONENTS[0][0], 1, 118.0)
        self.then(3.0, m2.end)
        self.say(0.2, "loss")
        self.then(9.0, self.caption.hide)

        # --- Match 3 (2v2) : victoire 2-0, rapide
        m3 = Match(self, 2, 0)
        self.then(1.0, m3.start)
        self.say(0.5, "match3")
        self.then(3.0, m3.goal, TEAMMATE[0], 0, 99.0)
        self.then(3.5, m3.kickoff)
        self.then(1.5, m3.goal, self.name, 0, 121.6, TEAMMATE[0])
        self.then(3.0, m3.end, self.name)
        self.then(9.0, self.caption.hide)

        # --- Menu clic droit
        self.say(1.0, "menu")
        self.then(1.0, self.open_menu)
        for _ in range(4):
            self.then(0.7, self.menu_down)
        self.then(1.5, self.close_menu)

        # --- Historique
        self.say(1.0, "history")
        self.then(0.5, self.open_history)
        self.then(4.0, self.history, "set_period", "30d")
        self.then(4.0, self.history, "set_tab", "matches")
        self.say(0.0, "matches")
        self.then(4.5, self.history, "set_tab", "players")
        self.say(0.0, "players")
        self.then(4.5, self.history, "set_tab", "analysis")
        self.say(0.0, "analysis")
        self.then(6.0, self.close_history)

        # --- Parametres
        self.say(0.5, "settings")
        self.then(0.5, self.open_settings)
        self.then(6.0, self.close_settings)

        # --- Styles et couleurs
        self.say(0.8, "styles")
        for design, shape in (("tableau", "droit"), ("tableau", "arrondi"), ("minimal", "arrondi"),
                              ("minimal", "droit"), ("minimal", "vertical")):
            self.then(0.5 if design == "tableau" and shape == "droit" else 3.0, self.style, design, shape)
        self.then(3.0, self.style, "tableau", "vertical")
        self.say(1.0, "colors")
        for win, loss in self.rl_presets()[1:] + self.rl_presets()[:1]:
            self.then(2.2, self.colors, win, loss)

        # --- Carte de session
        self.say(2.0, "card")
        self.then(0.5, self.card)
        self.then(6.0, self.picture.hide)

        self.say(0.8, "outro")
        self.then(6.0, self.caption.hide)
        self.then(1.5, app.quit)

    def short_script(self):
        """~25 s pour Reddit / le site : un match rythme (3 buts), victoire, resume et tour de l'historique."""
        app = self.app
        app.store.data["summary_time"] = 4
        self.then(0.3, app.q.put, ("status", True))

        m = Match(self, 2, 0)
        self.then(0.2, m.start)
        self.say(0.1, "met")
        self.then(1.6, m.goal, self.name, 0, 112.4, TEAMMATE[0])
        self.say(0.1, "goal_for")
        self.then(1.5, m.goal, OPPONENTS[0][0], 1, 96.0)
        self.say(0.1, "goal_against")
        self.then(1.4, m.goal, TEAMMATE[0], 0, 88.3, self.name)
        self.then(1.2, m.end, self.name)
        self.say(0.1, "win")

        # Tour rapide de l'historique, une fois le resume affiche
        self.say(5.0, "history")
        self.then(0.1, self.open_history)
        self.then(0.1, self.history, "set_period", "30d")
        for delay, tab, key in ((2.2, "mates", "mates"), (2.2, "hours", "hours"), (2.2, "analysis", "analysis")):
            self.then(delay, self.history, "set_tab", tab)
            self.say(0.0, key)
        self.then(2.4, self.close_history)

        self.say(0.2, "outro_short")
        self.then(2.5, app.quit)

    def rl_presets(self):
        from ui_windows import COLOR_PRESETS
        return list(COLOR_PRESETS)


def main():
    parser = argparse.ArgumentParser(description="Demo automatique de RL Stats")
    parser.add_argument("--lang", choices=("en", "fr"), default="en")
    parser.add_argument("--name", default="Ben")
    parser.add_argument("--sounds", action="store_true")
    parser.add_argument("--speed", type=float, default=1.0, help="essai accelere (ex. 4)")
    parser.add_argument("--short", action="store_true", help="clip d'environ 25 s (Reddit, site)")
    args = parser.parse_args()

    shutil.rmtree(DEMO_DIR, ignore_errors=True)
    os.makedirs(DEMO_DIR)
    with open(os.path.join(DEMO_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(fake_history(args.name), f)
    placement = {}
    configs = [p for p in REAL_CONFIGS if os.path.exists(p)]
    with contextlib.suppress(OSError, ValueError):
        with open(max(configs, key=os.path.getmtime), encoding="utf-8") as f:
            placement = {k: v for k, v in json.load(f).items() if k in PLACEMENT}
    placement.setdefault("hud_scale", 100)  # sans elle, l'app oublie les decalages (anciennes versions)
    with open(os.path.join(DEMO_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump({**placement, "player_name": args.name, "lang": args.lang, "design": "tableau", "shape": "vertical",
                   "animations": True, "sounds": args.sounds, "summary": True, "summary_time": 7,
                   "met_alert": True, "goal_alert": True, "session_timer": True, "check_updates": False,
                   "hotkeys": False, "discord": False, "obs": False, "tilt_alert": False, "resume_session": False,
                   "auto_hide": False, "tray": True, "taskbar": True}, f)

    rl = load_app()
    # Donnees de demo, et rien qui touche au vrai jeu ou a Discord
    rl.DATA_DIR = DEMO_DIR
    rl.DATA_FILE = os.path.join(DEMO_DIR, "stats.json")
    rl.HISTORY_FILE = os.path.join(DEMO_DIR, "matches.json")
    rl.LOG_FILE = os.path.join(DEMO_DIR, "overlay.log")
    rl.DISCORD_CLIENT_ID = ""
    rl.ensure_stats_api_enabled = lambda: False

    class NoApi:
        def __init__(self, *a):
            pass

        def start(self):
            pass

    rl.ApiListener = NoApi
    with contextlib.suppress(AttributeError, OSError):
        rl.ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RLStats.Demo")
    app = rl.Overlay(rl.socket.socket())
    demo = Demo(rl, app, args.lang, args.name, args.speed)
    demo.short_script() if args.short else demo.script()
    app.run()


if __name__ == "__main__":
    main()
