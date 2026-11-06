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

    # Entrainement
    "m_training": ("Entraînement (bêta)", "Training (beta)"),
    "kick_pill_me": ("TOI", "YOU"),
    "kick_pill_mate": ("COÉQUIPIER", "TEAMMATE"),
    "kick_pill_opp": ("ADVERSAIRE", "OPPONENT"),
    "tr_title": ("RL Stats - Entraînement (bêta)", "RL Stats - Training (beta)"),
    "tr_beta": ("BÊTA · en cours de test, tes retours sont les bienvenus", "BETA · still being tested, feedback welcome"),
    "tr_kickoffs": ("Engagements", "Kickoffs"),
    "tr_mechanics": ("Mécaniques", "Mechanics"),
    "tr_alert": ("Afficher une petite carte après chaque engagement en match",
                 "Show a small card after each kickoff in a match"),
    "tr_how": ("Discrète, à côté de l'overlay pendant 4 s, à chaque engagement : le temps entre le GO et le "
               "premier contact de celui qui touche en premier (toi, un coéquipier ou l'adversaire), sa position "
               "et sa couleur (parfait, bon, presque, lent) d'après les mêmes temps de référence qu'en "
               "entraînement (le chrono est recalé sur le vrai départ, signalé un peu en retard en ligne). L'angle et le cancel de ton flip si une manette est branchée. "
               "La position de l'adversaire est celle de ton équipe : les positions de départ sont symétriques, "
               "et celui qui y va (le plus proche du ballon, celui de gauche en cas d'égalité) est le joueur de "
               "ton équipe qui a le plus roulé au moment du contact. En ligne et hors ligne, pas en entraînement libre (pas de coup d'envoi).",
               "Discreet, next to the overlay for 4 s, at each kickoff: the time between GO and the first touch "
               "of whoever touches first (you, a teammate or the opponent), their position and color (perfect, "
               "good, close, slow) from the same reference times as in training (the timer is set back to the real start, "
               "reported slightly late online). "
               "The angle and cancel of your flip when a controller is plugged in. The opponent's position is "
               "your team's: spawns are symmetric, and the one who goes (closest to the ball, the left one on a "
               "tie) is the player of your team who drove the farthest by the time of the touch. Online and offline, not in free play "
               "(no kickoff)."),
    "tr_col_time": ("Heure", "Time"),
    "tr_col_dt": ("Temps", "Time to ball"),
    "tr_col_result": ("Résultat", "Result"),
    "tr_videos": ("Tutos vidéo", "Video tutorials"),
    "tr_levels": ("Débutant,Intermédiaire,Avancé,Expert", "Beginner,Intermediate,Advanced,Expert"),
    "tr_status": ("À travailler,En cours,Maîtrisé", "To learn,Working on it,Mastered"),
    "tr_diag": ("Diagonale", "Diagonal"),
    "tr_offc": ("Décalée", "Off-center"),
    "tr_back": ("Centre", "Back center"),
    "tr_ball": ("Ballon", "Ball"),
    "tr_boost": ("Gros boost", "Big boost"),
    "drill_hit": ("{spawn} · {s} · {d}", "{spawn} · {s} · {d}"),
    "gap_perfect": ("parfait !", "perfect!"),
    "gap_to_perfect": ("à {d} du parfait", "{d} from perfect"),
    "gap_to_good": ("{d} au-dessus du vert", "{d} above green"),
    "drill_miss": ("PAS TOUCHÉ · {s} · TEMPS DU PACK ÉCOULÉ", "MISSED · {s} · PACK TIME RAN OUT"),
    "gap_miss": ("temps du pack écoulé", "pack time ran out"),
    "dr_title": ("Engagement rapide (fast kickoff)", "Fast kickoff"),
    "dr_intro": ("Touche le ballon le plus vite possible depuis chaque position de départ, en entraînement "
                 "personnalisé ou hors ligne. Tous tes essais sont enregistrés.",
                 "Touch the ball as fast as you can from each spawn, in custom training or offline. "
                 "All your attempts are saved."),
    "dr_tile_sub": ("{ok} sur {n} en vert ou en or · parfaits : {p} · record {best}",
                    "{ok} of {n} green or gold · perfect: {p} · record {best}"),
    "dr_record_card": ("Record -{d}", "Record -{d}"),
    "dr_record_banner": ("NOUVEAU RECORD ({d} de mieux)", "NEW RECORD ({d} better)"),
    "dr_perfect": ("Parfait", "Perfect"),
    "dr_missed": ("Pas touchés", "Missed"),
    "dr_missed_sub": ("temps du tir écoulé avant le contact", "shot time ran out before contact"),
    "dr_pack": ("Pack d'engagements conseillé", "Recommended kickoff pack"),
    "dr_pack_copy": ("Copier le code", "Copy the code"),
    "dr_pack_copied": ("Copié !", "Copied!"),
    "dr_pack_hint": ("Dans le jeu : Entraînement > Entraînement personnalisé > Code, puis colle le code (Ctrl + V). "
                     "Le guide du speed flip s'affiche tout seul pendant les engagements.",
                     "In the game: Training > Custom training > Code, then paste the code (Ctrl + V). The speed "
                     "flip guide shows up on its own during kickoffs."),
    "dr_levels": ("Couleurs de tes temps", "Your time colors"),
    "dr_levels_hint": ("Vert : ton speed flip égale ou bat un bon engagement en flip diagonal classique (1,95 / 2,25 / "
                       "2,55 s). Or : speed flip parfait, calculé avec la physique du jeu. Mêmes temps en match : le jeu y signale le départ environ 0,06 s "
                       "après le vrai GO, le chrono est donc recalé sur le vrai départ des voitures.",
                       "Green: your speed flip matches or beats a good classic diagonal flip kickoff (1.95 / 2.25 / 2.55 s). "
                       "Gold: perfect speed flip, computed with the game physics. Same times in a match: the game reports the start about 0.06 s after the "
                       "real GO there, so the timer is set back to when the cars really start."),
    "dr_attempts": ("Derniers essais", "Latest attempts"),
    "dr_none": ("Aucun essai pour l'instant : lance un pack d'engagements en entraînement personnalisé.",
                "No attempts yet: load a kickoff pack in custom training."),
    "dr_col_spawn": ("Position", "Spawn"),
    "dr_col_diff": ("vs parfait", "vs perfect"),
    "dr_good": ("Bon", "Good"),
    "dr_close": ("Presque", "Close"),
    "dr_slow": ("Lent", "Slow"),
    "dr_miss": ("Pas touché", "Missed"),
    "dr_clear": ("Effacer les essais", "Clear attempts"),
    "dr_clear_confirm": ("Effacer tous les essais du défi ? Tes records sont gardés.",
                         "Clear all challenge attempts? Your records are kept."),
    "pf_last": ("Dernier speed flip", "Latest speed flip"),
    "pf_none": ("Fais un essai avec la manette pour voir l'analyse de ton speed flip : moment du saut, angle "
                "du flip, délai du cancel, air roll et boost.",
                "Do an attempt with your controller to see your speed flip analysis: jump timing, flip angle, "
                "cancel delay, air roll and boost."),
    "pf_jump": ("1er saut", "1st jump"),
    "pf_flip": ("Délai flip", "Flip delay"),
    "pf_angle": ("Angle", "Angle"),
    "pf_cancel": ("Cancel", "Cancel"),
    "pf_roll": ("Air roll", "Air roll"),
    "pf_boost": ("Boost", "Boost"),
    "pf_left": ("G", "L"),
    "pf_right": ("D", "R"),
    "pf_yes": ("Oui", "Yes"),
    "pf_no_flip": ("Pas de flip détecté : saute, puis flip en diagonale",
                   "No flip detected: jump, then flip diagonally"),
    "pf_straight": ("Flip trop droit : pousse le stick plus en diagonale",
                    "Flip too straight: push the stick more diagonally"),
    "pf_wide": ("Flip trop large : pousse le stick moins sur le côté", "Flip too wide: push the stick less sideways"),
    "pf_no_cancel": ("Pas de cancel : tire le stick vers l'arrière juste après le flip",
                     "No cancel: pull the stick back right after the flip"),
    "pf_slow_cancel": ("Cancel trop lent : tire le stick vers l'arrière plus tôt",
                       "Cancel too slow: pull the stick back sooner"),
    "pf_more_boost": ("Garde le boost appuyé jusqu'au contact", "Keep boosting until you touch the ball"),
    "pf_good": ("Bon speed flip !", "Good speed flip!"),
    "pf_tap": ("Décalage", "Offset"),
    "pf_no_tap": ("Pas de décalage du stick au 1er saut : décale-le un peu vers 35°, du côté opposé au flip",
                  "No stick offset at the 1st jump: shift it a little toward 35°, opposite your flip"),
    "pf_tap_side": ("Coup de stick du même côté que le flip : il doit partir de l'autre côté",
                    "Stick tap on the same side as the flip: it must go the other way"),
    "pf_tap_hard": ("Décalage trop fort : pas besoin d'aller à fond, vise juste « 1 h » (35°)",
                    "Offset too strong: no need to go all the way, just aim at \"1 o'clock\" (35°)"),
    "pf_tap_timing": ("Stick plus décalé au 1er saut : il doit encore l'être au moment du saut",
                      "Stick no longer offset at the 1st jump: it must still be offset as you jump"),
    "pf_jump_early": ("1er saut trop tôt : attends environ 0,5 s après le départ",
                      "1st jump too early: wait about 0.5 s after the start"),
    "pf_jump_late": ("1er saut trop tard : saute environ 0,5 s après le départ",
                     "1st jump too late: jump about 0.5 s after the start"),
    "pf_no_roll": ("Pas d'air roll pendant le flip : maintiens l'air roll {side}",
                   "No air roll during the flip: hold air roll {side}"),
    "pf_roll_side": ("Air roll du mauvais côté : prends l'air roll {side}, du côté du flip",
                     "Air roll on the wrong side: use air roll {side}, the flip side"),
    "pf_check_buttons": ("Boost jamais détecté : vérifie tes boutons (Entraînement > Engagement rapide)",
                         "Boost never seen: check your buttons (Training > Fast kickoff)"),
    "pf_left_full": ("gauche", "left"),
    "pf_right_full": ("droite", "right"),
    "pf_advice": ("À travailler", "Work on"),
    "tl_side": ("Stick G / D", "Stick L / R"),
    "tl_front": ("Stick av. / arr.", "Stick fwd / back"),
    "tl_jump": ("Saut", "Jump"),
    "tl_roll": ("Air roll", "Air roll"),
    "tl_boost": ("Boost", "Boost"),
    "rp_title": ("Ton geste au ralenti, à côté du geste parfait", "Your motion in slow motion, next to the perfect "
                 "motion"),
    "rp_speed": ("Vitesse", "Speed"),
    "rp_ref_title": ("Le geste parfait au ralenti", "The perfect motion in slow motion"),
    "rp_ref_hint": ("Stick gauche vu de face (haut = avant) et boutons allumés quand ils sont enfoncés, sur les "
                    "timings du speed flip enregistré de SpeedFlipTrainer.",
                    "Left stick seen from the front (up = forward) and buttons lit while pressed, on the timings "
                    "of the speed flip recorded by SpeedFlipTrainer."),
    "tl_ref_title": ("Inputs du geste parfait, du départ au cancel", "Inputs of the perfect motion, from the start "
                     "to the cancel"),
    "tl_legend": ("En couleur : ton essai. En pointillés clairs : le geste parfait, sur le même temps depuis le "
                  "départ. Ton input après le pointillé : tu es en retard ; avant : en avance.",
                  "In color: your attempt. Light dotted: the perfect motion, on the same time since the start. "
                  "Your input after the dotted one: you are late; before it: early."),
    "rp_you": ("Toi", "You"),
    "rp_ref": ("Geste parfait", "Perfect motion"),
    "rp_clock": ("1er saut {t}", "1st jump {t}"),
    "rp_hint": ("Les deux sticks sont calés sur ton premier saut : compare où ils sont au même moment. Zone grisée : "
                "angle du flip conseillé. Trait gris : tout le geste ; trait bleu : déjà fait.",
                "Both sticks are lined up on the first jump: compare where they are at the same moment. Grey area: "
                "recommended flip angle. Grey line: the whole motion; blue line: done so far."),
    "tl_title": ("Tes inputs, du départ au cancel", "Your inputs, from the start to the cancel"),
    "pf_best": ("Tes {n} essais les plus rapides : flip à {a}° en moyenne, cancel en {c} ms, 1er saut à {j}.",
                "Your {n} fastest attempts: {a}° flip on average, {c} ms cancel, 1st jump at {j}."),
    "pf_note": ("Repères du plugin SpeedFlipTrainer : 1er saut entre 0,46 et 0,58 s ; flip à 30° (vert de 22 à "
                "38°, zones grisées) ; cancel en 60 ms au plus (orange jusqu'à 90 ms). Son speed flip de référence : "
                "stick sur le côté 25 ms avant le saut, flip 92 ms après, cancel 42 ms après, air roll du côté du flip "
                "33 ms après. Compare-toi surtout à tes essais les plus rapides.",
                "SpeedFlipTrainer plugin benchmarks: 1st jump between 0.46 and 0.58 s; 30° flip (green from 22 to "
                "38°, grey areas); cancel within 60 ms (orange up to 90 ms). Its reference speed flip: sideways stick "
                "25 ms before the jump, flip 92 ms later, cancel 42 ms later, air roll on the flip side 33 ms "
                "later. Compare yourself mostly with your fastest attempts."),
    "pad_ok": ("Manette détectée", "Controller detected"),
    "pad_missing": ("Aucune manette détectée : l'analyse du speed flip a besoin d'une manette Xbox (ou reconnue "
                    "comme telle, par exemple via Steam Input).",
                    "No controller detected: the speed flip analysis needs an Xbox controller (or one seen as "
                    "such, for example through Steam Input)."),
    "pad_hint": ("L'analyse utilise les mêmes boutons que dans le jeu (Paramètres > Commandes). Seuls les inputs "
                 "de chaque essai sont analysés.",
                 "The analysis uses the same buttons as in the game (Settings > Controls). Only the inputs of each "
                 "attempt are analyzed."),
    "pad_jump": ("Saut", "Jump"),
    "pad_boost": ("Boost", "Boost"),
    "pad_roll": ("Air roll", "Air roll"),
    "pad_roll_l": ("Air roll gauche", "Air roll left"),
    "pad_roll_r": ("Air roll droite", "Air roll right"),
    "pad_change": ("Changer", "Change"),
    "pad_reset": ("Réinitialiser les boutons", "Reset buttons"),
    "pad_press": ("Appuie sur un bouton…", "Press a button…"),
    "pad_setup_title": ("Indique tes boutons avant de t'entraîner", "Set your buttons before you practice"),
    "pad_setup_text": ("L'analyse du speed flip lit ta manette : elle doit savoir sur quels boutons tu as mis le "
                       "saut, le boost et l'air roll dans le jeu (Paramètres > Commandes). Sans ça, le boost et "
                       "l'air roll de tes essais ne sont pas mesurés.",
                       "The speed flip analysis reads your controller: it needs to know which buttons you use in "
                       "the game for jump, boost and air roll (Settings > Controls). Without that, the boost and "
                       "air roll of your attempts are not measured."),
    "pad_setup_start": ("Régler mes boutons", "Set my buttons"),
    "pad_setup_step": ("{i}/{n} · Appuie sur ton bouton : {action}",
                       "{i}/{n} · Press your button: {action}"),
    "pad_title": ("Boutons de la manette", "Controller buttons"),
    "pad_ok_button": ("OK", "OK"),
    "pad_open": ("Boutons de la manette…", "Controller buttons…"),
    "m_pad": ("Boutons de la manette…", "Controller buttons…"),
    "s_pad": ("Boutons de la manette", "Controller buttons"),
    "s_pad_button": ("Régler…", "Set…"),
    "s_pad_hint": ("Pour l'analyse du speed flip (Entraînement) : les mêmes boutons que dans le jeu.",
                   "For the speed flip analysis (Training): the same buttons as in the game."),
    "pad_setup_done": ("C'est réglé !", "All set!"),
    "pad_setup_skip": ("Back / View si tu ne l'utilises pas. Sans appui pendant 8 s, le bouton actuel est gardé.",
                       "Back / View if you don't use it. With no press for 8 s, the current button is kept."),
    "sg_auto_option": ("Afficher le guide tout seul en entraînement personnalisé d'engagements",
                       "Show the guide automatically in kickoff custom training"),
    "sg_auto_on": ("ENTRAÎNEMENT D'ENGAGEMENTS · GUIDE AFFICHÉ", "KICKOFF TRAINING · GUIDE ON"),
    "pf_flip_label": ("FLIP", "FLIP"),
    "sg_title": ("GUIDE SPEED FLIP", "SPEED FLIP GUIDE"),
    "sg_tap": ("BOOST + PETIT DÉCALAGE", "BOOST + SMALL OFFSET"),
    "sg_jump": ("SAUTE VERS 0,5 S", "JUMP AT ABOUT 0.5 S"),
    "sg_tap_label": ("PETIT DÉCALAGE", "SMALL OFFSET"),
    "sg_jump_bar": ("1ER SAUT : SAUTE DANS LE VERT", "1ST JUMP: JUMP IN THE GREEN"),
    "sg_flip": ("TOURNE + FLIP EN DIAGONALE", "SWEEP + FLIP DIAGONALLY"),
    "sg_cancel": ("CONTINUE VERS L'ARRIÈRE", "KEEP GOING BACK"),
    "sg_hold": ("GARDE + AIR ROLL", "HOLD + AIR ROLL"),
    "sg_option": ("Guide du stick sur l'overlay", "Stick guide on the overlay"),
    "sg_on": ("GUIDE DU STICK AFFICHÉ", "STICK GUIDE ON"),
    "sg_off": ("GUIDE DU STICK MASQUÉ", "STICK GUIDE OFF"),
    "sg_no_pad": ("GUIDE ACTIVÉ · AUCUNE MANETTE", "GUIDE ON · NO CONTROLLER"),
    "m_guide": ("Guide du speed flip", "Speed flip guide"),
    "sg_side": ("Côté du flip", "Flip side"),
    "sg_reset_pos": ("Remettre à droite", "Move back to the right"),
    "sg_move_hint": ("Fais glisser le guide à la souris pour le placer où tu veux, comme l'overlay.",
                     "Drag the guide with the mouse to place it anywhere, like the overlay."),
    "sg_auto": ("Auto", "Auto"),
    "sg_left": ("Gauche", "Left"),
    "sg_right": ("Droite", "Right"),
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
