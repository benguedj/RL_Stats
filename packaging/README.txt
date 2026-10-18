RL Stats - automatic win / loss counter for Rocket League
===========================================================

The overlay shows your session wins, losses and win rate right above the boost
meter. It updates by itself at the end of every online match.

It uses Rocket League's official "Stats API" (provided by Psyonix for
overlays): nothing is injected into the game, no anti-cheat risk.


SETUP
-----
1. Put "RL Stats.exe" anywhere (Desktop, Documents...).
2. Double-click it.
   On first launch, Windows may show "Windows protected your PC": click
   "More info" then "Run anyway" (the program is not signed, this is normal).
3. Start Rocket League (or restart it if it was already running: the game only
   reads its config at startup). The overlay enables the Stats API by itself.
4. In the game's video settings, set the display mode to "Borderless"
   (in fullscreen, the overlay cannot be drawn over the game).

Once the "WAITING FOR GAME" banner disappears, the overlay is connected.


FEATURES
--------
- Per-mode counter: 1v1, 2v2, 3v3 and 4v4 are counted separately. The overlay
  shows the current mode (or all modes, your choice).
- Summary after each match: score, goals, assists, saves, shots, demos,
  shooting accuracy, fastest goal and MVP badge.
- History and progress: every game is saved. Daily win rate chart, best
  streak, MVPs, averages, CSV export.
- Players met before: the overlay tells you when you run into a player you
  already played with or against, with your record.
- Session goal: e.g. 10 wins, with progress shown.
- Win / loss animations and sounds (can be turned off).
- Customization: style, shape, size, colors, opacity.
- Multi-monitor and ultrawide: the overlay follows the game window on any
  screen. You can also pick the screen manually.
- Streamer mode: a page to add in OBS (browser source).
- Trophies and personal records (flip reset, aerial goal, hat trick...),
  announced on the overlay and listed in History > Trophies.
- Session card: right-click > "Copy session card", then Ctrl+V in Discord.
- Advanced stats (History > Analysis): kickoffs won, average boost, time at
  0 boost, supersonic time, goal map.
- Discord status: your mode, session score and streak on your Discord
  profile (Settings > Features, off by default).
- Tilt alert: break suggestion after 3 losses in a row or 2 h of play.
- Hides itself when the game is closed or minimized, resumes the session
  if restarted within 2 h, can start with Windows.
- Notifies you when a new version is available.
- English / French (follows the Windows language, can be changed).


USAGE
-----
- Menu: hover the overlay and click the menu button (three lines), or
  right-click the overlay: history, settings, appearance, score correction,
  reset session, quit.
- Mouse hover: +W / -W / +L / -L / menu / X buttons.
- Drag and drop to move it (position is remembered).
- Icon near the clock and taskbar button: click to hide / show the overlay;
  right-click the icon near the clock for the full menu. Windows 11 puts new
  icons behind the "^" arrow: drag it next to the clock to keep it visible.
- Ctrl+Shift+H: hide / show the overlay.
  Ctrl+Shift+R: reset the session.
  Ctrl+Shift+O: open the menu (in game, the mouse cursor is hidden).
  Launching RL Stats.exe again also shows the overlay if it was hidden.
- Right-click > "Players in this game (Tracker)": click a name to open their
  Tracker Network page (rank, MMR) in your browser.
- If results are reversed, right-click > "Set my in-game name..." and type
  your exact in-game name.

STREAMER MODE (OBS)
-------------------
Settings > "Streamer mode", then in OBS: Sources > + > Browser,
URL http://127.0.0.1:49124/ , width 600, height 260.

Only online matches are counted. Leaving a match early counts as a loss.
The game does not provide rank or MMR, so the overlay cannot show them.

Settings, history and log are stored in %APPDATA%\RL Stats
