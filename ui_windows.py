"""Fenetres Parametres et Historique (Tkinter, theme sombre assorti a l'overlay)."""

import datetime
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

import achievements
from history import MODES, History
from i18n import T, lang
from obs_server import OBS_URL

BG = "#0b1322"
PANEL = "#141f36"
EDGE = "#344666"
FG = "#f1f5f9"
MUTED = "#8c98ad"
GRID = "#1e2a44"
TITLE_FONT = ("Bahnschrift SemiBold", 13)
BODY_FONT = ("Segoe UI", 10)
NUM_FONT = ("Bahnschrift SemiBold", 20)

COLOR_PRESETS = [("#2ee66b", "#ff4d4d"), ("#3b82f6", "#f97316"), ("#22d3ee", "#e879f9"), ("#facc15", "#a855f7")]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _dark_window(root, title, geometry):
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    win.geometry(geometry)
    win.attributes("-topmost", True)
    try:
        win.iconbitmap(root.iconbitmap())
    except tk.TclError:
        pass
    style = ttk.Style(win)
    style.theme_use("clam")
    style.configure("Dark.Horizontal.TScale", background=EDGE, troughcolor=BG, bordercolor=PANEL,
                    lightcolor=EDGE, darkcolor=EDGE, gripcount=0)
    style.map("Dark.Horizontal.TScale", background=[("active", MUTED)])
    style.configure("Dark.Vertical.TScrollbar", background=EDGE, troughcolor=BG, bordercolor=BG, arrowcolor=FG,
                    lightcolor=EDGE, darkcolor=EDGE, gripcount=0)
    style.map("Dark.Vertical.TScrollbar", background=[("active", MUTED)])
    style.configure("Dark.Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=24,
                    bordercolor=EDGE, lightcolor=PANEL, darkcolor=PANEL, borderwidth=0, font=BODY_FONT)
    style.configure("Dark.Treeview.Heading", background=BG, foreground=MUTED, bordercolor=EDGE, lightcolor=BG,
                    darkcolor=BG, relief="flat", font=("Bahnschrift SemiBold", 10))
    style.map("Dark.Treeview", background=[("selected", EDGE)])
    style.map("Dark.Treeview.Heading", background=[("active", PANEL)])
    # Barre de titre sombre (Windows 10 20H1+ / 11)
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError):
        pass
    return win


def _section(parent, text):
    tk.Label(parent, text=text.upper(), bg=BG, fg=MUTED, font=("Bahnschrift SemiBold", 10),
             anchor="w").pack(fill="x", padx=18, pady=(16, 4))
    frame = tk.Frame(parent, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
    frame.pack(fill="x", padx=14)
    return frame


def _row(frame, label):
    row = tk.Frame(frame, bg=PANEL)
    row.pack(fill="x", padx=12, pady=6)
    tk.Label(row, text=label, bg=PANEL, fg=FG, font=BODY_FONT, anchor="w").pack(side="left")
    return row


def _check(frame, label, var, command):
    return tk.Checkbutton(frame, text=label, variable=var, command=command, bg=PANEL, fg=FG, font=BODY_FONT,
                          selectcolor=BG, activebackground=PANEL, activeforeground=FG, anchor="w",
                          highlightthickness=0, bd=0)


def _button(parent, text, command, bg=EDGE):
    return tk.Button(parent, text=text, command=command, bg=bg, fg=FG, activebackground=PANEL, activeforeground=FG,
                     relief="flat", font=BODY_FONT, padx=10, pady=2, cursor="hand2")


def _slider(parent, var, lo, hi, command):
    """Curseur + valeur affichee a cote (le tk.Scale classique est illisible en theme sombre)."""
    value = tk.Label(parent, text=str(var.get()), bg=PANEL, fg=FG, font=BODY_FONT, width=4)

    def moved(v):
        var.set(round(float(v)))
        value.configure(text=str(var.get()))
        command()

    scale = ttk.Scale(parent, from_=lo, to=hi, orient="horizontal", length=200, value=var.get(), command=moved,
                      style="Dark.Horizontal.TScale")
    value.pack(side="right")
    scale.pack(side="right", padx=(0, 6))
    return scale


def _option(parent, var, choices, command):
    """Liste deroulante : choices = [(valeur, libelle)]."""
    labels = dict(choices)
    shown = tk.StringVar(value=labels.get(var.get(), choices[0][1]))

    def pick(value):
        var.set(value)
        shown.set(labels[value])
        command()

    menu_button = tk.Menubutton(parent, textvariable=shown, bg=EDGE, fg=FG, activebackground=PANEL,
                                activeforeground=FG, relief="flat", font=BODY_FONT, padx=10, indicatoron=True)
    menu = tk.Menu(menu_button, tearoff=0, bg=PANEL, fg=FG, activebackground=EDGE, activeforeground=FG)
    for value, label in choices:
        menu.add_command(label=label, command=lambda v=value: pick(v))
    menu_button["menu"] = menu
    return menu_button


# --------------------------------------------------------------------------
# Parametres
# --------------------------------------------------------------------------

class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.win = _dark_window(app.root, T("s_title"), "520x780")
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.build()

    def close(self):
        self.app.settings_window = None
        self.win.destroy()

    def rebuild(self):
        """Apres un changement de langue."""
        self.win.title(T("s_title"))
        for child in self.win.winfo_children():
            child.destroy()
        self.build()

    def var(self, key, kind=tk.StringVar):
        v = kind(value=self.app.store[key])
        self.vars[key] = v
        return v

    def changed(self, key):
        self.app.set_option(key, self.vars[key].get())

    def build(self):
        self.vars = {}
        store = self.app.store
        canvas = tk.Canvas(self.win, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self.win, orient="vertical", command=canvas.yview, style="Dark.Vertical.TScrollbar")
        body = tk.Frame(canvas, bg=BG)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        item = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.win.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-e.delta // 120, "units"))

        # --- General
        f = _section(body, T("s_general"))
        row = _row(f, T("s_language"))
        _option(row, self.var("lang"), [("auto", T("s_lang_auto")), ("fr", "Français"), ("en", "English")],
                lambda: self.changed("lang")).pack(side="right")

        row = _row(f, T("s_screen"))
        screens = [(0, T("s_screen_auto"))] + [
            (i + 1, T("s_screen_n", n=i + 1, w=m[2], h=m[3])) for i, m in enumerate(self.app.monitors())]
        _option(row, self.var("monitor", tk.IntVar), screens, lambda: self.changed("monitor")).pack(side="right")

        row = _row(f, T("s_counter"))
        _option(row, self.var("counter"), [("mode", T("s_counter_mode")), ("all", T("s_counter_all"))],
                lambda: self.changed("counter")).pack(side="right")

        row = _row(f, T("s_goal"))
        goal = self.var("goal", tk.IntVar)
        tk.Spinbox(row, from_=0, to=100, width=5, textvariable=goal, command=lambda: self.changed("goal"),
                   bg=BG, fg=FG, buttonbackground=EDGE, insertbackground=FG, relief="flat",
                   font=BODY_FONT).pack(side="right")
        goal.trace_add("write", lambda *a: self._safe_int("goal", 0, 100))

        # --- Apparence
        f = _section(body, T("s_look"))
        row = _row(f, T("s_colors"))
        swatches = tk.Frame(row, bg=PANEL)
        swatches.pack(side="right")
        for win_c, loss_c in COLOR_PRESETS:
            sw = tk.Canvas(swatches, width=38, height=20, bg=PANEL, highlightthickness=1,
                           highlightbackground=FG if (win_c, loss_c) == (store["win_color"], store["loss_color"])
                           else EDGE, cursor="hand2")
            sw.create_rectangle(0, 0, 19, 21, fill=win_c, width=0)
            sw.create_rectangle(19, 0, 39, 21, fill=loss_c, width=0)
            sw.bind("<Button-1>", lambda e, w=win_c, l=loss_c: self.set_colors(w, l))
            sw.pack(side="left", padx=2)
        row = tk.Frame(f, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(0, 6))
        _button(row, T("s_loss_color"), lambda: self.pick_color("loss_color")).pack(side="right", padx=(6, 0))
        _button(row, T("s_win_color"), lambda: self.pick_color("win_color")).pack(side="right")

        row = _row(f, T("s_opacity"))
        _slider(row, self.var("opacity", tk.IntVar), 40, 100, lambda: self.changed("opacity"))

        _check(f, T("s_animations"), self.var("animations", tk.BooleanVar),
               lambda: self.changed("animations")).pack(fill="x", padx=12, pady=6)
        _check(f, T("s_sounds"), self.var("sounds", tk.BooleanVar),
               lambda: self.changed("sounds")).pack(fill="x", padx=12, pady=6)
        row = _row(f, T("s_volume"))
        _button(row, T("s_test"), lambda: self.app.play_sound("w")).pack(side="right", padx=(8, 0))
        _slider(row, self.var("volume", tk.IntVar), 0, 100, lambda: self.changed("volume"))
        for kind in ("w", "l", "gw", "gl"):
            self.sound_row(f, kind)
        _check(f, T("s_session_timer"), self.var("session_timer", tk.BooleanVar),
               lambda: self.changed("session_timer")).pack(fill="x", padx=12, pady=6)

        # --- Fonctions
        f = _section(body, T("s_features"))
        _check(f, T("s_summary"), self.var("summary", tk.BooleanVar),
               lambda: self.changed("summary")).pack(fill="x", padx=12, pady=6)
        row = _row(f, T("s_summary_time"))
        tk.Spinbox(row, from_=4, to=60, width=5, textvariable=self.var("summary_time", tk.IntVar),
                   command=lambda: self.changed("summary_time"), bg=BG, fg=FG, buttonbackground=EDGE,
                   insertbackground=FG, relief="flat", font=BODY_FONT).pack(side="right")
        self.vars["summary_time"].trace_add("write", lambda *a: self._safe_int("summary_time", 4, 60))
        _check(f, T("s_met"), self.var("met_alert", tk.BooleanVar),
               lambda: self.changed("met_alert")).pack(fill="x", padx=12, pady=6)
        _check(f, T("s_goal_alert"), self.var("goal_alert", tk.BooleanVar),
               lambda: self.changed("goal_alert")).pack(fill="x", padx=12, pady=6)
        _check(f, T("s_tilt"), self.var("tilt_alert", tk.BooleanVar),
               lambda: self.changed("tilt_alert")).pack(fill="x", padx=12, pady=6)
        discord = _check(f, T("s_discord"), self.var("discord", tk.BooleanVar), lambda: self.changed("discord"))
        discord.pack(fill="x", padx=12, pady=(6, 2 if not self.app.discord_available else 6))
        if not self.app.discord_available:
            discord.configure(state="disabled", disabledforeground=MUTED)
            tk.Label(f, text=T("s_discord_na"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(
                fill="x", padx=30, pady=(0, 6))

        _check(f, T("s_obs"), self.var("obs", tk.BooleanVar),
               lambda: self.changed("obs")).pack(fill="x", padx=12, pady=(10, 2))
        row = tk.Frame(f, bg=PANEL)
        row.pack(fill="x", padx=30, pady=2)
        tk.Label(row, text=T("s_obs_url"), bg=PANEL, fg=MUTED, font=BODY_FONT).pack(side="left")
        url = tk.Entry(row, bg=BG, fg=FG, relief="flat", font=BODY_FONT, width=24, readonlybackground=BG)
        url.insert(0, OBS_URL)
        url.configure(state="readonly")
        url.pack(side="left", padx=6)
        _button(row, T("s_copy"), self.app.copy_obs_url).pack(side="left")
        tk.Label(f, text=T("s_obs_hint"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(
            fill="x", padx=30, pady=(0, 6))

        _check(f, T("s_tray"), self.var("tray", tk.BooleanVar),
               lambda: self.changed("tray")).pack(fill="x", padx=12, pady=(10, 2))
        _check(f, T("s_taskbar"), self.var("taskbar", tk.BooleanVar),
               lambda: self.changed("taskbar")).pack(fill="x", padx=12, pady=2)
        tk.Label(f, text=T("s_shell_hint"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(
            fill="x", padx=30, pady=(0, 6))

        _check(f, T("s_hotkeys"), self.var("hotkeys", tk.BooleanVar),
               lambda: self.changed("hotkeys")).pack(fill="x", padx=12, pady=(10, 2))
        tk.Label(f, text=T("s_hotkeys_desc"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(
            fill="x", padx=30, pady=(0, 8))

        # --- Systeme
        f = _section(body, T("s_system"))
        _check(f, T("s_auto_hide"), self.var("auto_hide", tk.BooleanVar),
               lambda: self.changed("auto_hide")).pack(fill="x", padx=12, pady=6)
        startup = tk.BooleanVar(value=self.app.startup_enabled())
        _check(f, T("s_startup"), startup,
               lambda: self.app.set_startup(startup.get())).pack(fill="x", padx=12, pady=6)
        _check(f, T("s_resume"), self.var("resume_session", tk.BooleanVar),
               lambda: self.changed("resume_session")).pack(fill="x", padx=12, pady=6)
        _check(f, T("s_updates"), self.var("check_updates", tk.BooleanVar),
               lambda: self.changed("check_updates")).pack(fill="x", padx=12, pady=6)
        tk.Label(f, text=T("s_version", v=self.app.version), bg=PANEL, fg=MUTED, font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", padx=12, pady=(0, 8))

        _button(body, T("s_close"), self.close).pack(pady=16)

    def sound_row(self, frame, kind):
        """Son de victoire / defaite : fichier choisi (MP3, WAV) ou son par defaut."""
        row = _row(frame, T("s_sound_" + kind))
        custom = self.app.store["custom_sounds"].get(kind)
        _button(row, "▶", lambda: self.app.play_sound(kind)).pack(side="right", padx=(6, 0))
        if custom:
            _button(row, T("s_sound_reset"), lambda: self.set_sound(kind, None)).pack(side="right", padx=(6, 0))
        _button(row, T("s_sound_pick"), lambda: self.pick_sound(kind)).pack(side="right", padx=(6, 0))
        if not custom:
            tk.Label(row, text=T("s_sound_default"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")
            return
        name = custom["name"]
        tk.Label(frame, text="♪ " + (name if len(name) <= 60 else name[:59] + "…"), bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=30, pady=(0, 4))

    def pick_sound(self, kind):
        path = filedialog.askopenfilename(parent=self.win, title=T("s_sound_" + kind),
                                          filetypes=[(T("s_sound_files"), "*.mp3 *.wav")])
        if path:
            self.set_sound(kind, path)

    def set_sound(self, kind, path):
        ok = self.app.set_custom_sound(kind, path)
        self.rebuild()
        if not ok:
            messagebox.showwarning(T("s_sound_" + kind), T("s_sound_failed"), parent=self.win)

    def _safe_int(self, key, lo, hi):
        try:
            value = int(self.vars[key].get())
        except (tk.TclError, ValueError):
            return
        if lo <= value <= hi and value != self.app.store[key]:
            self.app.set_option(key, value)

    def set_colors(self, win_c, loss_c):
        self.app.set_option("win_color", win_c)
        self.app.set_option("loss_color", loss_c)
        self.rebuild()

    def pick_color(self, key):
        _, hex_color = colorchooser.askcolor(self.app.store[key], parent=self.win,
                                             title=T("s_win_color" if key == "win_color" else "s_loss_color"))
        if hex_color:
            self.app.set_option(key, hex_color)
            self.rebuild()


# --------------------------------------------------------------------------
# Historique
# --------------------------------------------------------------------------

class HistoryWindow:
    def __init__(self, app):
        self.app = app
        self.history: History = app.history
        self.period = "7d"
        self.mode = None
        self.tab = "overview"
        self.analysis_match = None  # "t" du match choisi dans l'onglet Analyse (None = tous)
        self.win = _dark_window(app.root, T("h_title"), "860x640")
        self.win.minsize(720, 520)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.build()

    def close(self):
        self.app.history_window = None
        self.win.destroy()

    def refresh(self):
        """Appele apres chaque match pour mettre la fenetre a jour."""
        self.show()

    def _segmented(self, parent, options, current, command):
        bar = tk.Frame(parent, bg=BG)
        for value, label in options:
            active = value == current
            tk.Button(bar, text=label, command=lambda v=value: command(v), relief="flat", cursor="hand2",
                      bg=EDGE if active else PANEL, fg=FG if active else MUTED, activebackground=EDGE,
                      activeforeground=FG, font=("Bahnschrift SemiBold", 10), padx=10, pady=3, bd=0).pack(
                side="left", padx=(0, 2))
        return bar

    def build(self):
        for child in self.win.winfo_children():
            child.destroy()
        top = tk.Frame(self.win, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 6))
        self._segmented(top, [("overview", T("h_overview")), ("matches", T("h_matches_tab")),
                              ("players", T("h_players")), ("trophies", T("h_trophies")),
                              ("analysis", T("h_analysis"))], self.tab, self.set_tab).pack(side="left")
        _button(top, T("h_export"), self.export, bg=PANEL).pack(side="right")
        _button(top, T("h_share"), self.app.share_card, bg=PANEL).pack(side="right", padx=(0, 6))

        filters = tk.Frame(self.win, bg=BG)
        filters.pack(fill="x", padx=16, pady=(0, 8))
        self._segmented(filters, [("today", T("h_today")), ("7d", T("h_7d")), ("30d", T("h_30d")),
                                  ("all", T("h_all"))], self.period, self.set_period).pack(side="left")
        self._segmented(filters, [(None, T("h_all_modes"))] + [(m, m) for m in MODES], self.mode,
                        self.set_mode).pack(side="right")

        self.content = tk.Frame(self.win, bg=BG)
        self.content.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.show()

    def set_tab(self, tab):
        self.tab = tab
        self.build()

    def set_period(self, period):
        self.period = period
        self.build()

    def set_mode(self, mode):
        self.mode = mode
        self.build()

    def show(self):
        for child in self.content.winfo_children():
            child.destroy()
        matches = self.history.filter(self.period, self.mode)
        {"overview": self.show_overview, "matches": self.show_matches, "players": self.show_players,
         "trophies": self.show_trophies, "analysis": self.show_analysis}[self.tab](matches)

    # --- Progression --------------------------------------------------------

    def show_overview(self, matches):
        if not matches:
            tk.Label(self.content, text=T("h_no_data"), bg=BG, fg=MUTED, font=TITLE_FONT).pack(expand=True)
            return
        s = History.summary(matches)
        tiles = tk.Frame(self.content, bg=BG)
        tiles.pack(fill="x")
        fastest = f"{round(s['fastest'])} km/h" if s["fastest"] else "–"
        for title, value, sub in (
                (T("h_games"), str(s["n"]), T("h_wl", w=s["w"], l=s["l"])),
                (T("h_winrate"), f"{s['pct']} %", ""),
                (T("h_best_streak"), str(s["best_streak"]), ""),
                (T("h_mvp"), str(s["mvp"]), ""),
                (T("h_fastest"), fastest, ""),
        ):
            tile = tk.Frame(tiles, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
            tile.pack(side="left", fill="both", expand=True, padx=(0, 6))
            tk.Label(tile, text=title, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=10,
                                                                                                  pady=(8, 0))
            tk.Label(tile, text=value, bg=PANEL, fg=FG, font=NUM_FONT, anchor="w").pack(fill="x", padx=10)
            tk.Label(tile, text=sub, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=10,
                                                                                                pady=(0, 8))
        per_game = T("h_per_game_val", g=f"{s['goals']:.1f}", a=f"{s['assists']:.1f}", s=f"{s['saves']:.1f}")
        tk.Label(self.content, text=f"{T('h_per_game')} : {per_game}" if lang() == "fr"
                 else f"{T('h_per_game')}: {per_game}", bg=BG, fg=MUTED, font=BODY_FONT, anchor="w").pack(
            fill="x", pady=(8, 0))

        tk.Label(self.content, text=T("h_chart"), bg=BG, fg=FG, font=TITLE_FONT, anchor="w").pack(fill="x",
                                                                                                 pady=(14, 4))
        chart = tk.Canvas(self.content, bg=PANEL, highlightthickness=1, highlightbackground=EDGE)
        chart.pack(fill="both", expand=True)
        days = History.per_day(matches, self.period)
        chart.bind("<Configure>", lambda e: self.draw_chart(chart, days))

    def draw_chart(self, c, days):
        """Barres divergentes autour de 50 % : au-dessus = plus de victoires que de defaites."""
        c.delete("all")
        W, H = c.winfo_width(), c.winfo_height()
        left, right, top, bottom = 44, 14, 14, 26
        pw, ph = W - left - right, H - top - bottom
        if pw < 50 or ph < 50 or not days:
            return
        win_c, loss_c = self.app.store["win_color"], self.app.store["loss_color"]

        def y_of(pct):
            return top + ph * (1 - pct / 100)

        for pct in (0, 25, 50, 75, 100):  # grille discrete, 50 % un peu plus marque
            y = y_of(pct)
            c.create_line(left, y, W - right, y, fill=EDGE if pct == 50 else GRID, width=1)
            c.create_text(left - 8, y, text=f"{pct}%", fill=MUTED, anchor="e", font=("Segoe UI", 8))

        n = len(days)
        slot = pw / n
        bar_w = max(2, min(28, slot - 2))  # 2 px d'ecart entre les barres
        base = y_of(50)
        self.chart_hits = []
        for i, (day, w, l) in enumerate(days):
            x = left + slot * i + (slot - bar_w) / 2
            if w + l:
                pct = w * 100 / (w + l)
                y = y_of(pct)
                if abs(y - base) < 2:  # 50 % pile : petit trait neutre
                    c.create_rectangle(x, base - 1, x + bar_w, base + 1, fill=MUTED, width=0)
                else:
                    c.create_rectangle(x, min(y, base), x + bar_w, max(y, base),
                                       fill=win_c if pct > 50 else loss_c, width=0)
                self.chart_hits.append((left + slot * i, left + slot * (i + 1), day, w, l))
            if n <= 10 or i in (0, n // 2, n - 1):
                c.create_text(x + bar_w / 2, H - bottom + 12, text=self._day_label(day), fill=MUTED,
                              font=("Segoe UI", 8))

        tip = c.create_text(0, 0, text="", fill=FG, font=("Segoe UI", 9), anchor="sw", state="hidden")
        tip_bg = c.create_rectangle(0, 0, 0, 0, fill=BG, outline=EDGE, state="hidden")
        cross = c.create_line(0, top, 0, top + ph, fill=EDGE, state="hidden")

        def hover(e):
            for x0, x1, day, w, l in self.chart_hits:
                if x0 <= e.x < x1:
                    c.itemconfigure(tip, text=T("h_chart_tip", day=self._day_label(day, long=True),
                                                p=round(w * 100 / (w + l)), w=w, l=l), state="normal")
                    c.coords(cross, (x0 + x1) / 2, top, (x0 + x1) / 2, top + ph)
                    c.itemconfigure(cross, state="normal")
                    c.tag_lower(cross)
                    bx = min(max(e.x + 10, left), W - 10 - (c.bbox(tip)[2] - c.bbox(tip)[0]))
                    c.coords(tip, bx, max(top + 22, e.y - 8))
                    x_0, y_0, x_1, y_1 = c.bbox(tip)
                    c.coords(tip_bg, x_0 - 6, y_0 - 4, x_1 + 6, y_1 + 4)
                    c.itemconfigure(tip_bg, state="normal")
                    c.tag_raise(tip_bg)
                    c.tag_raise(tip)
                    return
            leave()

        def leave(e=None):
            for item in (tip, tip_bg, cross):
                c.itemconfigure(item, state="hidden")

        c.bind("<Motion>", hover)
        c.bind("<Leave>", leave)

    @staticmethod
    def _day_label(day, long=False):
        if long:
            return day.strftime("%d/%m/%Y") if lang() == "fr" else day.strftime("%b %d, %Y")
        return day.strftime("%d/%m") if lang() == "fr" else day.strftime("%m/%d")

    # --- Liste des matchs ---------------------------------------------------

    def _tree(self, columns, widths):
        frame = tk.Frame(self.content, bg=BG)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=[c for c, _ in columns], show="headings", style="Dark.Treeview")
        for (col, label), width in zip(columns, widths):
            tree.heading(col, text=label)
            tree.column(col, width=width, anchor="w" if col in ("player", "date") else "center")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview, style="Dark.Vertical.TScrollbar")
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tree.tag_configure("w", foreground=self.app.store["win_color"])
        tree.tag_configure("l", foreground=self.app.store["loss_color"])
        return tree

    def show_matches(self, matches):
        tree = self._tree([("date", T("h_col_date")), ("mode", T("h_col_mode")), ("result", T("h_col_result")),
                           ("score", T("h_col_score")), ("stats", T("h_col_stats"))], (170, 70, 110, 90, 200))
        fmt = "%d/%m/%Y %H:%M" if lang() == "fr" else "%Y-%m-%d %H:%M"
        for m in reversed(matches):
            me = m.get("me") or {}
            score = m.get("score") or [None, None]
            tree.insert("", "end", tags=("w" if m["won"] else "l",), values=(
                datetime.datetime.fromtimestamp(m["t"]).strftime(fmt), m.get("mode", "?"),
                T("h_won" if m["won"] else "h_lost"),
                f"{score[0]} – {score[1]}" if None not in score else "–",
                f"{me.get('goals', 0)} / {me.get('assists', 0)} / {me.get('saves', 0)}" if me else "–"))

    # --- Joueurs croises ----------------------------------------------------

    def show_players(self, matches):
        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(0, 6))
        tk.Label(bar, text=T("h_search"), bg=BG, fg=MUTED, font=BODY_FONT).pack(side="left")
        query = tk.StringVar()
        tk.Entry(bar, textvariable=query, bg=PANEL, fg=FG, insertbackground=FG, relief="flat",
                 font=BODY_FONT, width=28).pack(side="left", padx=8)
        tk.Label(bar, text=T("h_players_hint"), bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")
        tree = self._tree([("player", T("h_col_player")), ("with", T("h_col_with")),
                           ("against", T("h_col_against")), ("last", T("h_col_last"))], (260, 130, 130, 130))
        players = History.players_of(matches)
        ranked = sorted(players.items(), key=lambda kv: (-kv[1]["n"], -kv[1]["last"]))
        fmt = "%d/%m/%Y" if lang() == "fr" else "%Y-%m-%d"
        wl = "{}V {}D" if lang() == "fr" else "{}W {}L"

        def fill(*_):
            q = query.get().strip().lower()
            tree.delete(*tree.get_children())
            for pid, p in ranked:
                if q and q not in p["name"].lower():
                    continue
                tree.insert("", "end", iid=pid, values=(
                    p["name"], wl.format(*p["with"]) if sum(p["with"]) else "–",
                    wl.format(*p["against"]) if sum(p["against"]) else "–",
                    datetime.datetime.fromtimestamp(p["last"]).strftime(fmt)))

        query.trace_add("write", fill)
        fill()
        tree.bind("<Double-1>", lambda e: tree.focus() and self.app.open_player(tree.focus(),
                                                                                 players[tree.focus()]["name"]))

    # --- Trophees et records ------------------------------------------------

    def show_trophies(self, _matches):
        matches = self.history.matches  # toujours sur tout l'historique
        got = self.app.store["achievements"]
        t = achievements.totals(matches)
        fr = lang() == "fr"
        tk.Label(self.content, text=T("h_unlocked", n=len(got), t=len(achievements.ACHIEVEMENTS)), bg=BG, fg=MUTED,
                 font=BODY_FONT, anchor="w").pack(fill="x", pady=(0, 6))
        body = tk.Frame(self.content, bg=BG)
        body.pack(fill="both", expand=True)
        grid = tk.Frame(body, bg=BG)
        grid.pack(side="left", fill="both", expand=True)
        gold = "#facc15"
        cols = 3
        for i, entry in enumerate(achievements.ACHIEVEMENTS):
            done = entry[0] in got
            value, goal = achievements.progress(entry, t)
            tile = tk.Frame(grid, bg=PANEL, highlightbackground=gold if done else EDGE, highlightthickness=1)
            tile.grid(row=i // cols, column=i % cols, sticky="nsew", padx=(0, 5), pady=(0, 5))
            badge = tk.Canvas(tile, width=26, height=26, bg=PANEL, highlightthickness=0)
            badge.create_oval(3, 3, 23, 23, fill=gold if done else BG, outline=gold if done else EDGE, width=2)
            badge.create_text(13, 13, text="★" if done else "", fill=BG, font=("Segoe UI", 9, "bold"))
            badge.pack(side="left", padx=(8, 6), pady=6)
            text = tk.Frame(tile, bg=PANEL)
            text.pack(side="left", fill="x", pady=4)
            tk.Label(text, text=achievements.label(entry, lang()), bg=PANEL, fg=FG if done else MUTED,
                     font=("Segoe UI", 9, "bold" if done else "normal"), anchor="w").pack(fill="x")
            if done:
                sub = datetime.datetime.fromtimestamp(got[entry[0]]).strftime("%d/%m/%Y" if fr else "%Y-%m-%d")
            else:
                sub = f"{min(round(value), goal)} / {goal}"
            tk.Label(text, text=sub, bg=PANEL, fg=MUTED, font=("Segoe UI", 8), anchor="w").pack(fill="x")
        for c in range(cols):
            grid.columnconfigure(c, weight=1)

        side = tk.Frame(body, bg=PANEL, highlightbackground=EDGE, highlightthickness=1, width=230)
        side.pack(side="right", fill="y", padx=(8, 0))
        side.pack_propagate(False)
        tk.Label(side, text=T("h_records"), bg=PANEL, fg=FG, font=TITLE_FONT, anchor="w").pack(fill="x", padx=12,
                                                                                            pady=(10, 6))
        recs = achievements.records(matches)
        for rid, _, _, fmt in achievements.RECORDS:
            entry = next(r for r in achievements.RECORDS if r[0] == rid)
            row = tk.Frame(side, bg=PANEL)
            row.pack(fill="x", padx=12, pady=4)
            tk.Label(row, text=achievements.label(entry, lang()), bg=PANEL, fg=MUTED, font=("Segoe UI", 9),
                     anchor="w").pack(fill="x")
            value = fmt.format(recs[rid][0]) if rid in recs else "–"
            tk.Label(row, text=value, bg=PANEL, fg=FG, font=("Bahnschrift SemiBold", 16), anchor="w").pack(fill="x")

    # --- Analyse (engagements, boost, carte des buts) -----------------------

    def _match_label(self, m):
        fmt = "%d/%m %H:%M" if lang() == "fr" else "%m/%d %H:%M"
        score = m.get("score") or [None, None]
        result = T("h_won" if m["won"] else "h_lost")
        if None not in score:
            result += f" {score[0]}–{score[1]}"
        return f"{datetime.datetime.fromtimestamp(m['t']).strftime(fmt)}  ·  {m.get('mode', '?')}  ·  {result}"

    def _match_filter(self, matches):
        """Liste deroulante : tous les matchs de la periode ou un seul. Renvoie les matchs a analyser."""
        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        tk.Label(bar, text=T("h_match_filter"), bg=BG, fg=MUTED, font=BODY_FONT).pack(side="left", padx=(0, 8))
        recent = list(reversed(matches))[:100]
        choices = [("", T("h_all_matches"))] + [(str(m["t"]), self._match_label(m)) for m in recent]
        picked = next((m for m in recent if str(m["t"]) == self.analysis_match), None)
        var = tk.StringVar(value=str(picked["t"]) if picked else "")

        def pick():
            self.analysis_match = var.get() or None
            self.show()

        _option(bar, var, choices, pick).pack(side="left")
        return [picked] if picked else matches

    def show_analysis(self, matches):
        matches = self._match_filter(matches)
        mes = [m.get("me") or {} for m in matches]
        kick = [sum(me.get("kickoffs", [0, 0, 0])[i] for me in mes) for i in range(3)]
        boosts = [me["boost"] for me in mes if me.get("boost")]
        zeros = [b for b in boosts if "n" in b]  # avant la version 1.4.0, le temps a 0 boost valait toujours 0
        spots = [s for me in mes for s in me.get("goal_spots", [])]
        if not (sum(kick) or boosts or spots):
            tk.Label(self.content, text=T("h_no_adv"), bg=BG, fg=MUTED, font=BODY_FONT).pack(expand=True)
            return
        tiles = tk.Frame(self.content, bg=BG)
        tiles.pack(fill="x")

        def avg(key, items=None):
            items = boosts if items is None else items
            return sum(b[key] for b in items) / len(items) if items else None

        decided = kick[0] + kick[1]
        for title, value, sub in (
                (T("h_kickoffs"), f"{round(kick[0] * 100 / decided)} %" if decided else "–",
                 T("h_kickoffs_sub", w=kick[0], l=kick[1], n=kick[2])),
                (T("h_boost"), f"{avg('avg'):.0f}" if boosts else "–", ""),
                (T("h_zero"), f"{avg('zero', zeros):.0f} %" if zeros else "–", ""),
                (T("h_superso"), f"{avg('superso'):.0f} %" if boosts else "–", ""),
        ):
            tile = tk.Frame(tiles, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
            tile.pack(side="left", fill="both", expand=True, padx=(0, 6))
            tk.Label(tile, text=title, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=10,
                                                                                                  pady=(8, 0))
            tk.Label(tile, text=value, bg=PANEL, fg=FG, font=NUM_FONT, anchor="w").pack(fill="x", padx=10)
            tk.Label(tile, text=sub, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=10,
                                                                                                pady=(0, 8))
        tk.Label(self.content, text=T("h_goal_map"), bg=BG, fg=FG, font=TITLE_FONT, anchor="w").pack(fill="x",
                                                                                                    pady=(14, 0))
        tk.Label(self.content, text=T("h_goal_map_sub", n=len(spots)), bg=BG, fg=MUTED, font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", pady=(0, 4))
        canvas = tk.Canvas(self.content, bg=PANEL, highlightthickness=1, highlightbackground=EDGE)
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", lambda e: self.draw_goal_map(canvas, spots))

    def draw_goal_map(self, c, spots):
        """Cage de face (largeur 1786, hauteur 642 unites du jeu) et points d'entree des buts."""
        c.delete("all")
        W, H = c.winfo_width(), c.winfo_height()
        half_w, height = 893, 642
        scale = min((W - 60) / (2 * half_w), (H - 40) / height)
        gw, gh = 2 * half_w * scale, height * scale
        x0, y1 = (W - gw) / 2, (H + gh) / 2
        y0 = y1 - gh
        for i in range(1, 8):  # filet
            c.create_line(x0 + gw * i / 8, y0, x0 + gw * i / 8, y1, fill=GRID)
        for i in range(1, 4):
            c.create_line(x0, y0 + gh * i / 4, x0 + gw, y0 + gh * i / 4, fill=GRID)
        c.create_line(x0, y1, x0, y0, x0 + gw, y0, x0 + gw, y1, fill=FG, width=4)  # poteaux et barre
        c.create_line(x0 - 20, y1, x0 + gw + 20, y1, fill=EDGE, width=2)  # ligne de but
        color = self.app.store["win_color"]
        r = max(4, scale * 28)
        for x, z in spots:
            px = x0 + (min(max(x, -half_w), half_w) + half_w) * scale
            py = y1 - min(max(z, 0), height) * scale
            c.create_oval(px - r, py - r, px + r, py + r, fill=color, outline=PANEL, width=2)

    def export(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".csv", initialfile="rl_stats.csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            self.history.export_csv(path)
