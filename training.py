"""Fenetre Entrainement : chrono des engagements et guides des mecaniques.

L'API Stats du jeu ne donne ni la position de la voiture, ni son orientation, ni les touches
pressees : on ne peut mesurer que les engagements (temps entre le GO et le premier contact, et qui
touche en premier). Pour le reste, les guides expliquent et le joueur note lui-meme sa progression.

Texte des guides : "## " titre, "- " puce, "1. " etape, "> " conseil encadre, sinon paragraphe.
"""

import datetime
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


def diff_text(value):
    text = f"{value:+.2f}"
    return text.replace(".", ",") if lang() == "fr" else text


def flip_cells(flip):
    """[(libelle, valeur, note)] des mesures d'un speed flip (carte de l'overlay et fenetre)."""
    def ms(v):
        return f"{round(v * 1000)} ms" if v is not None else "–"

    def side(a):
        return T("pf_left") if a < 0 else T("pf_right")

    flipped = flip["flip"] is not None
    return [
        (T("pf_jump"), seconds_text(flip["jump"]) if flip["jump"] is not None else "–", None),
        (T("pf_flip"), ms(flip["flip"]), pad.grade("flip", flip["flip"])),
        (T("pf_angle"), f"{abs(flip['angle'])}° {side(flip['angle'])}" if flip["angle"] is not None else "–",
         pad.grade("angle", flip["angle"]) if flipped else None),
        (T("pf_cancel"), ms(flip["cancel"]), pad.grade("cancel", flip["cancel"]) if flipped else None),
        (T("pf_roll"), {"l": T("pf_left"), "r": T("pf_right"), "x": T("pf_yes")}.get(flip["roll"], "–"), None),
        (T("pf_boost"), f"{flip['boost']} %" if flip["boost"] is not None else "–",
         pad.grade("boost", flip["boost"])),
    ]


def flip_card_info(attempt, targets):
    """Textes de la carte affichee sur l'overlay apres un essai du defi (designs.render_flip_card)."""
    if attempt["miss"]:
        title, state, diff = T("dr_miss").upper(), "miss", ""
    else:
        gap = attempt["dt"] - targets[attempt["spawn"]]
        title, state, diff = T("tr_" + attempt["spawn"]).upper(), "ok" if gap <= 0 else "slow", diff_text(gap)
    return {"title": title, "time": seconds_text(attempt["dt"]), "diff": diff, "state": state,
            "cells": [(label.upper(), value, note) for label, value, note in flip_cells(attempt["flip"])],
            "advice": T(pad.advice(attempt["flip"]))}


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
## Les étapes
1. Accélère et boost dès le GO. Garde le boost jusqu'au contact.
2. Tourne très légèrement d'un côté, un court instant, pour que la voiture parte de biais.
3. Saute, puis flip en diagonale avant vers l'autre côté (environ 45°).
4. Juste après le début du flip, tire le stick vers l'arrière pour annuler la rotation : c'est le flip cancel.
5. En même temps, maintiens l'air roll qui garde la voiture à plat. Un seul côté marche avec ton côté de flip : teste les deux.
6. Atterris sur les roues, toujours en boost, puis flip avant dans le ballon à environ une longueur de voiture.
> Si la voiture fait un tour complet, tu annules trop tard. Si elle retombe sur le côté ou sur le toit, change d'air roll.
## S'entraîner
- Entraînement libre : travaille d'abord le flip cancel seul, en ligne droite, sans ballon.
- Match d'exhibition contre des bots ou match privé : chaque but relance un engagement, et l'app te donne ton temps dans « Tes engagements ».
- Le plugin BakkesMod « SpeedFlipTrainer » (hors ligne, sans lien avec RL Stats) analyse chaque tentative.""",
              """The fastest flip in the game: the car goes diagonally but does not tip over, so it keeps its speed. It is how good players take kickoffs, and it also helps you reach a ball on the ground quickly.
## Before you start
- Bind air roll left and air roll right (Settings > Controls). You will also need them for the half flip and aerials.
## Steps
1. Throttle and boost from GO. Keep boosting until you touch the ball.
2. Steer very slightly to one side for a moment, so the car goes a bit sideways.
3. Jump, then flip diagonally forward toward the other side (about 45°).
4. Right after the flip starts, pull the stick back to stop the rotation: the flip cancel.
5. At the same time, hold the air roll that keeps the car flat. Only one side works with your flip side: try both.
6. Land on your wheels, still boosting, then front flip into the ball about one car length away.
> If the car does a full rotation, you cancel too late. If it lands on its side or roof, switch air roll.
## Practice
- Free play: first practice the flip cancel on its own, in a straight line, without the ball.
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
3. Après chaque tir, l'overlay affiche ton temps et l'écart avec l'objectif : vert si tu es dessous, rouge sinon.
- Ça marche aussi en match privé ou d'exhibition contre des bots : le chrono part alors au GO.
> Les packs avec une limite de temps (2 s pour celui de Musty) arrêtent le tir avant le contact s'il est trop lent : l'app le compte comme « pas touché ».
- Les objectifs par défaut sont des estimations pour un engagement rapide avec speed flip. Règle-les sur ton niveau, puis baisse-les petit à petit.""",
              """## How to practice
1. Training > Custom training: load a kickoff pack (car on the real kickoff spawns, ball in the center).
2. The timer starts on your first movement and stops when you touch the ball. The app recognizes your spawn from the distance your car traveled.
3. After each shot, the overlay shows your time and the gap to your target: green when you beat it, red otherwise.
- It also works in private matches or exhibitions against bots: the timer then starts at GO.
> Packs with a time limit (2 s in Musty's pack) end the shot before contact if you are too slow: the app counts it as "missed".
- The default targets are estimates for a fast speed flip kickoff. Set them to your level, then lower them bit by bit.""")


# --------------------------------------------------------------------------
# Fenetre
# --------------------------------------------------------------------------

class TrainingWindow:
    def __init__(self, app):
        self.app = app
        self.page = "kick_stats"
        self.capturing = None  # action dont on attend le bouton (assignation de la manette)
        self.win = _dark_window(app.root, T("tr_title"), (940, 680), app.viewport)
        self.win.minsize(780, 520)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.build()

    def close(self):
        self.app.training_window = None
        self.win.destroy()

    def refresh(self):
        """Appele a chaque engagement : seules les pages des chronos changent."""
        if self.page in ("kick_stats", "kick_drill"):
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
        if self.page == "kick_stats":
            self.show_stats()
        elif self.page == "kick_drill":
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
        for group, title in (("kick", T("tr_kickoffs")), ("mech", T("tr_mechanics"))):
            tk.Label(self.nav, text=title.upper(), bg=BG, fg=MUTED, font=("Bahnschrift SemiBold", 10),
                     anchor="w").pack(fill="x", pady=(0 if group == "kick" else 14, 4))
            entries = [("kick_stats", T("tr_stats"), None), ("kick_drill", T("dr_title"), None)] \
                if group == "kick" else []
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

    # --- Tes engagements ----------------------------------------------------

    def show_stats(self):
        self._title(T("tr_stats"))
        tk.Label(self.content, text=T("tr_period"), bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x")
        mes = [m.get("me") or {} for m in self.app.history.filter("30d", None)]
        first = [sum(me.get("kick_first", [0, 0, 0])[i] for me in mes) for i in range(3)]
        times = [t for me in mes for t in me.get("kick_times", [])]
        kick = [sum(me.get("kickoffs", [0, 0, 0])[i] for me in mes) for i in range(3)]
        touched, decided = sum(first), kick[0] + kick[1]
        self._tiles([
            (T("tr_first"), f"{round(first[0] * 100 / touched)} %" if touched else "–",
             T("tr_first_sub", me=first[0], n=touched)),
            (T("tr_avg"), seconds_text(sum(times) / len(times)) if times else "–", T("tr_avg_sub")),
            (T("tr_best"), seconds_text(min(times)) if times else "–", T("tr_avg_sub")),
            (T("h_kickoffs"), f"{round(kick[0] * 100 / decided)} %" if decided else "–",
             T("h_kickoffs_sub", w=kick[0], l=kick[1], n=kick[2])),
        ])

        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x", pady=(12, 0))
        var = tk.BooleanVar(value=self.app.store["kickoff_alert"])
        self.vars.append(var)
        tk.Checkbutton(box, text=T("tr_alert"), variable=var, bg=PANEL, fg=FG, font=BODY_FONT, selectcolor=BG,
                       activebackground=PANEL, activeforeground=FG, anchor="w", highlightthickness=0, bd=0,
                       command=lambda: self.app.set_option("kickoff_alert", var.get())).pack(
            fill="x", padx=12, pady=(10, 2))
        self._label(box, T("tr_how"), fg=MUTED, font=("Segoe UI", 9), bg=PANEL, margin=70, padx=12, pady=(0, 10))

        tk.Label(self.content, text=T("tr_session"), bg=BG, fg=FG, font=TITLE_FONT, anchor="w").pack(
            fill="x", pady=(16, 4))
        log = list(reversed(self.app.kick_log))[:15]
        if not log:
            self._label(self.content, T("tr_no_kick"), fg=MUTED)
            return
        win_c, loss_c = self.app.store["win_color"], self.app.store["loss_color"]
        who_colors = {"me": win_c, "opp": loss_c, "mate": FG}
        result_colors = {"won": win_c, "lost": loss_c}
        self._table(("tr_col_time", "tr_col_game", "tr_col_first", "dr_col_spawn", "tr_col_dt", "tr_col_result"), [[
            (datetime.datetime.fromtimestamp(k["t"]).strftime("%H:%M"), MUTED),
            (T("tr_online", mode=k["mode"] or "") if k["online"] else T("tr_offline"), MUTED),
            (T("tr_" + k["who"]), who_colors[k["who"]]),
            (T("tr_" + k["spawn"]) if k.get("spawn") else "–", MUTED),
            (seconds_text(k["dt"]), FG),
            (T("tr_" + k["result"]) if k["result"] else "–", result_colors.get(k["result"], MUTED)),
        ] for k in log])

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

    # --- Defi engagements ---------------------------------------------------

    def show_drill(self):
        self._title(T("dr_title"))
        self._label(self.content, T("dr_intro"), fg=MUTED, pady=(2, 0))
        targets, drill = self.app.store["kick_targets"], self.app.store["drill"]
        tiles = []
        for spawn in SPAWN_KEYS:
            tries = [a for a in drill if a["spawn"] == spawn]
            ok = [a for a in tries if a["dt"] <= targets[spawn]]
            best = min((a["dt"] for a in tries), default=None)
            tiles.append((T("tr_" + spawn), f"{round(len(ok) * 100 / len(tries))} %" if tries else "–",
                          T("dr_tile_sub", ok=len(ok), n=len(tries), best=seconds_text(best) if best else "–")))
        tiles.append((T("dr_missed"), str(sum(1 for a in drill if a["miss"])), T("dr_missed_sub")))
        self._tiles(tiles)

        box = tk.Frame(self.content, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        box.pack(fill="x", pady=(12, 0))
        tk.Label(box, text=T("dr_targets"), bg=PANEL, fg=FG, font=BODY_FONT, anchor="w").pack(
            fill="x", padx=12, pady=(8, 2))
        row = tk.Frame(box, bg=PANEL)
        row.pack(fill="x", padx=6, pady=(0, 10))
        for spawn in SPAWN_KEYS:
            group = tk.Frame(row, bg=PANEL)
            group.pack(side="left", padx=(6, 14))
            tk.Label(group, text=T("tr_" + spawn), bg=PANEL, fg=MUTED, font=BODY_FONT).pack(side="left", padx=(0, 6))
            for delta, sign in ((-0.05, "\u2212"), (0.05, "+")):
                button = _button(group, sign, lambda s=spawn, d=delta: self.set_target(s, d), bg=EDGE)
                button.configure(padx=6)
                if delta > 0:
                    tk.Label(group, text=seconds_text(targets[spawn]), bg=PANEL, fg=FG,
                             font=("Bahnschrift SemiBold", 11), width=7).pack(side="left")
                button.pack(side="left")

        self._last_flip(drill)
        self._pad_box()
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
        rows = []
        for a in recent:
            when = datetime.datetime.fromtimestamp(a["t"]).strftime("%H:%M")
            time_text = ("" if a.get("exact", True) else "≈ ") + seconds_text(a["dt"])
            grade_colors = {"ok": win_c, "warn": WARN, "bad": loss_c, None: FG}
            flip = [(value, grade_colors[note]) for _, value, note in flip_cells(a["flip"])][2:4] \
                if a.get("flip") else [("–", MUTED)] * 2
            if a["miss"]:
                rows.append([(when, MUTED), ("–", MUTED), (time_text, FG), ("–", MUTED)] + flip
                            + [(T("dr_miss"), WARN)])
                continue
            gap = a["dt"] - targets[a["spawn"]]
            color = win_c if gap <= 0 else loss_c
            rows.append([(when, MUTED), (T("tr_" + a["spawn"]), FG), (time_text, FG), (diff_text(gap), color)] + flip
                        + [(T("dr_ok" if gap <= 0 else "dr_slow"), color)])
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
        for col, (label, value, note) in enumerate(flip_cells(last)):
            cells.grid_columnconfigure(col, weight=1, uniform="flip")
            tk.Label(cells, text=value, bg=PANEL, fg=colors[note], font=("Bahnschrift SemiBold", 15)).grid(
                row=0, column=col, sticky="w")
            tk.Label(cells, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).grid(row=1, column=col, sticky="w")
        self._label(right, T(pad.advice(last)), bg=PANEL, font=("Bahnschrift SemiBold", 11), margin=260,
                    pady=(12, 4))
        best = sorted((a for a in drill if a.get("flip") and not a["miss"] and a["flip"]["flip"] is not None),
                      key=lambda a: a["dt"] - self.app.store["kick_targets"][a["spawn"]])[:5]
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

    def _draw_stick(self, c, flip):
        """Stick gauche vu de face (haut = avant) : zone 20-45 degres, trajet autour du flip, direction du flip
        et point du cancel."""
        size = int(c["width"])
        cx = cy = size / 2
        r = size / 2 - 12
        win_c, loss_c = self.app.store["win_color"], self.app.store["loss_color"]
        for lo, hi in ((20, 45), (-45, -20)):  # zones conseillees pour le flip
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
        self._label(box, T("sg_move_hint"), fg=MUTED, bg=PANEL, font=("Segoe UI", 9), margin=70, padx=12)
        grid = tk.Frame(box, bg=PANEL)
        grid.pack(fill="x", padx=8, pady=(4, 10))
        bindings = self.app.store["pad"]
        for i, action in enumerate(("jump", "boost", "roll", "roll_l", "roll_r")):
            row, col = divmod(i, 2)
            cell = tk.Frame(grid, bg=PANEL)
            cell.grid(row=row, column=col, sticky="w", padx=4, pady=2)
            tk.Label(cell, text=T("pad_" + action), bg=PANEL, fg=MUTED, font=BODY_FONT, width=14,
                     anchor="w").pack(side="left")
            waiting = self.capturing == action
            tk.Label(cell, text=T("pad_press") if waiting else bindings.get(action) or "–", bg=PANEL,
                     fg=WARN if waiting else FG, font=("Bahnschrift SemiBold", 11), width=14 if waiting else 4,
                     anchor="w").pack(side="left")
            if connected and not waiting:
                _button(cell, T("pad_change"), lambda a=action: self.capture(a), bg=EDGE).pack(side="left")

    def reset_guide_position(self):
        self.app.reset_guide_position()
        self.show()

    def set_flip_side(self, value):
        self.app.set_option("flip_side", value)
        self.show()

    def capture(self, action, deadline=None, before=None):
        """Assigne a `action` le prochain bouton presse sur la manette (6 s pour appuyer ; Back : aucun)."""
        if deadline is None:
            self.capturing = action
            self.show()
            self.win.after(30, lambda: self.capture(action, time_now() + 6, self.app.pad.held()))
            return
        if self.capturing != action or not self.win.winfo_exists():
            return
        new = self.app.pad.held() - before
        if new or time_now() > deadline:
            if new:
                bindings = dict(self.app.store["pad"])
                pressed = sorted(new)[0]
                bindings[action] = "" if pressed == "Back" else pressed
                self.app.set_option("pad", bindings)
            self.capturing = None
            self.show()
            return
        self.win.after(30, lambda: self.capture(action, deadline, before & self.app.pad.held()))

    def set_target(self, spawn, delta):
        targets = dict(self.app.store["kick_targets"])
        targets[spawn] = round(min(3.5, max(1.5, targets[spawn] + delta)), 2)
        self.app.set_option("kick_targets", targets)
        self.show()

    def clear_drill(self):
        if messagebox.askyesno(T("dr_title"), T("dr_clear_confirm"), parent=self.win):
            self.app.set_option("drill", [])
            self.show()

