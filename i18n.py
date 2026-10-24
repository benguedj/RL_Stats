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
    "met_title": ("DÉJÀ CROISÉS", "MET BEFORE"),
    "goal_me": ("BUT !", "GOAL!"),
    "goal_team": ("BUT DE {name} !", "{name} SCORES!"),
    "goal_us": ("BUT !", "GOAL!"),
    "goal_against": ("BUT ENCAISSÉ", "GOAL CONCEDED"),
    "all_modes": ("TOUS MODES", "ALL MODES"),

    "update_banner": ("MISE À JOUR {v} DISPONIBLE", "UPDATE {v} AVAILABLE"),
    "update_downloading": ("TÉLÉCHARGEMENT DE {v}…", "DOWNLOADING {v}…"),
    "update_failed": ("MISE À JOUR IMPOSSIBLE", "UPDATE FAILED"),
    "updated": ("MIS À JOUR EN {v}", "UPDATED TO {v}"),
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
    "dc_details": ("{mode}{w}W – {l}L ({p} %)", "{mode}{w}W – {l}L ({p}%)"),
    "dc_streak": ("Série de {n} victoires", "{n} win streak"),
    "dc_games": ("{n} matchs cette session", "{n} games this session"),
    "dc_waiting": ("Session en cours", "Session in progress"),
    "dc_button": ("Obtenir RL Stats", "Get RL Stats"),

    # Resume de match
    "sum_win": ("VICTOIRE", "VICTORY"),
    "sum_loss": ("DÉFAITE", "DEFEAT"),
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
    "m_met": ("déjà croisé {n}× : {w} W · {l} L", "met {n}×: {w} W · {l} L"),
    "m_blue": ("BLEU", "BLUE"),
    "m_orange": ("ORANGE", "ORANGE"),
    "m_history": ("Historique et progression…", "History and progress…"),
    "m_settings": ("Paramètres…", "Settings…"),
    "m_last_summary": ("Revoir le résumé du dernier match", "Show last match summary"),
    "m_share": ("Copier la carte de session (pour Discord…)", "Copy session card (for Discord…)"),
    "m_update": ("Mettre à jour vers {v}…", "Update to {v}…"),
    "m_reset": ("Réinitialiser la session", "Reset session"),
    "m_design": ("Design", "Style"),
    "m_shape": ("Forme", "Shape"),
    "m_size": ("Taille", "Size"),
    "m_hud_scale": ("Échelle de l'interface RL", "RL interface scale"),
    "m_preview": ("Aperçu", "Preview"),
    "m_victory": ("Victoire", "Victory"),
    "m_defeat": ("Défaite", "Defeat"),
    "m_goal_for": ("But marqué", "Goal scored"),
    "m_goal_against": ("But encaissé", "Goal conceded"),
    "m_summary_card": ("Carte de fin de match", "End of game card"),
    "m_met_preview": ("Adversaires déjà croisés", "Opponents met before"),
    "m_replace": ("Remettre à sa place", "Reset position"),
    "m_name": ("Définir mon pseudo…", "Set my in-game name…"),
    "m_hide": ("Masquer l'overlay", "Hide overlay"),
    "m_hide_key": ("Ctrl+Maj+H", "Ctrl+Shift+H"),
    "m_score": ("Corriger le score", "Fix the score"),
    "m_appearance": ("Apparence", "Appearance"),
    "m_copy_obs": ("Copier l'adresse OBS", "Copy OBS address"),
    "m_quit": ("Quitter", "Quit"),
    "style_tableau": ("Tableau des scores", "Scoreboard"),
    "style_minimal": ("Minimal", "Minimal"),
    "shape_arrondi": ("Arrondie (autour du boost)", "Curved (around boost)"),
    "shape_droit": ("Droite", "Straight"),
    "shape_vertical": ("Verticale (bord droit)", "Vertical (right edge)"),
    "name_title": ("Pseudo", "In-game name"),
    "name_prompt": ("Ton pseudo en jeu (laisser vide = détection automatique) :",
                    "Your in-game name (leave empty = automatic detection):"),
    "name_detected": ("Détecté automatiquement : {name}", "Detected automatically: {name}"),

    # Accueil (premier lancement)
    "welcome_title": ("Bienvenue dans RL Stats", "Welcome to RL Stats"),
    "welcome_heading": ("Un réglage avant de jouer", "One setting before you play"),
    "welcome_body": ("Dans Rocket League, va dans Paramètres > Vidéo et choisis le mode d'affichage "
                     "« Fenêtré sans bordure ».\n\n"
                     "En plein écran, Windows affiche le jeu par-dessus tout le reste : l'overlay "
                     "resterait en arrière-plan, invisible.",
                     "In Rocket League, go to Settings > Video and set the display mode to "
                     "\"Borderless\".\n\n"
                     "In fullscreen, Windows draws the game above everything else: the overlay "
                     "would stay in the background, invisible."),
    "welcome_ok": ("Compris", "Got it"),
    "welcome_ready_heading": ("Tout est prêt", "You're all set"),
    "welcome_ready_body": ("Rocket League est déjà dans un mode d'affichage compatible : l'overlay "
                           "s'affichera par-dessus le jeu.\n\n"
                           "Les paramètres vont s'ouvrir pour que tu choisisses ton style, tes couleurs "
                           "et tes alertes.",
                           "Rocket League already uses a compatible display mode: the overlay will show "
                           "over the game.\n\n"
                           "Settings will open next so you can pick your style, colors and alerts."),
    "fs_title": ("RL Stats - Plein écran", "RL Stats - Fullscreen"),
    "fs_heading": ("Rocket League est en plein écran", "Rocket League is in fullscreen"),

    # Parametres
    "s_title":("RL Stats - Paramètres", "RL Stats - Settings"),
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
    "s_animations": ("Animations (victoire, défaite, buts)", "Animations (win, loss, goals)"),
    "s_sounds": ("Sons (victoire, défaite, buts)", "Sounds (win, loss, goals)"),
    "s_volume": ("Volume", "Volume"),
    "s_sound_w": ("Son de victoire", "Victory sound"),
    "s_sound_l": ("Son de défaite", "Defeat sound"),
    "s_sound_gw": ("Son de but marqué", "Goal scored sound"),
    "s_sound_gl": ("Son de but encaissé", "Goal conceded sound"),
    "s_sound_default": ("par défaut", "default"),
    "s_sound_pick": ("Choisir…", "Choose…"),
    "s_sound_reset": ("Par défaut", "Default"),
    "s_sound_files": ("Sons (MP3, WAV)", "Sounds (MP3, WAV)"),
    "s_sound_failed": ("Ce fichier ne peut pas être lu", "This file can't be played"),
    "s_test": ("Tester", "Test"),
    "s_features": ("Fonctions", "Features"),
    "s_summary": ("Résumé après chaque match", "Summary after each match"),
    "s_summary_time": ("Durée du résumé (s)", "Summary duration (s)"),
    "s_met": ("Signaler les adversaires déjà croisés (pendant le match)",
              "Show opponents met before (during the game)"),
    "s_goal_alert": ("Alerte et animation à chaque but", "Alert and animation on every goal"),
    "s_session_timer": ("Chrono de session sur l'overlay", "Session timer on the overlay"),
    "s_obs": ("Mode streamer (source navigateur OBS)", "Streamer mode (OBS browser source)"),
    "s_obs_url": ("Adresse à ajouter dans OBS :", "Address to add in OBS:"),
    "s_obs_hint": ("OBS > Sources > + > Navigateur, largeur 600, hauteur 260",
                   "OBS > Sources > + > Browser, width 600, height 260"),
    "s_copy": ("Copier", "Copy"),
    "s_tray": ("Icône près de l'horloge (zone de notification)", "Icon near the clock (notification area)"),
    "s_taskbar": ("Bouton dans la barre des tâches", "Taskbar button"),
    "s_shell_hint": ("Clic : afficher / masquer l'overlay. Clic droit sur l'icône : menu.",
                     "Click: show / hide the overlay. Right-click the icon: menu."),
    "tray_tip": ("RL Stats – {w}W {l}L", "RL Stats – {w}W {l}L"),
    "s_hotkeys": ("Raccourcis clavier", "Keyboard shortcuts"),
    "s_hotkeys_desc": ("Ctrl+Maj+H : masquer / afficher    Ctrl+Maj+R : réinitialiser    Ctrl+Maj+O : menu",
                       "Ctrl+Shift+H: hide / show    Ctrl+Shift+R: reset    Ctrl+Shift+O: menu"),
    "s_close": ("Fermer", "Close"),
    "s_system": ("Système", "System"),
    "s_auto_hide": ("Masquer l'overlay quand le jeu est fermé ou réduit",
                    "Hide the overlay when the game is closed or minimized"),
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
    "h_wl": ("{w} W – {l} L", "{w} W – {l} L"),
    "h_best_streak": ("Meilleure série", "Best streak"),
    "h_mvp": ("MVP", "MVP"),
    "h_per_game": ("Par match", "Per game"),
    "h_per_game_val": ("{g} buts · {a} passes · {s} arrêts", "{g} goals · {a} assists · {s} saves"),
    "h_fastest": ("But le plus rapide", "Fastest goal"),
    "h_chart": ("Taux de victoire par jour", "Win rate per day"),
    "h_chart_tip": ("{day} : {p} % ({w} W – {l} L)", "{day}: {p}% ({w} W – {l} L)"),
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
    "h_analysis": ("Analyse", "Analysis"),
    "h_kickoffs": ("Engagements gagnés", "Kickoffs won"),
    "h_kickoffs_sub": ("{w} gagnés · {l} perdus · {n} neutres", "{w} won · {l} lost · {n} neutral"),
    "h_boost": ("Boost moyen", "Average boost"),
    "h_zero": ("Temps à 0 boost", "Time at 0 boost"),
    "h_superso": ("Temps en supersonique", "Supersonic time"),
    "h_goal_map": ("Où tes buts entrent dans la cage", "Where your goals go in"),
    "h_goal_map_sub": ("{n} buts, cage vue depuis le terrain", "{n} goals, goal seen from the field"),
    "h_no_adv": ("Pas encore de données : elles sont enregistrées à partir de la version 1.1.",
                 "No data yet: recorded starting with version 1.1."),
    "h_match_filter": ("Match", "Game"),
    "h_all_matches": ("Tous les matchs de la période", "All games in the period"),
    "h_share": ("Copier la carte de session", "Copy session card"),
    "h_mates": ("Coéquipiers", "Teammates"),
    "h_no_mates": ("Aucun coéquipier sur cette période", "No teammates in this period"),
    "h_best_mate": ("Meilleur duo", "Best duo"),
    "h_frequent_mate": ("Le plus fréquent", "Most frequent"),
    "h_your_avg": ("Ta moyenne", "Your average"),
    "h_mates_count": ("{n} coéquipiers croisés", "{n} teammates met"),
    "h_pct_games": ("{p} % · {n} matchs", "{p}% · {n} games"),
    "h_need_games": ("{n} matchs ensemble minimum", "{n} games together minimum"),
    "h_mates_hint": ("Écart : ton taux de victoire avec ce joueur, comparé à ta moyenne. "
                     "En gris : moins de {n} matchs ensemble. Double-clic : page Tracker.",
                     "Difference: your win rate with this player compared to your average. "
                     "Grey: fewer than {n} games together. Double-click: Tracker page."),
    "h_col_games": ("Matchs", "Games"),
    "h_col_record": ("Bilan", "Record"),
    "h_col_winrate": ("Victoires", "Win rate"),
    "h_col_diff": ("Écart", "Difference"),
    "h_hours": ("Horaires", "Time of day"),
    "h_best_slot": ("Meilleur créneau", "Best time slot"),
    "h_worst_slot": ("Créneau le moins bon", "Worst time slot"),
    "h_best_day": ("Meilleur jour", "Best day"),
    "h_slot": ("{a} h – {b} h", "{a}:00 – {b}:00"),
    "h_not_enough": ("Pas encore assez de matchs", "Not enough games yet"),
    "h_hours_hint": ("Selon l'heure de fin des matchs. En gris : moins de {n} matchs.",
                     "Based on when games ended. Grey: fewer than {n} games."),
    "h_by_hour": ("Taux de victoire selon l'heure", "Win rate by hour"),
    "h_by_day": ("Taux de victoire selon le jour", "Win rate by day of the week"),
    "h_hour": ("{h} h", "{h}:00"),
    "h_weekdays": ("Lundi,Mardi,Mercredi,Jeudi,Vendredi,Samedi,Dimanche",
                   "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday"),
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
