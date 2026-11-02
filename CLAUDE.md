# RL Stats

Overlay Windows pour Rocket League : compteur W / L automatique affiché près de la jauge de boost,
historique, analyses, source OBS. Python 3.12 + tkinter, fenêtres "layered" Win32 via ctypes,
rendu des images avec Pillow. Lit la **Stats API officielle** du jeu (socket TCP local, port 49123) :
rien n'est injecté dans le jeu.

Dépôt public : https://github.com/benguedj/RL_Stats (site : `docs/`, servi par GitHub Pages).

## Fichiers

| Fichier | Rôle |
|---|---|
| `rl_stats.pyw` | Point d'entrée et cœur : `APP_VERSION`, mise à jour auto, `Store` (config), `ApiListener` + `MatchTracker` (lecture des matchs), `Overlay` (fenêtre principale, menu, bandeaux) |
| `designs.py` | Dessin des 6 styles de l'overlay (scoreboard / minimal × courbe / droit / vertical) et des cartes |
| `ui_windows.py` | Fenêtres Historique, Paramètres, notices, accueil |
| `popup_menu.py` | Menu contextuel dessiné maison |
| `history.py` | `matches.json` : historique des matchs et agrégats |
| `i18n.py` | Tous les textes de l'interface : `TEXTS = {"cle": ("fr", "en")}`, lus avec `T("cle", n=3)` |
| `obs_server.py` | Page locale pour la source navigateur OBS (mode streamer) |
| `synth.py` | Sons générés |
| `tools/demo.py` | Démo scriptée (matchs simulés, données dans un dossier temporaire) pour les vidéos |
| `packaging/` | Notices du zip, package MSIX (Microsoft Store), manifestes winget |
| `docs/` | Site web (FR/EN), `privacy.html`, captures utilisées par le README |

Données utilisateur :
- depuis les sources : `stats.json`, `matches.json`, `overlay.log` à la racine du projet (ignorés par git) ;
- depuis l'exe : `%APPDATA%\RL Stats\`.

Ne jamais committer ni écraser ces fichiers : ce sont les vraies stats de l'utilisateur.

## Lancer et vérifier

- Lancer depuis les sources : `.venv\Scripts\pythonw.exe rl_stats.pyw` (ou `python` pour voir les erreurs).
- **Une seule instance** (verrou sur le port 49199) : si l'exe installé tourne déjà, lancer les
  sources ne fait que réafficher l'exe. Le fermer d'abord (icône de la barre des tâches > Quitter).
- Pas de suite de tests. Vérification minimale après une modif :
  `.venv\Scripts\python.exe -m py_compile rl_stats.pyw designs.py ui_windows.py popup_menu.py history.py i18n.py obs_server.py`
- Sans Rocket League, l'overlay reste sur "EN ATTENTE DU JEU". Pour voir des matchs simulés :
  `.venv\Scripts\python.exe tools\demo.py --short` (ne touche pas aux vraies données).
- Build local : `build.bat` → `dist\RL Stats.exe` et `dist\RL Stats.zip`.

## Conventions

- Code et commentaires en français **sans accents**. Les textes de l'interface (dans `i18n.py`) ont
  leurs accents.
- Tout texte visible passe par `i18n.py`, toujours en FR **et** EN.
- Victoires / défaites : toujours "W / L", jamais "V / D", même en français.
- Messages de commit en français sans accents. Une release : `vX.Y.Z : description courte`, puis un
  paragraphe d'explication si utile. Les autres commits : une phrase courte sans numéro de version.
- Une nouvelle fonction visible se documente dans le README (section anglaise **et** section
  "En français") et, si elle est importante, dans `docs/index.html` (FR et EN).
- Pas de nouvelle dépendance sans raison forte : l'exe doit rester petit (Pillow + winrt seulement).
- UPX reste désactivé dans `rl_stats.spec` (faux positifs antivirus).

## Release

Voir la skill `/release`. En résumé : `APP_VERSION` dans `rl_stats.pyw` est la seule source de la
version (le `.spec`, le MSIX et la CI la lisent). Commit, puis `git tag vX.Y.Z` et push du tag :
`.github/workflows/release.yml` construit l'exe, le zip, le MSIX, publie la release GitHub et
propose la version à winget. Le MSIX se télécharge dans l'onglet Actions et se soumet à la main
dans Partner Center.
