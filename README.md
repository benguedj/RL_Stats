# RL Overlay

**Automatic win / loss tracker for Rocket League**, displayed right around your boost meter.
Session stats per mode, post-match summary, history and progress charts, OBS browser source.

![Overlay styles](docs/designs.png)

It uses Rocket League's **official Stats API** (the local socket Psyonix provides for overlays):
nothing is injected into the game and nothing touches the anti-cheat. Everything stays on your PC.

> 🇫🇷 [Version française plus bas](#-en-français)

---

## Download

👉 **[Download the latest version](https://github.com/benguedj/rl-overlay/releases/latest)** (`RL Overlay.zip`, Windows 10/11)

1. Unzip and double-click **`RL Overlay.exe`** (no install needed).
   Windows SmartScreen may say *"Windows protected your PC"*: click **More info → Run anyway**
   (the exe is not code-signed).
2. Start Rocket League, or **restart** it if it was already running (the game only reads its
   config at startup). The overlay enables the Stats API by itself.
3. In the game video settings, use **Borderless** display mode (an overlay can't be drawn over
   exclusive fullscreen).

Once the *"WAITING FOR GAME"* banner disappears, you're connected.

## Features

| | |
|---|---|
| **Automatic W/L counter** | Updates at the end of every online match. Leaving a match counts as a loss. |
| **Per-mode stats** | 1v1, 2v2, 3v3 and 4v4 are counted separately; the overlay shows the current mode (or all modes). |
| **Post-match summary** | Score, goals, assists, saves, shots, demos, accuracy, fastest goal, MVP badge. |
| **History & progress** | Every game is saved: daily win-rate chart, best streak, MVPs, averages, game list, CSV export. |
| **Players met before** | Warns you when you meet a player you already played with or against, with your record. |
| **Session goal** | e.g. *10 wins tonight*, with progress shown on the overlay. |
| **Animations & sounds** | Confetti on wins, shake on losses, optional sounds. |
| **Customization** | 4 styles (scoreboard / minimal × curved / straight), size, colors, opacity. |
| **Multi-monitor & ultrawide** | Follows the game window on any screen, any resolution, windowed or borderless. |
| **Streamer mode** | A local page to add as an **OBS browser source**. Off by default. |
| **Tray icon & taskbar button** | Click to hide / show the overlay, right-click for the menu. |
| **English / French** | Follows the Windows language, can be changed in Settings. |

![Victory animation and match summary](docs/victory.png)

| History | Settings |
|---|---|
| ![History window](docs/history.png) | ![Settings window](docs/settings.png) |

## Usage

- **Right-click the overlay** (or the tray icon): history, settings, style, players in the game, score correction, quit.
- **Hover** the overlay: `+W` `-W` `+L` `-L` `X` buttons.
- **Drag** it to move it (the position is remembered per style).
- **Shortcuts**: `Ctrl+Shift+H` hide / show, `Ctrl+Shift+R` reset session.
- **Players in this game (Tracker)**: click a name to open their Tracker Network profile (rank, MMR).
- If wins and losses are swapped: right-click → *Set my in-game name…*

### Streamer mode (OBS)

Settings → *Streamer mode*, then in OBS: **Sources → + → Browser**, URL `http://127.0.0.1:49124/`,
width 600, height 260. The server only listens on `127.0.0.1` (not reachable from the network).

## FAQ

**Can I get banned?** The overlay only reads the official Stats API, a feature Psyonix added for
overlays and tournament tools. It does not read game memory, inject code or modify game files
(it only sets `PacketSendRate` in your user config `TAStatsAPI.ini`).

**Why no rank / MMR?** The game doesn't send them through the Stats API. Use the Tracker links
in the players menu.

**Are offline / private matches counted?** Only online matches are counted.

**Where is my data?** In `%APPDATA%\RL Overlay` (settings, match history, log). Nothing is sent
anywhere.

**My antivirus flags the exe.** Executables made with PyInstaller are sometimes flagged by mistake.
The full source is here: you can read it and [build the exe yourself](#build-from-source).

## Build from source

Requirements: Windows 10/11, Python 3.10+.

```bat
git clone https://github.com/benguedj/rl-overlay.git
cd rl-overlay
pip install -r requirements.txt
pythonw rl_overlay.pyw
```

Build the standalone exe (`dist\RL Overlay.exe` + `dist\RL Overlay.zip`):

```bat
build.bat
```

### Project structure

| File | Role |
|---|---|
| `rl_overlay.pyw` | Entry point: Stats API connection, match tracking, overlay window, tray icon, hotkeys |
| `designs.py` | Overlay styles, animations and match summary card, drawn with Pillow |
| `history.py` | Match history (`matches.json`) and statistics |
| `ui_windows.py` | Settings and History windows (Tkinter) |
| `obs_server.py` | Local page for OBS (streamer mode) |
| `i18n.py` | English / French texts |
| `rl_overlay.spec`, `build.bat` | PyInstaller build |
| `packaging/` | Readme files shipped in the zip |

## License

[MIT](LICENSE) © benguedj

*RL Overlay is a fan-made project, not affiliated with or endorsed by Psyonix or Epic Games.
Rocket League is a trademark of Psyonix LLC.*

---

## 🇫🇷 En français

**Compteur automatique de victoires / défaites pour Rocket League**, affiché autour de la jauge de boost.

👉 **[Télécharger la dernière version](https://github.com/benguedj/rl-overlay/releases/latest)**, puis :

1. Dézippe et lance **`RL Overlay.exe`**. Si Windows affiche *« Windows a protégé votre ordinateur »* :
   **Informations complémentaires → Exécuter quand même** (l'exe n'est pas signé).
2. Lance Rocket League (ou **relance-le** s'il était ouvert). L'overlay active la Stats API tout seul.
3. Dans les options vidéo du jeu, choisis **Fenêtré sans bordure**.

**Fonctionnalités** : compteur par mode (1v1, 2v2, 3v3, 4v4), résumé après chaque match, historique
et graphique de progression, joueurs déjà croisés, objectif de session, animations et sons,
personnalisation (designs, couleurs, opacité), multi-écrans et ultra-larges, mode streamer (OBS),
icône près de l'horloge, français / anglais.

**Utilisation** : clic droit sur l'overlay (ou sur l'icône près de l'horloge) pour le menu,
glisser pour le déplacer, `Ctrl+Maj+H` pour le masquer, `Ctrl+Maj+R` pour réinitialiser la session.

Utilise la **Stats API officielle** de Rocket League : rien n'est injecté dans le jeu, aucun risque
avec l'anti-cheat. Les données restent sur ton PC (`%APPDATA%\RL Overlay`).
