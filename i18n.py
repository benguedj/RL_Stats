"""Textes de l'interface en francais et en anglais.

T("cle") renvoie le texte dans la langue active ; T("cle", n=3) le formate.
La langue "auto" suit la langue d'affichage de Windows (francais sinon anglais).
"""

import ctypes

TEXTS = {
    # Overlay
    "win_banner": ("VICTOIRE !", "VICTORY!"),
    "loss_banner": ("DÉFAITE", "DEFEAT"),
    "waiting": ("EN ATTENTE DU JEU", "WAITING FOR GAME"),
    "restart_rl": ("RELANCE ROCKET LEAGUE", "RESTART ROCKET LEAGUE"),
    "streak_w": ("SÉRIE {n} VICTOIRES", "{n} WIN STREAK"),
    "streak_l": ("SÉRIE {n} DÉFAITES", "{n} LOSS STREAK"),
    "matches": ("{n} MATCH", "{n} GAME"),
    "matches_pl": ("{n} MATCHS", "{n} GAMES"),
    "goal_progress": ("OBJECTIF {w}/{goal}", "GOAL {w}/{goal}"),
    "goal_reached": ("OBJECTIF ATTEINT !", "GOAL REACHED!"),
    "met_before": ("DÉJÀ CROISÉ : {name} ({w}V {l}D)", "MET BEFORE: {name} ({w}W {l}L)"),
    "all_modes": ("TOUS MODES", "ALL MODES"),

    "update_banner": ("MISE À JOUR {v} DISPONIBLE", "UPDATE {v} AVAILABLE"),
    "trophy_banner": ("TROPHÉE : {name}", "TROPHY: {name}"),
    "trophy_more": ("+{n} AUTRES TROPHÉES DÉBLOQUÉS", "+{n} MORE TROPHIES UNLOCKED"),
    "record_banner":("RECORD : {name} ({v})", "RECORD: {name} ({v})"),
    "tilt_losses": ("{n} DÉFAITES – PETITE PAUSE ?", "{n} LOSSES – TAKE A BREAK?"),
    "tilt_time": ("{h} H DE JEU – PENSE À UNE PAUSE", "{h} H PLAYED – TIME FOR A BREAK?"),
    "card_copied": ("CARTE COPIÉE !", "CARD COPIED!"),

    # Carte de session
    "card_session": ("SESSION", "SESSION"),
    "card_winrate": ("DE VICTOIRES", "WIN RATE"),
    "card_streak": ("MEILLEURE SÉRIE", "BEST STREAK"),
    "card_fastest": ("BUT MAX (KM/H)", "TOP GOAL (KM/H)"),
    "card_footer": ("{min} MIN DE JEU  ·  GITHUB.COM/BENGUEDJ/RL_STATS",
                    "{min} MIN PLAYED  ·  GITHUB.COM/BENGUEDJ/RL_STATS"),

    # Statut Discord
    "dc_details": ("{mode}{w}V – {l}D ({p} %)", "{mode}{w}W – {l}L ({p}%)"),
    "dc_streak": ("Série de {n} victoires", "{n} win streak"),
    "dc_games": ("{n} matchs cette session", "{n} games this session"),
    "dc_waiting": ("Session en cours", "Session in progress"),
    "dc_button": ("Obtenir RL Stats", "Get RL Stats"),

    # Resume de match
    "sum_win": ("VICTOIRE", "VICTORY"),
    "sum_loss": ("DÉFAITE", "DEFEAT"),
    "sum_forfeit": ("ABANDON", "FORFEIT"),
    "sum_goals": ("BUTS", "GOALS"),
    "sum_assists": ("PASSES D.", "ASSISTS"),
    "sum_saves": ("ARRÊTS", "SAVES"),
    "sum_shots": ("TIRS", "SHOTS"),
    "sum_demos": ("DÉMOS", "DEMOS"),
    "sum_score": ("SCORE", "SCORE"),
    "sum_accuracy": ("PRÉCISION {p} %", "ACCURACY {p}%"),
    "sum_fastest": ("BUT LE PLUS RAPIDE {v} KM/H", "FASTEST GOAL {v} KM/H"),
    "sum_mvp": ("MVP", "MVP"),

    # Menu
    "m_players": ("Joueurs de la partie (Tracker)", "Players in this game (Tracker)"),
    "m_no_game": ("Aucune partie en ligne pour l'instant", "No online game yet"),
    "m_you": ("(toi)", "(you)"),
    "m_bot": ("(bot / indisponible)", "(bot / unavailable)"),
    "m_met": ("déjà croisé {n}× : {w}V {l}D", "met {n}×: {w}W {l}L"),
    "m_blue": ("BLEU", "BLUE"),
    "m_orange": ("ORANGE", "ORANGE"),
    "m_history": ("Historique et progression…", "History and progress…"),
    "m_settings": ("Paramètres…", "Settings…"),
    "m_last_summary": ("Revoir le résumé du dernier match", "Show last match summary"),
    "m_share": ("Copier la carte de session (pour Discord…)", "Copy session card (for Discord…)"),
    "m_update": ("⬆ Mettre à jour vers {v}…", "⬆ Update to {v}…"),
    "m_reset": ("Réinitialiser la session", "Reset session"),
    "m_win_plus": ("+1 victoire", "+1 win"),
    "m_win_minus": ("-1 victoire", "-1 win"),
    "m_loss_plus": ("+1 défaite", "+1 loss"),
    "m_loss_minus": ("-1 défaite", "-1 loss"),
    "m_design": ("Design", "Style"),
    "m_shape": ("Forme", "Shape"),
    "m_size": ("Taille", "Size"),
    "m_preview": ("Aperçu de l'animation", "Animation preview"),
    "m_victory": ("Victoire", "Victory"),
    "m_defeat": ("Défaite", "Defeat"),
    "m_replace": ("Replacer au-dessus du boost", "Move back above boost"),
    "m_name": ("Définir mon pseudo…", "Set my in-game name…"),
    "m_hide": ("Masquer l'overlay   (Ctrl+Maj+H)", "Hide overlay   (Ctrl+Shift+H)"),
    "m_copy_obs": ("Copier l'adresse OBS", "Copy OBS address"),
    "m_quit": ("Quitter", "Quit"),
    "style_tableau": ("Tableau des scores", "Scoreboard"),
    "style_minimal": ("Minimal", "Minimal"),
    "shape_arrondi": ("Arrondie (autour du boost)", "Curved (around boost)"),
    "shape_droit": ("Droite", "Straight"),
    "name_title": ("Pseudo", "In-game name"),
    "name_prompt": ("Ton pseudo en jeu (laisser vide = détection automatique) :",
                    "Your in-game name (leave empty = automatic detection):"),
    "name_detected": ("Détecté automatiquement : {name}", "Detected automatically: {name}"),

    # Parametres
    "s_title": ("RL Stats - Paramètres", "RL Stats - Settings"),
    "s_general": ("Général", "General"),
    "s_language": ("Langue", "Language"),
    "s_lang_auto": ("Automatique (Windows)", "Automatic (Windows)"),
    "s_screen": ("Écran", "Screen"),
    "s_screen_auto": ("Automatique (écran du jeu)", "Automatic (game screen)"),
    "s_screen_n": ("Écran {n} – {w}×{h}", "Screen {n} – {w}×{h}"),
    "s_counter": ("Compteur affiché", "Counter shown"),
    "s_counter_mode": ("Mode en cours (1v1, 2v2…)", "Current mode (1v1, 2v2…)"),
    "s_counter_all": ("Tous les modes", "All modes"),
    "s_goal": ("Objectif de victoires (0 = aucun)", "Win goal (0 = none)"),
    "s_look": ("Apparence", "Appearance"),
    "s_colors": ("Couleurs victoire / défaite", "Win / loss colors"),
    "s_custom": ("Personnalisé…", "Custom…"),
    "s_win_color": ("Couleur des victoires", "Win color"),
    "s_loss_color": ("Couleur des défaites", "Loss color"),
    "s_opacity": ("Opacité", "Opacity"),
    "s_animations": ("Animations de victoire / défaite", "Win / loss animations"),
    "s_sounds": ("Sons de victoire / défaite", "Win / loss sounds"),
    "s_volume": ("Volume", "Volume"),
    "s_test": ("Tester", "Test"),
    "s_features": ("Fonctions", "Features"),
    "s_summary": ("Résumé après chaque match", "Summary after each match"),
    "s_summary_time": ("Durée du résumé (s)", "Summary duration (s)"),
    "s_met": ("Signaler les joueurs déjà croisés", "Show players met before"),
    "s_obs": ("Mode streamer (source navigateur OBS)", "Streamer mode (OBS browser source)"),
    "s_obs_url": ("Adresse à ajouter dans OBS :", "Address to add in OBS:"),
    "s_obs_hint": ("OBS > Sources > + > Navigateur, largeur 600, hauteur 260",
                   "OBS > Sources > + > Browser, width 600, height 260"),
    "s_copy": ("Copier", "Copy"),
    "s_tray": ("Icône près de l'horloge (zone de notification)", "Icon near the clock (notification area)"),
    "s_taskbar": ("Bouton dans la barre des tâches", "Taskbar button"),
    "s_shell_hint": ("Clic : afficher / masquer l'overlay. Clic droit sur l'icône : menu.",
                     "Click: show / hide the overlay. Right-click the icon: menu."),
    "tray_tip": ("RL Stats – {w}V {l}D", "RL Stats – {w}W {l}L"),
    "s_hotkeys": ("Raccourcis clavier", "Keyboard shortcuts"),
    "s_hotkeys_desc": ("Ctrl+Maj+H : masquer / afficher    Ctrl+Maj+R : réinitialiser la session",
                       "Ctrl+Shift+H: hide / show    Ctrl+Shift+R: reset session"),
    "s_close": ("Fermer", "Close"),
    "s_system": ("Système", "System"),
    "s_auto_hide": ("Masquer l'overlay quand le jeu n'est pas au premier plan",
                    "Hide the overlay when the game is not in focus"),
    "s_startup": ("Démarrer avec Windows (discret jusqu'au lancement du jeu)",
                  "Start with Windows (stays hidden until the game starts)"),
    "s_resume": ("Reprendre la session si l'app est relancée dans les 2 h",
                 "Resume the session if restarted within 2 h"),
    "s_updates": ("Vérifier les mises à jour au démarrage", "Check for updates at startup"),
    "s_version": ("Version {v}", "Version {v}"),
    "s_tilt": ("Alerte tilt : pause conseillée (3 défaites d'affilée, 2 h de jeu)",
               "Tilt alert: break suggestion (3 losses in a row, 2 h played)"),
    "s_discord": ("Statut Discord (Rich Presence)", "Discord status (Rich Presence)"),
    "s_discord_na": ("Indisponible : aucun identifiant d'application Discord dans cette version",
                     "Unavailable: no Discord application ID in this build"),

    # Historique
    "h_title": ("RL Stats - Historique", "RL Stats - History"),
    "h_overview": ("Progression", "Progress"),
    "h_players": ("Joueurs croisés", "Players met"),
    "h_matches_tab": ("Matchs", "Games"),
    "h_today": ("Aujourd'hui", "Today"),
    "h_7d": ("7 jours", "7 days"),
    "h_30d": ("30 jours", "30 days"),
    "h_all": ("Tout", "All time"),
    "h_all_modes": ("Tous les modes", "All modes"),
    "h_games": ("Matchs", "Games"),
    "h_winrate": ("Victoires", "Win rate"),
    "h_wl": ("{w} V – {l} D", "{w} W – {l} L"),
    "h_best_streak": ("Meilleure série", "Best streak"),
    "h_mvp": ("MVP", "MVP"),
    "h_per_game": ("Par match", "Per game"),
    "h_per_game_val": ("{g} buts · {a} passes · {s} arrêts", "{g} goals · {a} assists · {s} saves"),
    "h_fastest": ("But le plus rapide", "Fastest goal"),
    "h_chart": ("Taux de victoire par jour", "Win rate per day"),
    "h_chart_tip": ("{day} : {p} % ({w} V – {l} D)", "{day}: {p}% ({w} W – {l} L)"),
    "h_no_data": ("Aucun match sur cette période", "No games in this period"),
    "h_search": ("Rechercher", "Search"),
    "h_col_player": ("Joueur", "Player"),
    "h_col_with": ("Avec toi", "With you"),
    "h_col_against": ("Contre toi", "Against you"),
    "h_col_last": ("Dernier match", "Last game"),
    "h_col_date": ("Date", "Date"),
    "h_col_mode": ("Mode", "Mode"),
    "h_col_result": ("Résultat", "Result"),
    "h_col_score": ("Score", "Score"),
    "h_col_stats": ("Buts / Passes / Arrêts", "Goals / Assists / Saves"),
    "h_players_hint": ("Double-clic : ouvrir la page Tracker", "Double-click: open Tracker page"),
    "h_export": ("Exporter en CSV…", "Export to CSV…"),
    "h_trophies": ("Trophées", "Trophies"),
    "h_analysis": ("Analyse", "Analysis"),
    "h_records": ("Records", "Records"),
    "h_unlocked": ("{n} / {t} trophées débloqués (sur tout l'historique)",
                   "{n} / {t} trophies unlocked (whole history)"),
    "h_kickoffs": ("Engagements gagnés", "Kickoffs won"),
    "h_kickoffs_sub": ("{w} gagnés · {l} perdus · {n} neutres", "{w} won · {l} lost · {n} neutral"),
    "h_boost": ("Boost moyen", "Average boost"),
    "h_zero": ("Temps à 0 boost", "Time at 0 boost"),
    "h_superso": ("Temps en supersonique", "Supersonic time"),
    "h_goal_map": ("Où tes buts entrent dans la cage", "Where your goals go in"),
    "h_goal_map_sub": ("{n} buts, cage vue depuis le terrain", "{n} goals, goal seen from the field"),
    "h_no_adv": ("Pas encore de données : elles sont enregistrées à partir de la version 1.1.",
                 "No data yet: recorded starting with version 1.1."),
    "h_share": ("Copier la carte de session", "Copy session card"),
    "h_won": ("Victoire", "Win"),
    "h_lost": ("Défaite", "Loss"),
}

_lang = "fr"


def system_lang():
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "fr" if lang_id & 0x3FF == 0x0C else "en"  # LANG_FRENCH = 0x0C
    except (AttributeError, OSError):
        return "en"


def set_lang(choice):
    global _lang
    _lang = system_lang() if choice not in ("fr", "en") else choice


def lang():
    return _lang


def T(key, **kw):
    fr, en = TEXTS[key]
    text = fr if _lang == "fr" else en
    return text.format(**kw) if kw else text


def matches_label(n):
    return T("matches_pl" if n > 1 else "matches", n=n)
