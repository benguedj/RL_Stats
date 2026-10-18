"""Menu de l'overlay : panneau sombre assorti aux fenetres de l'app, a la place du menu Windows.

Les sous-menus s'ouvrent dans le meme panneau, avec une ligne de retour : une seule fenetre,
donc le clavier (fleches, Entree, Echap) et la fermeture au clic a cote restent simples.

Une page est une fonction qui renvoie une liste d'entrees construites avec les helpers
ci-dessous ; elle est rappelee a chaque affichage, le contenu est donc toujours a jour.
"""

import ctypes
import time
import tkinter as tk
from ctypes import wintypes

from ui_windows import EDGE, FG, GRID, MUTED, PANEL

HOVER = "#22314f"
CHIP = "#1b2844"
ICON_FONT = "Segoe MDL2 Assets"

# Icones Segoe MDL2 Assets (Windows 10 et 11)
I_HISTORY, I_SETTINGS, I_PEOPLE, I_SUMMARY, I_COPY = "\ue81c", "\ue713", "\ue716", "\ue8a5", "\ue8c8"
I_RESET, I_STYLE, I_EDIT, I_HIDE, I_QUIT = "\ue72c", "\ue771", "\ue70f", "\ued1a", "\ue7e8"
I_UPDATE, I_PLAY, I_PLACE, I_LINK, I_BOT = "\ue896", "\ue768", "\ue81d", "\ue8a7", "\ue99a"
I_SHAPE, I_SIZE, I_COLOR, I_CONTACT = "\ue97c", "\ue740", "\ue790", "\ue77b"
_CHEVRON, _BACK, _CHECK = "\ue76c", "\ue76b", "\ue73e"


def item(label, command, icon="", hint="", color=None, keep_open=False):
    return {"kind": "item", "label": label, "command": command, "icon": icon, "hint": hint, "color": color,
            "keep_open": keep_open}


def disabled(label, icon="", hint=""):
    return {"kind": "item", "label": label, "command": None, "icon": icon, "hint": hint, "color": MUTED}


def sub(label, page, icon=""):
    return {"kind": "sub", "label": label, "page": page, "icon": icon}


def choice(label, selected, command):
    """Entree a cocher qui laisse le menu ouvert (on voit le resultat sur l'overlay)."""
    return {"kind": "item", "label": label, "command": command, "icon": _CHECK if selected else "",
            "hint": "", "color": None, "keep_open": True, "accent": selected}


def chips(label, buttons, icon=""):
    """Rangee de petits boutons [(texte, couleur, commande)], qui laissent le menu ouvert."""
    return {"kind": "chips", "label": label, "buttons": buttons, "icon": icon}


def header(text, color=MUTED):
    return {"kind": "header", "text": text, "color": color}


def banner(title, segments, subtitle=""):
    """Bandeau du haut : titre a gauche, [(texte, couleur)] a droite."""
    return {"kind": "banner", "title": title, "segments": segments, "subtitle": subtitle}


SEPARATOR = {"kind": "sep"}


def work_area(x, y):
    """Zone utile (sans la barre des taches) de l'ecran qui contient le point."""
    u = ctypes.windll.user32

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD)]

    u.MonitorFromPoint.restype = ctypes.c_void_p
    u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    u.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    info = MONITORINFO(ctypes.sizeof(MONITORINFO))
    hmon = u.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2)  # MONITOR_DEFAULTTONEAREST
    if hmon and u.GetMonitorInfoW(hmon, ctypes.byref(info)):
        r = info.rcWork
        return r.left, r.top, r.right, r.bottom
    return 0, 0, u.GetSystemMetrics(0), u.GetSystemMetrics(1)


class PopupMenu:
    def __init__(self, root):
        self.root = root
        self.win = None
        self.on_close = None
        self.closed_at = 0

    @property
    def is_open(self):
        return self.win is not None

    def px(self, v):
        return round(v * self.scale)

    # --- Ouverture / fermeture ----------------------------------------------

    def open(self, page, x, y, on_close=None, keyboard=False):
        """Ouvre la page racine pres de (x, y), en se retournant si elle deborde de l'ecran.
        on_close(commande_lancee) est appele a la fermeture."""
        self.close()
        self.on_close = on_close
        self.anchor = (x, y)
        self.keyboard = keyboard
        self.stack = [("", page)]
        self.scale = self.root.winfo_fpixels("1i") / 96
        win = self.win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)
        win.configure(bg=EDGE)
        self.body = tk.Frame(win, bg=PANEL)
        self.body.pack(fill="both", expand=True, padx=1, pady=1)
        for seq, fn in (("<Escape>", self.back), ("<BackSpace>", self.back), ("<Up>", lambda: self.move(-1)),
                        ("<Down>", lambda: self.move(1)), ("<Left>", self.left), ("<Right>", self.right),
                        ("<Return>", self.activate), ("<space>", self.activate)):
            win.bind(seq, lambda e, f=fn: f())
        win.bind("<FocusOut>", lambda e: win.after(60, self._check_focus))
        self._watch_clicks()
        self.render()
        win.deiconify()
        win.update_idletasks()
        self._style_frame()
        self._focus()
        self._fade(0)

    def close(self, ran=False):
        if not self.win:
            return
        self.win.destroy()
        self.win = None
        self.closed_at = time.monotonic()
        if self.on_close:
            self.on_close(ran)

    def _check_focus(self):
        # Clic dans une autre fenetre (le jeu, le bureau...) : on ferme
        try:
            if self.win and self.win.focus_get() is None:
                self.close()
        except (KeyError, tk.TclError):
            pass

    def _watch_clicks(self, was_down=True):
        # Filet de securite si Windows a refuse le focus au menu : un clic a cote le ferme aussi.
        # Seulement un nouveau clic : le bouton qui vient d'ouvrir le menu est encore enfonce.
        if not self.win:
            return
        u = ctypes.windll.user32
        down = bool(u.GetAsyncKeyState(1) & 0x8000 or u.GetAsyncKeyState(2) & 0x8000)
        if down and not was_down:
            px, py = self.win.winfo_pointerxy()
            x, y = self.win.winfo_rootx(), self.win.winfo_rooty()
            if not (x <= px < x + self.win.winfo_width() and y <= py < y + self.win.winfo_height()):
                self.close()
                return
        self.win.after(50, lambda: self._watch_clicks(down))

    def _hwnd(self):
        return ctypes.windll.user32.GetParent(self.win.winfo_id())

    def _focus(self):
        u = ctypes.windll.user32
        u.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        u.SetForegroundWindow(self._hwnd())
        self.win.focus_force()

    def _style_frame(self):
        # Coins arrondis et bordure de Windows 11 (sans effet sur Windows 10)
        try:
            dwm, hwnd = ctypes.windll.dwmapi, self._hwnd()
            for attr, value in ((33, 2), (34, 0x00664634)):  # DWMWCP_ROUND, couleur de bordure (BGR de EDGE)
                v = ctypes.c_int(value)
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))
        except (AttributeError, OSError):
            pass

    def _fade(self, step):
        if self.win:
            self.win.attributes("-alpha", min(1.0, step / 5))
            if step < 5:
                self.win.after(12, lambda: self._fade(step + 1))

    # --- Pages ----------------------------------------------------------------

    def render(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.rows = []  # entrees selectionnables : (cadre, action, kind)
        self.selected = None
        title, page = self.stack[-1]
        tk.Frame(self.body, bg=PANEL, width=self.px(290), height=1).pack()  # largeur minimale
        if len(self.stack) > 1:
            self._back_row(title)
        for entry in page():
            getattr(self, "_" + entry["kind"])(entry)
        tk.Frame(self.body, bg=PANEL, height=self.px(6)).pack(fill="x")
        self.body.update_idletasks()
        self._place()
        if self.keyboard and self.rows:
            self.select(1 if len(self.stack) > 1 and len(self.rows) > 1 else 0)  # pas sur le retour

    def _place(self):
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x, y = self.anchor
        left, top, right, bottom = work_area(x, y)
        if x + w > right:
            x -= w
        if y + h > bottom:
            y -= h
        x = max(left, min(x, right - w))
        y = max(top, min(y, bottom - h))
        self.win.geometry(f"+{int(x)}+{int(y)}")

    def push(self, title, page):
        self.stack.append((title, page))
        self.render()

    def back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.render()
        else:
            self.close()

    def refresh(self):
        index = self.selected
        self.render()
        if index is not None and index < len(self.rows):
            self.select(index)

    # --- Entrees --------------------------------------------------------------

    def _line(self, icon, label, color, right="", right_font=None, right_color=MUTED):
        row = tk.Frame(self.body, bg=PANEL)
        row.pack(fill="x", padx=self.px(6))
        labels = [tk.Label(row, text=icon, font=(ICON_FONT, 11), width=2, bg=PANEL, fg=color if icon else PANEL)]
        labels[0].pack(side="left", padx=(self.px(8), self.px(6)), pady=self.px(7))
        if right:
            labels.append(tk.Label(row, text=right, font=right_font or ("Segoe UI", 9), bg=PANEL, fg=right_color))
            labels[-1].pack(side="right", padx=(self.px(10), self.px(10)))
        text = tk.Label(row, text=label, font=("Segoe UI", 10), bg=PANEL, fg=color, anchor="w")
        text.pack(side="left", fill="x", expand=True)
        labels.append(text)
        return row, labels

    def _selectable(self, row, widgets, action, kind="item"):
        index = len(self.rows)
        self.rows.append((row, widgets, action, kind))
        for w in [row, *widgets]:
            w.bind("<Enter>", lambda e, i=index: self.select(i))
            w.bind("<ButtonRelease-1>", lambda e, i=index: self.activate(i))
            w.configure(cursor="hand2")

    def _item(self, entry):
        enabled = entry["command"] is not None
        color = entry["color"] or (FG if enabled else MUTED)
        row, labels = self._line(entry["icon"], entry["label"], color, entry["hint"])
        if not (entry["color"] or entry.get("accent")):
            labels[0].configure(fg=MUTED)
        if enabled:
            self._selectable(row, labels, lambda: self._run(entry["command"], entry.get("keep_open")))

    def _sub(self, entry):
        row, labels = self._line(entry["icon"], entry["label"], FG, _CHEVRON, (ICON_FONT, 8))
        labels[0].configure(fg=MUTED)
        self._selectable(row, labels, lambda: self.push(entry["label"], entry["page"]), "sub")

    def _back_row(self, title):
        row, labels = self._line(_BACK, title, FG)
        labels[0].configure(fg=MUTED)
        labels[-1].configure(font=("Bahnschrift SemiBold", 10))
        self._selectable(row, labels, self.back, "back")
        self._sep(None)

    def _chips(self, entry):
        row, labels = self._line(entry["icon"], entry["label"], FG)
        labels[0].configure(fg=MUTED)
        box = tk.Frame(row, bg=PANEL)
        box.pack(side="right", padx=(0, self.px(6)))
        for text, color, command in entry["buttons"]:
            chip = tk.Label(box, text=text, font=("Bahnschrift SemiBold", 10), bg=CHIP, fg=color,
                            padx=self.px(8), pady=self.px(2))
            chip.pack(side="left", padx=self.px(2))
            self._selectable(chip, [], lambda c=command: self._run(c, True), "chip")

    def _header(self, entry):
        tk.Label(self.body, text=entry["text"], font=("Bahnschrift SemiBold", 9), bg=PANEL, fg=entry["color"],
                 anchor="w").pack(fill="x", padx=self.px(16), pady=(self.px(8), self.px(2)))

    def _banner(self, entry):
        top = tk.Frame(self.body, bg=PANEL)
        top.pack(fill="x", padx=self.px(16), pady=(self.px(12), 0))
        tk.Label(top, text=entry["title"], font=("Bahnschrift SemiBold", 13), bg=PANEL, fg=FG).pack(side="left")
        score = tk.Frame(top, bg=PANEL)
        score.pack(side="right")
        for text, color in entry["segments"]:
            tk.Label(score, text=text, font=("Bahnschrift SemiBold", 13), bg=PANEL, fg=color).pack(side="left")
        if entry["subtitle"]:
            tk.Label(self.body, text=entry["subtitle"], font=("Segoe UI", 9), bg=PANEL, fg=MUTED,
                     anchor="e").pack(fill="x", padx=self.px(16))
        self._sep(None)

    def _sep(self, entry):
        tk.Frame(self.body, bg=GRID, height=1).pack(fill="x", padx=self.px(12), pady=self.px(5))

    # --- Selection et clavier -------------------------------------------------

    def select(self, index):
        if self.selected is not None and self.selected < len(self.rows):
            self._paint(self.selected, False)
        self.selected = index
        self._paint(index, True)

    def _paint(self, index, on):
        row, widgets, _, kind = self.rows[index]
        if kind == "chip":
            row.configure(bg=EDGE if on else CHIP)
            return
        for w in [row, *widgets]:
            w.configure(bg=HOVER if on else PANEL)

    def move(self, step):
        if not self.rows:
            return
        index = (self.selected if self.selected is not None else -step) + step
        self.select(index % len(self.rows))

    def left(self):
        if self.selected is not None and self.rows[self.selected][3] == "chip" and \
                self.selected > 0 and self.rows[self.selected - 1][3] == "chip":
            self.move(-1)
        else:
            self.back()

    def right(self):
        if self.selected is None:
            return
        kind = self.rows[self.selected][3]
        if kind == "sub":
            self.activate()
        elif kind == "chip" and self.selected + 1 < len(self.rows) and self.rows[self.selected + 1][3] == "chip":
            self.move(1)

    def activate(self, index=None):
        if index is None:
            index = self.selected
        if index is None:
            return
        self.rows[index][2]()

    def _run(self, command, keep_open):
        if keep_open:
            command()
            if self.win:
                self.refresh()
        else:
            self.close(ran=True)
            self.root.after_idle(command)  # menu ferme d'abord (fenetres, boite de dialogue...)
