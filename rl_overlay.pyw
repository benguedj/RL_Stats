"""RL Overlay - compteur automatique de victoires / defaites pour Rocket League.

Utilise la Stats API officielle de Rocket League (socket TCP local, port 49123),
autorisee par Psyonix : aucune injection, aucun risque avec l'anti-cheat.
"""

import contextlib
import ctypes
import io
import json
import math
import os
import queue
import re
import socket
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request
import wave
import webbrowser
import winreg
import winsound
from collections import Counter
from ctypes import wintypes
from tkinter import simpledialog

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(APP_DIR, "_lib"), APP_DIR]  # Pillow embarque dans _lib

import achievements  # noqa: E402
import designs  # noqa: E402
import i18n  # noqa: E402
from discord_rpc import DiscordPresence  # noqa: E402
from history import History  # noqa: E402
from i18n import T  # noqa: E402
from obs_server import OBS_URL, ObsServer  # noqa: E402
from ui_windows import HistoryWindow, SettingsWindow, hex_to_rgb  # noqa: E402

if getattr(sys, "frozen", False):
    # Version .exe : APP_DIR est un dossier temporaire, les donnees vont dans %APPDATA%
    DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RL Overlay")
    os.makedirs(DATA_DIR, exist_ok=True)
else:
    DATA_DIR = APP_DIR
DATA_FILE = os.path.join(DATA_DIR, "stats.json")
HISTORY_FILE = os.path.join(DATA_DIR, "matches.json")
LOG_FILE = os.path.join(DATA_DIR, "overlay.log")

APP_VERSION = "1.1.0"
REPO = "benguedj/RL_Stats"
REPO_URL = f"https://github.com/{REPO}"
# "Application ID" Discord (https://discord.com/developers/applications) : vide = statut Discord indisponible
DISCORD_CLIENT_ID = ""
RESUME_HOURS = 2  # une session relancee dans ce delai reprend la ou elle en etait

API_HOST = "127.0.0.1"
API_PORT = 49123
PACKET_SEND_RATE = 10
LOCK_PORT = 49199  # empeche de lancer deux overlays en meme temps (le 2e reaffiche le 1er)

# Jauge de boost de RL sur un ecran 1440p : centre a 171 px du bord droit et
# 177 px du bas (l'overlay s'enroule autour de son sommet)
BOOST_FROM_RIGHT = 171
BOOST_FROM_BOTTOM = 177

SIZES = {0.9: "90 %", 0.95: "95 %", 1.0: "100 %", 1.05: "105 %", 1.1: "110 %"}


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def log(msg):
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
            os.replace(LOG_FILE, LOG_FILE + ".old")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def documents_dir():
    buf = ctypes.create_unicode_buffer(260)
    # CSIDL_PERSONAL = 5 (suit la redirection OneDrive eventuelle)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
        return buf.value
    return os.path.join(os.path.expanduser("~"), "Documents")


TRACKER_PROFILE = "https://rocketleague.tracker.network/rocket-league/profile/{platform}/{id}/overview"


def tracker_url(player):
    """Lien Tracker Network d'un joueur (rang / MMR), ou None (bot, plateforme inconnue).

    PrimaryId = "Plateforme|Uid|Ecran". Tracker Network identifie les comptes Steam par
    leur SteamID, et les autres plateformes par le pseudo.
    """
    platform, _, rest = (player.get("PrimaryId") or "").partition("|")
    uid = rest.partition("|")[0]
    name = player.get("Name", "")
    platform = platform.lower()
    if platform == "steam" and uid.isdigit() and uid != "0":
        return TRACKER_PROFILE.format(platform="steam", id=uid)
    by_name = {"epic": "epic", "ps4": "psn", "ps5": "psn", "psn": "psn",
               "xboxone": "xbl", "xbox": "xbl", "xbl": "xbl", "switch": "switch"}
    if platform in by_name and name:
        return TRACKER_PROFILE.format(platform=by_name[platform], id=urllib.parse.quote(name, safe=""))
    return None


def valid_id(primary_id):
    """Vrai pour un vrai compte (les bots ont une plateforme inconnue ou un uid nul)."""
    platform, _, rest = (primary_id or "").partition("|")
    uid = rest.partition("|")[0]
    return platform.lower() not in ("", "unknown", "none") and uid not in ("", "0")


def short_name(name, n=16):
    name = name.strip().upper()
    return name if len(name) <= n else name[:n - 1] + "…"


def rgb_hex(color):
    return "#%02x%02x%02x" % tuple(color[:3])


def rocket_league_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq RocketLeague.exe", "/NH"],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout
        return "rocketleague.exe" in out.lower()
    except OSError:
        return False


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return f'"{pythonw}" "{os.path.abspath(__file__)}"'


def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, "RL Overlay")
            return True
    except OSError:
        return False


def set_startup(enabled):
    """Demarrage avec Windows (cle Run de l'utilisateur, aucun droit admin necessaire)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, "RL Overlay", 0, winreg.REG_SZ, launch_command())
            else:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(key, "RL Overlay")
    except OSError as e:
        log(f"Demarrage avec Windows impossible : {e}")


def copy_image_to_clipboard(img, hwnd):
    """Copie une image Pillow dans le presse-papiers Windows (format DIB, collable dans Discord)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "BMP")
    dib = buf.getvalue()[14:]  # sans l'en-tete de fichier BMP
    k, u = ctypes.windll.kernel32, ctypes.windll.user32
    k.GlobalAlloc.restype = ctypes.c_void_p
    k.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k.GlobalLock.restype = ctypes.c_void_p
    k.GlobalLock.argtypes = k.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u.OpenClipboard.argtypes = [ctypes.c_void_p]
    u.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    handle = k.GlobalAlloc(0x0002, len(dib))  # GMEM_MOVEABLE
    ctypes.memmove(k.GlobalLock(handle), dib, len(dib))
    k.GlobalUnlock(handle)
    if not u.OpenClipboard(hwnd):
        return False
    try:
        u.EmptyClipboard()
        return bool(u.SetClipboardData(8, handle))  # CF_DIB (le presse-papiers devient proprietaire)
    finally:
        u.CloseClipboard()


def version_tuple(text):
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


def check_update(out_queue):
    """Interroge les Releases GitHub (thread) ; signale une version plus recente."""
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                     headers={"User-Agent": f"RL-Overlay/{APP_VERSION}",
                                              "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
        tag = data.get("tag_name", "")
        if tag and version_tuple(tag) > version_tuple(APP_VERSION):
            out_queue.put(("update", (tag, data.get("html_url") or f"{REPO_URL}/releases/latest")))
    except (OSError, ValueError) as e:
        log(f"Verification des mises a jour impossible : {e}")


def ensure_stats_api_enabled():
    """Active la Stats API (PacketSendRate > 0). Renvoie True si un fichier a ete modifie.

    On ne modifie que la config utilisateur (Documents) : toucher au DefaultStatsAPI.ini
    du dossier du jeu fait regenerer TAStatsAPI.ini par le jeu, qui repasse alors a 0.
    """
    files = [os.path.join(documents_dir(), "My Games", "Rocket League", "TAGame", "Config", "TAStatsAPI.ini")]
    changed = False
    for path in files:
        if not os.path.isfile(path):
            # Le dossier existe des que le jeu a ete lance une fois : on cree le fichier
            if not os.path.isdir(os.path.dirname(path)):
                continue
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"[TAGame.MatchStatsExporter_TA]\nPort={API_PORT}\nPacketSendRate={PACKET_SEND_RATE}\n")
                log(f"Stats API activee (fichier cree) : {path}")
                changed = True
            except OSError as e:
                log(f"Impossible de creer {path}: {e}")
            continue
        try:
            with open(path, encoding="utf-8-sig") as f:
                text = f.read()
            m = re.search(r"^\s*PacketSendRate\s*=\s*([\d.]+)", text, re.M)
            if m and float(m.group(1)) > 0:
                continue
            if m:
                text = text[:m.start(1)] + str(PACKET_SEND_RATE) + text[m.end(1):]
            elif "[TAGame.MatchStatsExporter_TA]" in text:
                text = text.replace("[TAGame.MatchStatsExporter_TA]",
                                    f"[TAGame.MatchStatsExporter_TA]\nPacketSendRate={PACKET_SEND_RATE}", 1)
            else:
                text = (f"[TAGame.MatchStatsExporter_TA]\nPort={API_PORT}\n"
                        f"PacketSendRate={PACKET_SEND_RATE}\n\n") + text
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            log(f"Stats API activee dans {path}")
            changed = True
        except (OSError, ValueError) as e:
            log(f"Impossible de modifier {path}: {e}")
    return changed


# --------------------------------------------------------------------------
# Ecrans et fenetre du jeu
# --------------------------------------------------------------------------

class Screens:
    """Ecrans branches et fenetre de Rocket League (multi-ecrans, ultra-larges, fenetre)."""

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD)]

    GAME_CLASS = "LaunchUnrealUWindowsClient"

    def __init__(self):
        u = ctypes.windll.user32
        H = ctypes.c_void_p
        self.MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, H, H, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        self.WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, H, wintypes.LPARAM)
        u.EnumDisplayMonitors.argtypes = [H, ctypes.c_void_p, self.MONITORENUMPROC, wintypes.LPARAM]
        u.GetMonitorInfoW.argtypes = [H, ctypes.POINTER(self.MONITORINFO)]
        u.EnumWindows.argtypes = [self.WNDENUMPROC, wintypes.LPARAM]
        for name in ("IsWindow", "IsWindowVisible", "IsIconic"):
            getattr(u, name).argtypes = [H]
        u.GetClassNameW.argtypes = [H, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowThreadProcessId.argtypes = [H, ctypes.POINTER(wintypes.DWORD)]
        u.GetClientRect.argtypes = [H, ctypes.POINTER(wintypes.RECT)]
        u.ClientToScreen.argtypes = [H, ctypes.POINTER(wintypes.POINT)]
        k = ctypes.windll.kernel32
        k.OpenProcess.restype = H
        k.QueryFullProcessImageNameW.argtypes = [H, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        k.CloseHandle.argtypes = [H]
        self.u, self.k = u, k
        self.game_hwnd = None
        self.last_game_rect = None

    def monitors(self):
        """[(x, y, largeur, hauteur)], l'ecran principal en premier."""
        found = []

        def cb(hmon, hdc, rect, data):
            info = self.MONITORINFO(ctypes.sizeof(self.MONITORINFO))
            if self.u.GetMonitorInfoW(hmon, ctypes.byref(info)):
                r = info.rcMonitor
                found.append((not info.dwFlags & 1, (r.left, r.top, r.right - r.left, r.bottom - r.top)))
            return True

        self.u.EnumDisplayMonitors(None, None, self.MONITORENUMPROC(cb), 0)
        found.sort(key=lambda m: m[0])  # tri stable : principal d'abord
        return [m for _, m in found] or [(0, 0, self.u.GetSystemMetrics(0), self.u.GetSystemMetrics(1))]

    def _exe_name(self, hwnd):
        pid = wintypes.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = self.k.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(520)
            size = wintypes.DWORD(520)
            if self.k.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return os.path.basename(buf.value).lower()
            return ""
        finally:
            self.k.CloseHandle(handle)

    def _find_game(self):
        found = []

        def cb(hwnd, data):
            if self.u.IsWindowVisible(hwnd):
                cls = ctypes.create_unicode_buffer(64)
                self.u.GetClassNameW(hwnd, cls, 64)
                if cls.value == self.GAME_CLASS and self._exe_name(hwnd) == "rocketleague.exe":
                    found.append(hwnd)
            return True

        self.u.EnumWindows(self.WNDENUMPROC(cb), 0)
        return found[0] if found else None

    def game_rect(self):
        """Zone d'affichage du jeu (x, y, largeur, hauteur), ou la derniere connue."""
        if not (self.game_hwnd and self.u.IsWindow(self.game_hwnd)):
            self.game_hwnd = self._find_game()
        hwnd = self.game_hwnd
        if hwnd and not self.u.IsIconic(hwnd):
            rc = wintypes.RECT()
            pt = wintypes.POINT(0, 0)
            if self.u.GetClientRect(hwnd, ctypes.byref(rc)) and self.u.ClientToScreen(hwnd, ctypes.byref(pt)):
                if rc.right > 200 and rc.bottom > 200:
                    self.last_game_rect = (pt.x, pt.y, rc.right, rc.bottom)
        return self.last_game_rect


# --------------------------------------------------------------------------
# Sons
# --------------------------------------------------------------------------

class Sounds:
    """Petits jingles synthetises (pas de fichier a fournir), joues sans bloquer."""

    NOTES = {"w": [(523.25, 0.09), (659.25, 0.09), (783.99, 0.09), (1046.5, 0.40)],
             "l": [(392.0, 0.17), (329.63, 0.17), (261.63, 0.55)]}

    def __init__(self, folder):
        self.folder = folder
        self.volume = None

    def _synth(self, notes, volume):
        rate = 44100
        frames = bytearray()
        amp = 32767 * 0.55 * volume / 100
        for freq, dur in notes:
            n = int(rate * dur)
            for i in range(n):
                t = i / rate
                env = min(1.0, t / 0.005) * math.exp(-t * (3.0 if dur > 0.3 else 7.0))
                v = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t)
                frames += struct.pack("<h", int(amp * env * v / 1.25))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(bytes(frames))
        return buf.getvalue()

    def play(self, kind, volume):
        try:
            if volume != self.volume:
                os.makedirs(self.folder, exist_ok=True)
                for k, notes in self.NOTES.items():
                    with open(os.path.join(self.folder, f"{k}.wav"), "wb") as f:
                        f.write(self._synth(notes, volume))
                self.volume = volume
            winsound.PlaySound(os.path.join(self.folder, f"{kind}.wav"),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except (OSError, RuntimeError) as e:
            log(f"Son impossible : {e!r}")


# --------------------------------------------------------------------------
# Raccourcis clavier globaux
# --------------------------------------------------------------------------

class Hotkeys(threading.Thread):
    """Ctrl+Maj+H (masquer / afficher) et Ctrl+Maj+R (reinitialiser la session).

    RegisterHotKey envoie WM_HOTKEY au thread qui l'a enregistre : ce thread a donc
    sa propre boucle de messages et transmet les touches a l'interface via la file.
    """

    KEYS = {1: ("toggle", 0x48), 2: ("reset", 0x52)}  # H, R

    def __init__(self, out_queue):
        super().__init__(daemon=True)
        self.q = out_queue
        self.thread_id = None

    def run(self):
        u = ctypes.windll.user32
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        for hid, (name, vk) in self.KEYS.items():
            if not u.RegisterHotKey(None, hid, 0x2 | 0x4 | 0x4000, vk):  # Ctrl + Maj, sans repetition
                log(f"Raccourci Ctrl+Maj+{chr(vk)} deja utilise par une autre application")
        msg = wintypes.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312 and msg.wParam in self.KEYS:  # WM_HOTKEY
                self.q.put(("hotkey", self.KEYS[msg.wParam][0]))
        for hid in self.KEYS:
            u.UnregisterHotKey(None, hid)

    def stop(self):
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)  # WM_QUIT


# --------------------------------------------------------------------------
# Icone pres de l'horloge et bouton dans la barre des taches
# --------------------------------------------------------------------------

class ShellIcons(threading.Thread):
    """Fenetre Windows invisible (toujours reduite) qui porte :
      - l'icone de la zone de notification (clic gauche = afficher / masquer, clic droit = menu) ;
      - le bouton de la barre des taches (clic = afficher / masquer, "Fermer la fenetre" = quitter).
    L'overlay lui-meme reste une "fenetre outil" sans bouton, pour ne pas gener en jeu.
    """

    WM_TRAY = 0x8001  # WM_APP + 1
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_void_p, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM)

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [("style", ctypes.c_uint), ("lpfnWndProc", ctypes.c_void_p), ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int), ("hInstance", ctypes.c_void_p), ("hIcon", ctypes.c_void_p),
                    ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
                    ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", ctypes.c_void_p), ("uID", ctypes.c_uint),
                    ("uFlags", ctypes.c_uint), ("uCallbackMessage", ctypes.c_uint), ("hIcon", ctypes.c_void_p),
                    ("szTip", ctypes.c_wchar * 128), ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                    ("szInfo", ctypes.c_wchar * 256), ("uVersion", ctypes.c_uint),
                    ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", wintypes.DWORD),
                    ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", ctypes.c_void_p)]

    def __init__(self, out_queue, icon_path, title, tray, taskbar):
        super().__init__(daemon=True)
        self.q = out_queue
        self.icon_path = icon_path
        self.title = title
        self.want_tray, self.want_taskbar = tray, taskbar
        self.tray_shown = False
        self.tip = title
        self.hwnd = None
        self.armed = False  # ignore les messages de taille envoyes a la creation
        self.last_click = 0
        self.ready = threading.Event()
        u = ctypes.windll.user32
        H = ctypes.c_void_p
        u.DefWindowProcW.argtypes = [H, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
        u.DefWindowProcW.restype = self.LRESULT
        u.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                      ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, H, H, H, H]
        u.CreateWindowExW.restype = H
        u.LoadImageW.argtypes = [H, wintypes.LPCWSTR, ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        u.LoadImageW.restype = H
        u.SendMessageW.argtypes = [H, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
        u.ShowWindowAsync.argtypes = [H, ctypes.c_int]
        u.PostMessageW.argtypes = [H, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
        u.SetForegroundWindow.argtypes = [H]
        ctypes.windll.kernel32.GetModuleHandleW.restype = H
        ctypes.windll.shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
        self.u = u
        self.proc = self.WNDPROC(self._wndproc)  # garder une reference (sinon crash)

    def _icon(self, size):
        return self.u.LoadImageW(None, self.icon_path, 1, size, size, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE

    def run(self):
        u = self.u
        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        self.taskbar_created = u.RegisterWindowMessageW("TaskbarCreated")
        wc = self.WNDCLASSW()
        wc.lpfnWndProc = ctypes.cast(self.proc, ctypes.c_void_p)
        wc.hInstance = hinst
        wc.lpszClassName = "RLOverlayShell"
        dpi = u.GetDpiForSystem() if hasattr(u, "GetDpiForSystem") else 96
        self.small_icon = self._icon(round(16 * dpi / 96))
        self.big_icon = self._icon(round(24 * dpi / 96))  # taille exacte d'un bouton de barre des taches
        wc.hIcon = self.big_icon
        u.RegisterClassW(ctypes.byref(wc))
        # WS_POPUP | WS_SYSMENU | WS_MINIMIZEBOX, WS_EX_APPWINDOW, hors de l'ecran
        self.hwnd = u.CreateWindowExW(0x40000, "RLOverlayShell", self.title, 0x80000000 | 0x80000 | 0x20000,
                                      -10000, -10000, 1, 1, None, None, hinst, None)
        u.SendMessageW(self.hwnd, 0x80, 1, self.big_icon or 0)    # WM_SETICON, ICON_BIG
        u.SendMessageW(self.hwnd, 0x80, 0, self.small_icon or 0)  # ICON_SMALL
        if self.want_taskbar:
            u.ShowWindow(self.hwnd, 7)  # SW_SHOWMINNOACTIVE : bouton present, fenetre jamais visible
        self.armed = True
        if self.want_tray:
            self._tray(0)  # NIM_ADD
        self.ready.set()
        msg = wintypes.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u.TranslateMessage(ctypes.byref(msg))
            u.DispatchMessageW(ctypes.byref(msg))

    def _tray(self, action):
        nid = self.NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = 0x1 | 0x2 | 0x4  # NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = self.WM_TRAY
        nid.hIcon = self.small_icon
        nid.szTip = self.tip[:127]
        ok = ctypes.windll.shell32.Shell_NotifyIconW(action, ctypes.byref(nid))
        if action == 0:
            self.tray_shown = bool(ok)
        elif action == 2:
            self.tray_shown = False

    def _clicked(self):
        now = time.monotonic()
        if now - self.last_click > 0.4:  # un clic peut produire plusieurs messages
            self.last_click = now
            self.q.put(("shell", "toggle"))

    def _wndproc(self, hwnd, msg, wparam, lparam):
        u = self.u
        if msg == self.WM_TRAY:
            event = lparam & 0xFFFF
            if event == 0x0202:  # WM_LBUTTONUP
                self._clicked()
            elif event in (0x0205, 0x007B):  # WM_RBUTTONUP, WM_CONTEXTMENU
                pt = wintypes.POINT()
                u.GetCursorPos(ctypes.byref(pt))
                self.q.put(("shell_menu", (pt.x, pt.y)))
            return 0
        if msg == self.taskbar_created and self.want_tray:  # l'explorateur a redemarre
            self._tray(0)
            return 0
        if msg == 0x0112:  # WM_SYSCOMMAND
            command = wparam & 0xFFF0
            if command in (0xF120, 0xF030):  # SC_RESTORE, SC_MAXIMIZE : clic sur le bouton
                self._clicked()
                return 0
            if command == 0xF060:  # SC_CLOSE
                self.q.put(("shell", "quit"))
                return 0
        if msg == 0x0005 and self.armed and wparam in (0, 2):  # WM_SIZE restauree / agrandie malgre tout
            self._clicked()
            u.ShowWindowAsync(hwnd, 7)
            return 0
        if msg == 0x0010:  # WM_CLOSE
            self.q.put(("shell", "quit"))
            return 0
        return u.DefWindowProcW(hwnd, msg, wparam, lparam)

    # --- Appels depuis l'interface (autre thread : uniquement des appels surs) ---

    def set_tray(self, enabled):
        self.want_tray = enabled
        if self.hwnd:
            if enabled and not self.tray_shown:
                self._tray(0)
            elif not enabled and self.tray_shown:
                self._tray(2)

    def set_taskbar(self, enabled):
        self.want_taskbar = enabled
        if self.hwnd:
            self.u.ShowWindowAsync(self.hwnd, 7 if enabled else 0)  # SW_SHOWMINNOACTIVE / SW_HIDE

    def set_tip(self, text):
        if text != self.tip:
            self.tip = text
            if self.hwnd and self.tray_shown:
                self._tray(1)  # NIM_MODIFY

    def close(self):
        if self.hwnd:
            if self.tray_shown:
                self._tray(2)  # NIM_DELETE, sinon une icone fantome reste pres de l'horloge
            self.u.PostMessageW(self.hwnd, 0x0012, 0, 0)  # WM_QUIT


# --------------------------------------------------------------------------
# Sauvegarde
# --------------------------------------------------------------------------

class Store:
    DEFAULTS = {
        "player_name": "", "detected_name": "", "design": "tableau", "shape": "arrondi", "offsets": {},
        "size": 1.0, "processed": [],
        "lang": "auto", "monitor": 0, "counter": "mode", "goal": 0,
        "win_color": "#2ee66b", "loss_color": "#ff4d4d", "opacity": 100, "animations": True,
        "sounds": False, "volume": 60, "summary": True, "summary_time": 12, "met_alert": True,
        "obs": False, "hotkeys": True, "tray": True, "taskbar": True,
        "auto_hide": True, "resume_session": True, "check_updates": True, "tilt_alert": True, "discord": False,
        "session_saved": {}, "achievements": {},
    }

    def __init__(self):
        self.data = json.loads(json.dumps(self.DEFAULTS))
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, encoding="utf-8") as f:
                    saved = json.load(f)
                self.data.update({k: v for k, v in saved.items()
                                  if k in self.data and isinstance(v, type(self.DEFAULTS[k]))
                                  or (k == "size" and isinstance(v, (int, float)))})
                if "offset" in saved:  # ancienne version : un seul decalage, pour l'arc
                    self.data["offsets"].setdefault("arc", saved["offset"])
                # Anciennes versions : un seul reglage "design" qui melangeait style et forme
                old = {"arc": ("tableau", "arrondi"), "score": ("tableau", "droit"), "mini": ("minimal", "droit")}
                if self.data["design"] in old:
                    self.data["design"], self.data["shape"] = old[self.data["design"]]
                if (self.data["design"], self.data["shape"]) not in designs.RENDERERS:
                    self.data["design"], self.data["shape"] = "tableau", "arrondi"
            except (OSError, ValueError):
                log("stats.json illisible, valeurs par defaut")
        self.save()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        self.data["processed"] = self.data["processed"][-100:]
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)


# --------------------------------------------------------------------------
# Connexion a la Stats API
# --------------------------------------------------------------------------

class JsonStream:
    """Decoupe un flux texte en objets JSON complets (sans supposer de separateur)."""

    def __init__(self):
        self.buf = ""
        self.pos = 0
        self.start = -1
        self.depth = 0
        self.in_str = False
        self.esc = False

    def feed(self, text):
        self.buf += text
        out = []
        buf = self.buf
        i = self.pos
        while i < len(buf):
            c = buf[i]
            if self.in_str:
                if self.esc:
                    self.esc = False
                elif c == "\\":
                    self.esc = True
                elif c == '"':
                    self.in_str = False
            elif c == '"':
                if self.depth > 0:
                    self.in_str = True
            elif c == "{":
                if self.depth == 0:
                    self.start = i
                self.depth += 1
            elif c == "}" and self.depth > 0:
                self.depth -= 1
                if self.depth == 0:
                    out.append(buf[self.start:i + 1])
                    self.start = -1
            i += 1
        # On ne garde que l'objet en cours
        if self.depth > 0:
            self.buf = buf[self.start:]
            self.pos = len(self.buf)
            self.start = 0
        else:
            self.buf = ""
            self.pos = 0
        return out


def parse_message(raw):
    try:
        msg = json.loads(raw)
    except ValueError:
        return None, None
    event = msg.get("Event")
    data = msg.get("Data")
    if isinstance(data, str):  # certaines versions double-encodent Data
        try:
            data = json.loads(data)
        except ValueError:
            data = {}
    return event, data if isinstance(data, dict) else {}


class ApiListener(threading.Thread):
    def __init__(self, out_queue):
        super().__init__(daemon=True)
        self.q = out_queue

    def run(self):
        import codecs
        while True:
            try:
                with socket.create_connection((API_HOST, API_PORT), timeout=3) as sock:
                    sock.settimeout(None)
                    self.q.put(("status", True))
                    log("Connecte a Rocket League")
                    stream = JsonStream()
                    decoder = codecs.getincrementaldecoder("utf-8")("replace")
                    while True:
                        chunk = sock.recv(65536)
                        if not chunk:
                            break
                        for raw in stream.feed(decoder.decode(chunk)):
                            event, data = parse_message(raw)
                            if event:
                                self.q.put(("event", (event, data)))
            except OSError:
                pass
            self.q.put(("status", False))
            time.sleep(3)


# --------------------------------------------------------------------------
# Suivi des matchs
# --------------------------------------------------------------------------

FEED_STATS = {"Goal": "goals", "Assist": "assists", "Save": "saves", "Shot": "shots", "Demolish": "demos"}
STATE_STATS = {"Goals": "goals", "Assists": "assists", "Saves": "saves", "Shots": "shots", "Demos": "demos",
               "Score": "score"}


class MatchTracker:
    """Determine l'equipe du joueur, le mode, les stats et le resultat de chaque match."""

    def __init__(self, store, on_result, on_start):
        self.store = store
        self.on_result = on_result
        self.on_start = on_start
        self.last_players = []  # joueurs du dernier match vu (garde apres la fin du match)
        self.ids = {}  # pseudo -> PrimaryId (evenements PlayerJoined)
        self.reset(None)

    def reset(self, guid):
        self.guid = guid
        self.team_votes = Counter()
        self.name_votes = Counter()
        self.players = []
        self.seen = {}  # cle -> {"name", "id", "team", stats...} : tous les joueurs passes dans le match
        self.feed = {}  # pseudo -> Counter des evenements du fil (buts, arrets...)
        self.mvp = set()
        self.goal_speeds = {}  # pseudo -> vitesse max de ses buts
        self.team_goals = Counter()
        self.team_scores = None  # scores officiels si le jeu les envoie
        self.team_size = 0
        self.created = time.time()  # debut du match (pour la duree de session)
        self.started = False
        self.announced = False
        self.finished = False
        self.goal_spots = []  # [x, z] ou mes buts entrent dans la cage
        self.kick = None  # engagement en cours : {"t": instant du premier contact}
        self.kickoffs = [0, 0, 0]  # gagnes, perdus, neutres
        self.last_ball = None  # derniere position connue du ballon
        self.boost = [0, 0, 0, 0]  # echantillons, somme du boost, a 0 boost, supersonique

    @property
    def mode(self):
        return f"{self.team_size}v{self.team_size}" if 1 <= self.team_size <= 4 else None

    def handle(self, event, data):
        guid = data.get("MatchGuid") or None
        if event not in ("UpdateState", "BallHit", "ClockUpdatedSeconds"):
            log(f"{event} {json.dumps(data, ensure_ascii=False)[:300]}")

        if event in ("MatchCreated", "MatchInitialized") and guid != self.guid:
            self.reset(guid)
        elif event == "UpdateState":
            if guid and guid != self.guid:  # app lancee en cours de match
                self.reset(guid)
            self._observe(data)
        elif event == "PlayerJoined":
            if data.get("PlayerName") and valid_id(data.get("PrimaryId")):
                self.ids[data["PlayerName"]] = data["PrimaryId"]
        elif event == "RoundStarted":
            self.started = True
            self.kick = {"t": None}  # coup d'envoi : on attend le premier contact
            if self.guid and not self.announced and self.players:
                self.announced = True
                self.on_start(self)
        elif event == "BallHit":
            loc = (data.get("Ball") or {}).get("Location")
            if loc:
                self.last_ball = loc
            if self.kick is not None and self.kick["t"] is None:
                self.kick["t"] = time.monotonic()
        elif event == "StatfeedEvent":
            name = (data.get("MainTarget") or {}).get("Name")
            if name:
                self.feed.setdefault(name, Counter())[data.get("EventName")] += 1
                if data.get("EventName") == "MVP":
                    self.mvp.add(name)
        elif event == "GoalScored":
            scorer = data.get("Scorer") or {}
            if scorer.get("TeamNum") is not None:
                self.team_goals[scorer["TeamNum"]] += 1
            if scorer.get("Name") and data.get("GoalSpeed"):
                name = scorer["Name"]
                self.goal_speeds[name] = max(self.goal_speeds.get(name, 0), float(data["GoalSpeed"]))
            spot = data.get("ImpactLocation") or {}
            if (scorer.get("Name", "").strip().lower() == self.my_name().strip().lower()
                    and any(spot.get(a) for a in ("X", "Y", "Z"))):
                # Vue depuis le terrain : X est inverse selon la cage (bleue en Y < 0, orange en Y > 0)
                side = 1 if spot.get("Y", 0) >= 0 else -1
                self.goal_spots.append([round(spot.get("X", 0) * side), round(spot.get("Z", 0))])
            self.kick = None
        elif event == "MatchEnded":
            self._finish(guid, data.get("WinnerTeamNum"))
        elif event == "MatchDestroyed":
            # Quitter un match en cours = defaite
            if self.guid and self.started and not self.finished:
                log("Match quitte avant la fin -> defaite")
                self._finish(self.guid, None, forfeit=True)
            self.reset(None)

    def player_id(self, p):
        pid = p.get("PrimaryId")
        if valid_id(pid):
            return pid
        return self.ids.get(p.get("Name", ""))

    def _observe(self, data):
        game = data.get("Game") or {}
        players = data.get("Players") or []
        if players:
            self.players = players
            if self.guid:  # matchs en ligne uniquement
                self.last_players = players
                sizes = Counter(p.get("TeamNum") for p in players)
                self.team_size = max(self.team_size, max(sizes.values()))
                for p in players:
                    entry = self.seen.setdefault(p.get("PrimaryId") or p.get("Name", ""), {})
                    entry.update({"name": p.get("Name", ""), "team": p.get("TeamNum"), "id": self.player_id(p)})
                    for src, dst in STATE_STATS.items():
                        if src in p:
                            entry[dst] = int(p[src] or 0)
        teams = game.get("Teams")
        if isinstance(teams, list) and teams:
            self.team_scores = {t.get("TeamNum"): t.get("Score") for t in teams if isinstance(t, dict)}
        if game.get("bReplay"):
            return
        ball = game.get("Ball") or {}
        if isinstance(ball.get("Location"), dict):
            self.last_ball = ball["Location"]
        if game.get("TimeSeconds") is not None and game.get("bHasWinner") is False:
            self.started = self.started or bool(self.guid)
            if self.guid:
                self._sample_boost(players)
        self._check_kickoff()
        target = game.get("Target") or {}
        if game.get("bHasTarget") and target.get("Name"):
            self.team_votes[target.get("TeamNum")] += 1
            self.name_votes[target["Name"]] += 1
        else:
            # Les donnees "spectateur" (boost...) ne sont envoyees que pour notre equipe
            teams = {p.get("TeamNum") for p in players if "Boost" in p}
            if len(teams) == 1:
                self.team_votes[teams.pop()] += 1

    def _sample_boost(self, players):
        """Boost du joueur (envoye par le jeu pour notre equipe uniquement), 10 fois par seconde."""
        me = self.my_name().strip().lower()
        p = next((p for p in players if p.get("Name", "").strip().lower() == me), None)
        if p is None or "Boost" not in p:
            return
        boost = float(p.get("Boost") or 0)
        self.boost[0] += 1
        self.boost[1] += boost
        self.boost[2] += boost <= 0
        self.boost[3] += bool(p.get("bSupersonic"))

    def _check_kickoff(self):
        """2,5 s apres le premier contact : le ballon est-il chez l'adversaire ?
        L'equipe 0 (bleue) attaque vers les Y positifs."""
        if not (self.kick and self.kick["t"]) or time.monotonic() - self.kick["t"] < 2.5:
            return
        self.kick = None
        team = self.my_team()
        if team is None or not self.last_ball:
            return
        y = float(self.last_ball.get("Y", 0)) * (1 if int(team) == 0 else -1)
        self.kickoffs[0 if y > 600 else 1 if y < -600 else 2] += 1

    def my_name(self):
        if self.store["player_name"].strip():
            return self.store["player_name"].strip()
        if self.name_votes:
            return self.name_votes.most_common(1)[0][0]
        return self.store["detected_name"]

    def my_team(self):
        name = self.store["player_name"].strip().lower()
        if name:
            for p in self.players:
                if p.get("Name", "").strip().lower() == name:
                    return p.get("TeamNum")
        if self.team_votes:
            return self.team_votes.most_common(1)[0][0]
        return None

    def others(self):
        """[(id, pseudo, equipe)] des vrais joueurs du match, moi exclu."""
        me = self.my_name().strip().lower()
        out = []
        for e in self.seen.values():
            if e.get("id") and e["name"].strip().lower() != me:
                out.append((e["id"], e["name"], e.get("team")))
        return out

    def my_stats(self):
        me = self.my_name().strip().lower()
        entry = next((e for e in self.seen.values() if e["name"].strip().lower() == me), {})
        feed = next((c for n, c in self.feed.items() if n.strip().lower() == me), Counter())
        stats = {}
        for src, dst in FEED_STATS.items():
            stats[dst] = entry.get(dst, feed.get(src, 0))  # stats du jeu si dispo, sinon fil d'evenements
        stats["score"] = entry.get("score")
        stats["mvp"] = any(n.strip().lower() == me for n in self.mvp)
        stats["fastest"] = round(max((v for n, v in self.goal_speeds.items() if n.strip().lower() == me),
                                     default=0), 1)
        stats["feed"] = {k: v for k, v in feed.items() if k}
        stats["goal_spots"] = self.goal_spots
        if sum(self.kickoffs):
            stats["kickoffs"] = list(self.kickoffs)
        n, total, zero, superso = self.boost
        if n >= 100:  # au moins ~10 s de donnees
            stats["boost"] = {"avg": round(total / n, 1), "zero": round(zero * 100 / n, 1),
                              "superso": round(superso * 100 / n, 1)}
        return stats

    def _finish(self, guid, winner, forfeit=False):
        guid = guid or self.guid
        if self.finished:
            return
        self.finished = True
        if not guid:
            log("Match hors ligne ignore")
            return
        if guid in self.store["processed"]:
            return
        team = self.my_team()
        if forfeit:
            won = False
        elif team is None or winner is None:
            log(f"Resultat inconnu (equipe={team}, gagnant={winner})")
            return
        else:
            won = int(winner) == int(team)
        if self.name_votes:
            self.store.data["detected_name"] = self.name_votes.most_common(1)[0][0]
        self.store.data["processed"].append(guid)
        log(f"Resultat: {'VICTOIRE' if won else 'DEFAITE'} (equipe={team}, gagnant={winner}, mode={self.mode})")

        score = None
        if team is not None:
            goals = self.team_scores if self.team_scores else self.team_goals
            score = [goals.get(team, 0), goals.get(1 - int(team), 0)]
        others = self.others()
        self.on_result(won, {
            "t": time.time(), "start": round(self.created), "guid": guid, "mode": self.mode, "won": won,
            "forfeit": forfeit, "score": score,
            "me": self.my_stats(),
            "with": [[pid, name] for pid, name, t in others if team is not None and t == team],
            "against": [[pid, name] for pid, name, t in others if team is None or t != team],
        })


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------

def enable_dpi_awareness():
    # Rendu net sur les ecrans en 125 % / 150 % (sinon Windows etire une image floue)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


class LayeredWindow:
    """Affiche une image RGBA dans une fenetre Windows a transparence par pixel."""

    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x80000
    WS_EX_TOOLWINDOW = 0x80

    class BLENDFUNCTION(ctypes.Structure):
        _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                    ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    def __init__(self, tk_window):
        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        H = ctypes.c_void_p
        u.GetParent.restype = H
        u.GetParent.argtypes = [H]
        u.GetDC.restype = H
        u.GetDC.argtypes = [H]
        u.ReleaseDC.argtypes = [H, H]
        u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.GetWindowLongPtrW.argtypes = [H, ctypes.c_int]
        u.SetWindowLongPtrW.argtypes = [H, ctypes.c_int, ctypes.c_ssize_t]
        u.UpdateLayeredWindow.argtypes = [H, H, ctypes.POINTER(wintypes.POINT), ctypes.POINTER(wintypes.SIZE),
                                          H, ctypes.POINTER(wintypes.POINT), wintypes.DWORD,
                                          ctypes.POINTER(self.BLENDFUNCTION), wintypes.DWORD]
        g.CreateCompatibleDC.restype = H
        g.CreateCompatibleDC.argtypes = [H]
        g.CreateDIBSection.restype = H
        g.CreateDIBSection.argtypes = [H, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                                       H, wintypes.DWORD]
        g.SelectObject.restype = H
        g.SelectObject.argtypes = [H, H]
        g.DeleteObject.argtypes = [H]
        g.DeleteDC.argtypes = [H]
        self.u, self.g = u, g

        tk_window.update_idletasks()
        self.hwnd = u.GetParent(tk_window.winfo_id())
        style = u.GetWindowLongPtrW(self.hwnd, self.GWL_EXSTYLE)
        u.SetWindowLongPtrW(self.hwnd, self.GWL_EXSTYLE, style | self.WS_EX_LAYERED | self.WS_EX_TOOLWINDOW)

    def show(self, img, x, y, alpha=255):
        u, g = self.u, self.g
        w, h = img.size
        data = img.convert("RGBa").tobytes("raw", "BGRa")  # BGRA premultiplie
        screen = u.GetDC(None)
        mem = g.CreateCompatibleDC(screen)
        bmi = self.BITMAPINFOHEADER(ctypes.sizeof(self.BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        bits = ctypes.c_void_p()
        bmp = g.CreateDIBSection(mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        try:
            ctypes.memmove(bits, data, len(data))
            old = g.SelectObject(mem, bmp)
            blend = self.BLENDFUNCTION(0, 0, alpha, 1)  # AC_SRC_OVER, alpha par pixel
            u.UpdateLayeredWindow(self.hwnd, screen, ctypes.byref(wintypes.POINT(x, y)),
                                  ctypes.byref(wintypes.SIZE(w, h)), mem, ctypes.byref(wintypes.POINT(0, 0)),
                                  0, ctypes.byref(blend), 2)  # ULW_ALPHA
            g.SelectObject(mem, old)
        finally:
            g.DeleteObject(bmp)
            g.DeleteDC(mem)
            u.ReleaseDC(None, screen)


def empty_image():
    return designs.Image.new("RGBA", (1, 1), (0, 0, 0, 0))


class SummaryCard:
    """Carte de resume affichee au-dessus de l'overlay apres un match (clic = fermer)."""

    def __init__(self, root):
        self.root = root
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.geometry("1x1+0+0")
        self.layer = LayeredWindow(self.top)
        self.top.bind("<ButtonPress-1>", lambda e: self.hide())
        self.img = None
        self.pos = (0, 0)
        self.alpha = 0
        self.job = None
        self.layer.show(empty_image(), 0, 0)

    def _cancel(self):
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None

    def show(self, img, x, y, seconds):
        self._cancel()
        self.img, self.pos = img, (x, y)
        self.top.geometry(f"{img.width}x{img.height}+{x}+{y}")
        self.top.lift()
        self._fade(+1, seconds)

    def _fade(self, direction, seconds=0):
        self.alpha = max(0, min(255, self.alpha + direction * 40))
        if self.alpha == 0:
            self.layer.show(empty_image(), *self.pos)
            self.img = None
            return
        self.layer.show(self.img, *self.pos, alpha=self.alpha)
        if direction > 0 and self.alpha == 255:
            self.job = self.root.after(int(seconds * 1000), lambda: self._fade(-1))
        else:
            self.job = self.root.after(16, lambda: self._fade(direction, seconds))

    def hide(self):
        self._cancel()
        if self.img is not None:
            self._fade(-1)

    @property
    def visible(self):
        return self.img is not None


class Overlay:
    def __init__(self, lock):
        self.store = Store()
        i18n.set_lang(self.store["lang"])
        self.apply_colors()
        self.history = History(HISTORY_FILE, log)
        self.session = {}  # mode -> [victoires, defaites]
        self.streak = 0  # >0 victoires d'affilee, <0 defaites
        self.current_mode = None
        self.connected = False
        self.notice = None  # cle de texte i18n
        self.banner = None  # (texte, couleur, "w"|"l"|None) pendant quelques secondes
        self.anim = None  # designs.MatchAnimation en cours
        self._anim_job = None
        self._banner_job = None
        self._geom = None
        self.hidden = False
        self.hover = False
        self.buttons = {}
        self._dragging = False
        self.last_summary = None
        self.event_id = 0
        self.event_kind = None
        self.settings_window = None
        self.history_window = None
        self.hotkeys = None
        self.auto_hidden = False  # masque car le jeu n'est pas au premier plan
        self.grace_until = time.monotonic() + 8  # visible quelques secondes au lancement
        self.banner_queue = []
        self.session_start = None  # heure du premier match de la session
        self.break_hours = 0  # alertes "pause" deja affichees
        self.update_info = None  # (version, url) si une mise a jour existe
        self.restore_session()
        if not self.store["achievements"] and self.history.matches:
            # Premiere version avec trophees : ceux deja merites sont acquis sans annonce
            self.store["achievements"] = {a: time.time() for a in achievements.unlocked(self.history.matches)}

        self.q = queue.Queue()
        self.tracker = MatchTracker(self.store, self.add_result, self.on_match_start)
        self.screens = Screens()
        self.sounds = Sounds(os.path.join(DATA_DIR, "sounds"))
        self.obs = ObsServer(log)

        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("RL Overlay")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry("1x1+0+0")
        icon = os.path.join(APP_DIR, "rl_overlay_wl.ico")
        if os.path.exists(icon):
            self.root.iconbitmap(default=icon)
        self.shell = ShellIcons(self.q, icon, "RL Overlay", self.store["tray"], self.store["taskbar"])
        self.shell.start()
        self.shell.ready.wait(2)
        self.layer = LayeredWindow(self.root)
        self.card = SummaryCard(self.root)
        self.viewport = self.compute_viewport()

        self.root.bind("<ButtonPress-1>", self.on_press)
        self.root.bind("<B1-Motion>", self.drag_move)
        self.root.bind("<ButtonRelease-1>", self.drag_end)
        self.root.bind("<Button-3>", self.show_menu)
        self.root.bind("<Enter>", self.on_hover)
        self.root.bind("<Leave>", self.on_hover)

        self._build_menu()
        self.draw()

        ApiListener(self.q).start()
        threading.Thread(target=self._accept_wakeups, args=(lock,), daemon=True).start()
        if self.store["obs"]:
            self.obs.start()
        if self.store["hotkeys"]:
            self.start_hotkeys()
        self.discord = DiscordPresence(DISCORD_CLIENT_ID, log)
        if DISCORD_CLIENT_ID:
            self.discord.start()
            self.update_presence()
        if self.store["check_updates"]:
            threading.Thread(target=check_update, args=(self.q,), daemon=True).start()
        self.check_config()
        self.root.after(100, self.poll)
        self.root.after(300, self.check_focus)
        self.root.after(2000, self.keep_on_top)
        self.root.after(60000, self.check_play_time)

    def _accept_wakeups(self, lock):
        # Relancer l'application alors qu'elle tourne deja = reafficher l'overlay
        while True:
            try:
                conn, _ = lock.accept()
                conn.close()
                self.q.put(("wake", None))
            except OSError:
                return

    # --- Reglages -----------------------------------------------------------

    def apply_colors(self):
        try:
            designs.set_colors(hex_to_rgb(self.store["win_color"]), hex_to_rgb(self.store["loss_color"]))
        except ValueError:
            self.store.data.update(win_color=Store.DEFAULTS["win_color"], loss_color=Store.DEFAULTS["loss_color"])
            designs.set_colors(hex_to_rgb(self.store["win_color"]), hex_to_rgb(self.store["loss_color"]))

    def set_option(self, key, value):
        """Appele par la fenetre Parametres : enregistre et applique tout de suite."""
        if self.store[key] == value:
            return
        self.store[key] = value
        if key == "lang":
            i18n.set_lang(value)
            self._build_menu()
            for window in (self.settings_window, self.history_window):
                if window:
                    window.rebuild() if window is self.settings_window else window.build()
        elif key in ("win_color", "loss_color"):
            self.apply_colors()
            if self.history_window:
                self.history_window.build()
        elif key == "monitor":
            self.viewport = self.compute_viewport()
        elif key == "obs":
            if value:
                self.obs.start()
            else:
                self.obs.stop()
        elif key == "hotkeys":
            self.start_hotkeys() if value else self.stop_hotkeys()
        elif key == "tray":
            self.shell.set_tray(value)
            return
        elif key == "taskbar":
            self.shell.set_taskbar(value)
            return
        elif key == "auto_hide":
            self.check_focus(reschedule=False)
            return
        elif key == "discord":
            self.update_presence()
            return
        elif key in ("volume", "sounds", "summary", "summary_time", "met_alert", "tilt_alert", "resume_session",
                     "check_updates"):
            return  # pris en compte au prochain match, rien a redessiner
        self.draw()

    def start_hotkeys(self):
        if not self.hotkeys:
            self.hotkeys = Hotkeys(self.q)
            self.hotkeys.start()

    def stop_hotkeys(self):
        if self.hotkeys:
            self.hotkeys.stop()
            self.hotkeys = None

    def play_sound(self, kind):
        self.sounds.play(kind, self.store["volume"])

    def copy_obs_url(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(OBS_URL)

    def monitors(self):
        return self.screens.monitors()

    # Pour la fenetre Parametres
    version = APP_VERSION
    discord_available = bool(DISCORD_CLIENT_ID)
    startup_enabled = staticmethod(startup_enabled)
    set_startup = staticmethod(set_startup)

    def open_player(self, pid, name):
        url = tracker_url({"PrimaryId": pid, "Name": name})
        if url:
            webbrowser.open(url)

    def open_settings(self):
        if self.settings_window:
            self.settings_window.win.lift()
        else:
            self.settings_window = SettingsWindow(self)

    def open_history(self):
        if self.history_window:
            self.history_window.win.lift()
        else:
            self.history_window = HistoryWindow(self)

    # --- Position -----------------------------------------------------------

    def compute_viewport(self):
        """Zone ou s'affiche le jeu : sa fenetre (n'importe quel ecran, ultra-large, fenetre),
        sinon l'ecran choisi dans les parametres, sinon l'ecran principal."""
        monitors = self.screens.monitors()
        game = self.screens.game_rect()  # toujours chercher le jeu (sert aussi au masquage auto)
        choice = self.store["monitor"]
        if choice and choice <= len(monitors):
            return monitors[choice - 1]
        return game or monitors[0]

    def scale(self):
        # Le HUD de RL suit la hauteur de l'image du jeu ; reference : 1440p
        return self.viewport[3] / 1440

    def renderer(self):
        """(cle de position, fonction de rendu, ancre au centre de la jauge ?) du reglage actif."""
        return designs.RENDERERS[(self.store["design"], self.store["shape"])]

    def offset(self):
        # Chaque combinaison design/forme garde sa propre position
        return self.store["offsets"].get(self.renderer()[0], [0, 0])

    def screen_anchor(self):
        """Point de l'ecran ou se place l'ancre du design actif."""
        vx, vy, vw, vh = self.viewport
        r = self.scale()
        gx, gy = vx + vw - BOOST_FROM_RIGHT * r, vy + vh - BOOST_FROM_BOTTOM * r
        if not self.renderer()[2]:
            gy -= (designs.GAUGE_R + 14) * r  # juste au-dessus de la jauge
        dx, dy = self.offset()
        return gx + dx, gy + dy

    # --- Compteurs ----------------------------------------------------------

    def counts(self):
        if self.store["counter"] == "mode" and self.current_mode:
            return tuple(self.session.get(self.current_mode, (0, 0)))
        return (sum(v[0] for v in self.session.values()), sum(v[1] for v in self.session.values()))

    def total_wins(self):
        return sum(v[0] for v in self.session.values())

    def sub_label(self):
        w, l = self.counts()
        label = i18n.matches_label(w + l)
        if self.store["counter"] == "mode" and self.current_mode:
            return f"{self.current_mode.upper()} · {label}"
        return label

    # --- Dessin -------------------------------------------------------------

    def info_line(self):
        if self.banner:
            text, color, _ = self.banner
            return text, color, True
        if self.notice:
            return T(self.notice), designs.AMBER, False
        if not self.connected:
            return T("waiting"), designs.MUTED, False
        if self.streak >= 2:
            return T("streak_w", n=self.streak), designs.GREEN, False
        if self.streak <= -2:
            return T("streak_l", n=-self.streak), designs.RED, False
        goal = self.store["goal"]
        if goal:
            w = self.total_wins()
            return T("goal_progress", w=min(w, goal), goal=goal), designs.GREEN if w >= goal else designs.MUTED, False
        return None

    def draw(self):
        w, l = self.counts()
        state = {"w": w, "l": l, "info": self.info_line(), "flash": self.banner[2] if self.banner else None,
                 "sub": self.sub_label()}
        k = self.scale() * float(self.store["size"])
        render = self.renderer()[1]
        img, (ax, ay), buttons = render(state, k, hover=self.hover)
        self._base = (img, ax, ay, buttons)
        self.present()
        self.publish(state)
        self.shell.set_tip(T("tray_tip", w=w, l=l))

    def publish(self, state):
        """Etat envoye a la page OBS."""
        if not self.store["obs"]:
            return
        info = state["info"]
        goal = self.store["goal"]
        w, l = state["w"], state["l"]
        self.obs.update({
            "w": w, "l": l, "pct": round(w * 100 / (w + l)) if w + l else 0, "sub": state["sub"],
            "info": {"text": info[0], "color": rgb_hex(info[1]), "filled": info[2]} if info else None,
            "goal": {"w": self.total_wins(), "goal": goal} if goal else None,
            "win_color": self.store["win_color"], "loss_color": self.store["loss_color"], "flash": state["flash"],
            "event": {"id": self.event_id, "kind": self.event_kind} if self.event_id else None,
            "animations": self.store["animations"],
        })

    def present(self):
        """Affiche le dernier rendu, avec l'animation de fin de match par-dessus s'il y en a une."""
        img, ax, ay, buttons = self._base
        if self.hidden or self.auto_hidden:
            img, ax, ay, buttons = empty_image(), 0, 0, {}
        elif self.anim:
            img, (px, py) = self.anim.frame(img)
            ax, ay = ax + px, ay + py
            buttons = {key: (x0 + px, y0 + py, x1 + px, y1 + py) for key, (x0, y0, x1, y1) in buttons.items()}
        opacity = self.store["opacity"]
        if opacity < 100 and not self.hidden:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: v * opacity // 100))
        sx, sy = self.screen_anchor()
        x, y = round(sx - ax), round(sy - ay)
        self.buttons = buttons
        self.pos = (x, y)
        geom = f"{img.width}x{img.height}+{x}+{y}"
        if geom != self._geom:
            self.root.geometry(geom)
            self._geom = geom
        self.layer.show(img, x, y)

    def refresh(self):
        self.draw()

    def play_animation(self, kind):
        self.anim = designs.MatchAnimation(kind, self.scale() * float(self.store["size"]))
        if not self._anim_job:
            self._anim_tick()

    def _anim_tick(self):
        self._anim_job = None
        try:
            if self.anim and self.anim.done():
                self.anim = None
            if not self._dragging:  # pendant un glisser, la fenetre suit la souris
                self.present()
        except Exception as e:  # une animation ratee ne doit pas bloquer l'overlay
            log(f"Erreur d'animation: {e!r}")
            self.anim = None
            self.present()
        if self.anim:
            self._anim_job = self.root.after(33, self._anim_tick)

    def show_banner(self, text, color, side, seconds=5):
        self.banner = (text, color, side)
        self.draw()
        if self._banner_job:
            self.root.after_cancel(self._banner_job)
        self._banner_job = self.root.after(int(seconds * 1000), self.clear_banner)

    def clear_banner(self):
        self.banner = None
        self._banner_job = None
        if self.banner_queue:
            self.show_banner(*self.banner_queue.pop(0))
        else:
            self.draw()

    def queue_banner(self, text, color, side=None, seconds=5):
        """Bandeau affiche apres ceux en cours (trophees, records, pause...)."""
        if self.banner:
            self.banner_queue.append((text, color, side, seconds))
        else:
            self.show_banner(text, color, side, seconds)

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.card.hide()
        else:
            self.grace_until = time.monotonic() + 5  # reafficher meme si le jeu n'est pas au premier plan
            self.auto_hidden = False
        self.draw()

    def game_in_focus(self):
        """Vrai si le jeu ou une fenetre de l'app (menu, parametres...) est au premier plan,
        None quand on ne peut pas trancher (l'overlay lui-meme vient d'etre clique, transition...)."""
        u = ctypes.windll.user32
        u.GetForegroundWindow.restype = ctypes.c_void_p
        u.GetAncestor.restype = ctypes.c_void_p
        u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        fg = u.GetForegroundWindow()
        if not fg or fg in (self.layer.hwnd, self.card.layer.hwnd, self.shell.hwnd):
            return None
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(ctypes.c_void_p(fg), ctypes.byref(pid))
        if pid.value == os.getpid():
            return True
        game = self.screens.game_hwnd
        return bool(game) and (fg == game or u.GetAncestor(fg, 2) == game)  # GA_ROOT

    def check_focus(self, reschedule=True):
        focus = self.game_in_focus()
        if not self.store["auto_hide"] or self._dragging or time.monotonic() < self.grace_until:
            hide = False
        elif focus is None:
            hide = self.auto_hidden  # on ne peut pas trancher : rien ne change
        else:
            hide = not focus
        if hide != self.auto_hidden:
            self.auto_hidden = hide
            if hide:
                self.card.hide()
            self.present()
        if reschedule:
            self.root.after(300, self.check_focus)

    # --- Session ------------------------------------------------------------

    def restore_session(self):
        saved = self.store["session_saved"]
        if (self.store["resume_session"] and saved.get("modes")
                and time.time() - saved.get("last", 0) < RESUME_HOURS * 3600):
            self.session = {m: list(v) for m, v in saved["modes"].items()}
            self.streak = saved.get("streak", 0)
            self.current_mode = saved.get("mode")
            self.session_start = saved.get("start")
            log("Session reprise")

    def save_session(self):
        self.store["session_saved"] = {"modes": self.session, "streak": self.streak, "mode": self.current_mode,
                                       "start": self.session_start, "last": time.time()}

    def session_matches(self):
        return [m for m in self.history.matches if self.session_start and m["t"] > self.session_start]

    def check_play_time(self):
        """Alerte pause toutes les 2 h de jeu (si l'alerte tilt est activee)."""
        if self.session_start and self.store["tilt_alert"]:
            hours = int((time.time() - self.session_start) // 3600)
            if hours >= 2 and hours > self.break_hours:
                self.break_hours = hours
                self.queue_banner(T("tilt_time", h=hours), designs.AMBER, None, 8)
        self.root.after(60000, self.check_play_time)

    def update_presence(self):
        """Statut Discord : mode, score de la session, serie."""
        if not DISCORD_CLIENT_ID:
            return
        w, l = self.counts()
        mode = f"{self.current_mode} · " if self.current_mode and self.store["counter"] == "mode" else ""
        if self.streak >= 2:
            state = T("dc_streak", n=self.streak)
        elif w + l:
            state = T("dc_games", n=sum(sum(v) for v in self.session.values()))
        else:
            state = T("dc_waiting")
        activity = {
            "details": T("dc_details", mode=mode, w=w, l=l, p=round(w * 100 / (w + l)) if w + l else 0),
            "state": state,
            "assets": {"large_image": "logo", "large_text": f"RL Overlay {APP_VERSION}"},
            "buttons": [{"label": T("dc_button"), "url": REPO_URL}],
        }
        if self.session_start:
            activity["timestamps"] = {"start": int(self.session_start)}
        self.discord.update(activity, self.store["discord"] and self.connected)

    def share_card(self):
        """Copie une image de la session dans le presse-papiers."""
        matches = self.session_matches()
        me = [m.get("me") or {} for m in matches if not m.get("forfeit")]
        w = sum(v[0] for v in self.session.values())
        l = sum(v[1] for v in self.session.values())
        minutes = round((time.time() - self.session_start) / 60) if self.session_start else 0
        fmt = "%d/%m/%Y" if i18n.lang() == "fr" else "%Y-%m-%d"
        info = {"w": w, "l": l, "modes": self.session,
                "best_streak": History.summary(matches)["best_streak"] if matches else max(self.streak, 0),
                "mvp": sum(1 for x in me if x.get("mvp")), "goals": sum(x.get("goals", 0) for x in me),
                "assists": sum(x.get("assists", 0) for x in me), "saves": sum(x.get("saves", 0) for x in me),
                "fastest": max((x.get("fastest", 0) for x in me), default=0), "minutes": minutes,
                "date": time.strftime(fmt)}
        img = designs.render_session_card(info, T)
        if copy_image_to_clipboard(img, self.layer.hwnd):
            self.show_banner(T("card_copied"), designs.GREEN, None, 3)
        return img

    # --- Resume de match ----------------------------------------------------

    def show_summary(self, info=None):
        info = info or self.last_summary
        if not info or self.hidden:
            return
        k = self.scale() * float(self.store["size"])
        img = designs.render_summary(info, k, T)
        base, ax, ay, _ = self._base
        sx, sy = self.screen_anchor()
        left, top = sx - ax, sy - ay
        vx, vy, vw, vh = self.viewport
        x = round(min(max(left + base.width / 2 - img.width / 2, vx), vx + vw - img.width))
        y = round(max(top + 20 * k - img.height, vy))
        self.card.show(img, x, y, self.store["summary_time"])

    # --- Menu ---------------------------------------------------------------

    def _build_menu(self):
        if getattr(self, "menu", None):
            self.menu.destroy()
        m = tk.Menu(self.root, tearoff=0)
        if self.update_info:
            version, url = self.update_info
            m.add_command(label=T("m_update", v=version), command=lambda: webbrowser.open(url))
            m.add_separator()
        self.players_menu = tk.Menu(m, tearoff=0)
        m.add_cascade(label=T("m_players"), menu=self.players_menu)
        m.add_command(label=T("m_history"), command=self.open_history)
        m.add_command(label=T("m_settings"), command=self.open_settings)
        m.add_command(label=T("m_last_summary"), command=lambda: self.show_summary())
        m.add_command(label=T("m_share"), command=self.share_card)
        m.add_separator()
        m.add_command(label=T("m_reset"), command=self.reset_session)
        m.add_command(label=T("m_win_plus"), command=lambda: self.adjust(1, 0))
        m.add_command(label=T("m_win_minus"), command=lambda: self.adjust(-1, 0))
        m.add_command(label=T("m_loss_plus"), command=lambda: self.adjust(0, 1))
        m.add_command(label=T("m_loss_minus"), command=lambda: self.adjust(0, -1))
        m.add_separator()
        design_menu = tk.Menu(m, tearoff=0)
        self.design_var = tk.StringVar(value=self.store["design"])
        for key in designs.STYLES:
            design_menu.add_radiobutton(label=T(f"style_{key}"), value=key, variable=self.design_var,
                                        command=lambda k=key: self.set_design(k))
        m.add_cascade(label=T("m_design"), menu=design_menu)
        shape_menu = tk.Menu(m, tearoff=0)
        self.shape_var = tk.StringVar(value=self.store["shape"])
        for key in designs.SHAPES:
            shape_menu.add_radiobutton(label=T(f"shape_{key}"), value=key, variable=self.shape_var,
                                       command=lambda k=key: self.set_shape(k))
        m.add_cascade(label=T("m_shape"), menu=shape_menu)
        size_menu = tk.Menu(m, tearoff=0)
        for value, label in SIZES.items():
            size_menu.add_command(label=label, command=lambda v=value: self.set_size(v))
        m.add_cascade(label=T("m_size"), menu=size_menu)
        preview_menu = tk.Menu(m, tearoff=0)
        preview_menu.add_command(label=T("m_victory"), command=lambda: self.celebrate(True, preview=True))
        preview_menu.add_command(label=T("m_defeat"), command=lambda: self.celebrate(False, preview=True))
        m.add_cascade(label=T("m_preview"), menu=preview_menu)
        m.add_command(label=T("m_replace"), command=self.reset_position)
        m.add_command(label=T("m_name"), command=self.edit_name)
        m.add_separator()
        m.add_command(label=T("m_hide"), command=self.toggle_hidden)
        m.add_command(label=T("m_quit"), command=self.quit)
        self.menu = m

    def set_size(self, value):
        self.store["size"] = value
        self.draw()

    def set_shape(self, key):
        self.store["shape"] = key
        self.draw()

    def set_design(self, key):
        self.store["design"] = key
        self.draw()

    def reset_position(self):
        self.store.data["size"] = 1.0
        self.store["offsets"].pop(self.renderer()[0], None)
        self.store.save()
        self.draw()

    # --- Evenements ---------------------------------------------------------

    def poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "status":
                    if payload != self.connected:
                        self.connected = payload
                        if payload:
                            self.notice = None
                        self.refresh()
                        self.update_presence()
                elif kind == "update":
                    self.update_info = payload
                    log(f"Mise a jour disponible : {payload[0]}")
                    self._build_menu()
                    self.queue_banner(T("update_banner", v=payload[0]), designs.SKY, None, 8)
                elif kind == "hotkey":
                    self.toggle_hidden() if payload == "toggle" else self.reset_session()
                elif kind == "wake":
                    if self.hidden:
                        self.toggle_hidden()
                    self.grace_until = time.monotonic() + 8
                    self.check_focus(reschedule=False)
                elif kind == "shell":
                    self.toggle_hidden() if payload == "toggle" else self.quit()
                    if payload == "quit":
                        return
                elif kind == "shell_menu":
                    self.show_menu_at(*payload, from_tray=True)
                else:
                    try:
                        self.tracker.handle(*payload)
                    except Exception as e:  # ne jamais tuer l'overlay sur un message inattendu
                        log(f"Erreur sur {payload[0]}: {e!r}")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def on_hover(self, e=None):
        # Les zones transparentes ne recoivent pas la souris : on verifie la
        # position reelle du curseur par rapport au rectangle de la fenetre.
        self.root.after(80, self.update_hover)

    def update_hover(self):
        # Pas de re-dessin pendant le glisser, ni quand un menu est ouvert
        # (la souris part vers un sous-menu : l'overlay ne doit pas bouger)
        if self._dragging or getattr(self, "_behind", False):
            return
        px, py = self.root.winfo_pointerxy()
        x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
        inside = x <= px < x + self.root.winfo_width() and y <= py < y + self.root.winfo_height()
        if inside != self.hover:
            self.hover = inside
            self.draw()
        if self.hover:
            self.root.after(250, self.update_hover)

    def check_config(self):
        # Le jeu peut regenerer sa config (mise a jour, autre launcher) : on reverifie
        # tant qu'on n'est pas connecte.
        if not self.connected and ensure_stats_api_enabled() and rocket_league_running():
            self.notice = "restart_rl"
            self.refresh()
        self.root.after(15000, self.check_config)

    def keep_on_top(self):
        if not getattr(self, "_behind", False):
            self.root.attributes("-topmost", True)
            self.root.lift()
        # Le jeu a pu changer d'ecran, de resolution ou de mode fenetre
        viewport = self.compute_viewport()
        if viewport != self.viewport and not self._dragging:
            self.viewport = viewport
            self.draw()
        self.root.after(2000, self.keep_on_top)

    @contextlib.contextmanager
    def behind(self):
        """Laisse passer devant un menu ou une fenetre de dialogue le temps qu'il est ouvert."""
        self._behind = True
        self.root.attributes("-topmost", False)
        try:
            yield
        finally:
            self._behind = False
            self.root.attributes("-topmost", True)
            self.root.lift()

    def on_match_start(self, tracker):
        """Premier coup d'envoi d'un match en ligne : mode connu, joueurs deja croises."""
        if tracker.mode and tracker.mode != self.current_mode:
            self.current_mode = tracker.mode
            self.refresh()
        if not self.store["met_alert"]:
            return
        best = None
        for pid, name, _ in tracker.others():
            p = self.history.met(pid)
            if p and (best is None or p["n"] > best[1]["n"]):
                best = (name, p)
        if best:
            name, p = best
            self.show_banner(T("met_before", name=short_name(name, 12), w=p["with"][0] + p["against"][0],
                               l=p["with"][1] + p["against"][1]), designs.AMBER, None)

    def add_result(self, won, info):
        mode = info.get("mode") or "?"
        self.current_mode = info.get("mode") or self.current_mode
        bucket = self.session.setdefault(mode, [0, 0])
        bucket[0 if won else 1] += 1
        if won:
            self.streak = self.streak + 1 if self.streak > 0 else 1
        else:
            self.streak = self.streak - 1 if self.streak < 0 else -1
        if not self.session_start:
            self.session_start = info.get("start") or info["t"]
        self.save_session()
        records_before = achievements.records(self.history.matches) if len(self.history.matches) >= 5 else {}
        self.history.add(info)
        self.last_summary = info
        self.celebrate(won)
        if self.store["summary"]:
            self.root.after(1500, lambda: self.show_summary(info))

        # Bandeaux qui suivent celui du resultat
        goal = self.store["goal"]
        if won and goal and self.total_wins() == goal:
            self.queue_banner(T("goal_reached"), designs.GOLD, "w")
        # Au plus 1 record et 2 trophees annonces par match (le reste est dans l'onglet Trophees)
        lang = i18n.lang()
        records_after = achievements.records(self.history.matches)
        broken = achievements.broken_records(records_before, records_after)
        if broken:
            entry = next(r for r in achievements.RECORDS if r[0] == broken[0])
            self.queue_banner(T("record_banner", name=achievements.label(entry, lang).upper(),
                                v=entry[3].format(records_after[broken[0]][0])), designs.GOLD, None, 4)
        unlocked = achievements.unlocked(self.history.matches)
        new = [e for e in achievements.ACHIEVEMENTS if e[0] in unlocked and e[0] not in self.store["achievements"]]
        for entry in new:
            self.store["achievements"][entry[0]] = time.time()
            log(f"Trophee : {entry[0]}")
        for entry in new[:2]:
            self.queue_banner(T("trophy_banner", name=achievements.label(entry, lang).upper()), designs.GOLD, "w", 5)
        if len(new) > 2:
            self.queue_banner(T("trophy_more", n=len(new) - 2), designs.GOLD, None, 4)
        self.store.save()
        if not won and self.store["tilt_alert"] and self.streak in (-3, -5, -7):
            self.queue_banner(T("tilt_losses", n=-self.streak), designs.AMBER, None, 7)
        self.update_presence()
        if self.history_window:
            self.history_window.refresh()

    def celebrate(self, won, preview=False):
        kind = "w" if won else "l"
        self.event_id += 1
        self.event_kind = kind
        self.show_banner(T("win_banner" if won else "loss_banner"), designs.GREEN if won else designs.RED, kind)
        if self.store["animations"]:
            self.play_animation(kind)
        if self.store["sounds"]:
            self.play_sound(kind)

    def adjust(self, dw, dl):
        bucket = self.session.setdefault(
            self.current_mode if self.store["counter"] == "mode" and self.current_mode else "?", [0, 0])
        if dw < 0 and bucket[0] == 0 or dl < 0 and bucket[1] == 0:
            # Rien a retirer dans ce mode : on retire dans un autre mode qui en a
            idx = 0 if dw < 0 else 1
            bucket = next((v for v in self.session.values() if v[idx] > 0), bucket)
        bucket[0] = max(0, bucket[0] + dw)
        bucket[1] = max(0, bucket[1] + dl)
        if dw > 0:
            self.streak = self.streak + 1 if self.streak > 0 else 1
        elif dl > 0:
            self.streak = self.streak - 1 if self.streak < 0 else -1
        else:
            self.streak = 0
        self.save_session()
        self.update_presence()
        self.refresh()

    def reset_session(self):
        self.session = {}
        self.streak = 0
        self.session_start = None
        self.break_hours = 0
        self.save_session()
        self.update_presence()
        self.refresh()

    def edit_name(self):
        hint = self.store["detected_name"]
        prompt = T("name_prompt")
        if hint:
            prompt += "\n" + T("name_detected", name=hint)
        with self.behind():
            val = simpledialog.askstring(T("name_title"), prompt, initialvalue=self.store["player_name"],
                                         parent=self.root)
        if val is not None:
            self.store["player_name"] = val.strip()

    # --- Clic et deplacement ------------------------------------------------

    def on_press(self, e):
        for key, (x0, y0, x1, y1) in self.buttons.items():
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                {"w+": lambda: self.adjust(1, 0), "w-": lambda: self.adjust(-1, 0),
                 "l+": lambda: self.adjust(0, 1), "l-": lambda: self.adjust(0, -1),
                 "quit": self.quit}[key]()
                return
        self._dragging = True
        self._start = (e.x_root, e.y_root)

    def drag_delta(self, e):
        return e.x_root - self._start[0], e.y_root - self._start[1]

    def drag_move(self, e):
        # On deplace l'image deja rendue (pas de re-dessin pendant le glisser)
        if self._dragging:
            dx, dy = self.drag_delta(e)
            self.root.geometry(f"+{self.pos[0] + dx}+{self.pos[1] + dy}")
            self._geom = None

    def drag_end(self, e):
        if self._dragging:
            self._dragging = False
            dx, dy = self.drag_delta(e)
            ox, oy = self.offset()
            self.store["offsets"][self.renderer()[0]] = [ox + dx, oy + dy]
            self.store.save()
            self.draw()

    def fill_players_menu(self):
        pm = self.players_menu
        pm.delete(0, "end")
        players = self.tracker.last_players
        if not players:
            pm.add_command(label=T("m_no_game"), state="disabled")
            return
        me = (self.store["player_name"] or self.store["detected_name"]).strip().lower()
        for team, team_label in ((0, T("m_blue")), (1, T("m_orange"))):
            members = [p for p in players if p.get("TeamNum") == team]
            if not members:
                continue
            if pm.index("end") is not None:
                pm.add_separator()
            pm.add_command(label=team_label, state="disabled")
            for p in sorted(members, key=lambda p: -int(p.get("Score") or 0)):
                name = p.get("Name") or "?"
                is_me = name.strip().lower() == me
                label = f"   {name}" + (f"  {T('m_you')}" if is_me else "")
                pid = self.tracker.player_id(p)
                met = self.history.met(pid) if pid and not is_me else None
                if met:
                    label += "   · " + T("m_met", n=met["n"], w=met["with"][0] + met["against"][0],
                                         l=met["with"][1] + met["against"][1])
                url = tracker_url({"PrimaryId": pid or p.get("PrimaryId"), "Name": name})
                if url:
                    pm.add_command(label=label, command=lambda u=url: webbrowser.open(u))
                else:
                    pm.add_command(label=f"{label}  {T('m_bot')}", state="disabled")

    def show_menu(self, e):
        self.show_menu_at(e.x_root, e.y_root)

    def show_menu_at(self, x, y, from_tray=False):
        self.fill_players_menu()
        if from_tray:
            # Sans fenetre au premier plan, le menu ne se fermerait pas en cliquant a cote
            self.layer.u.SetForegroundWindow.argtypes = [ctypes.c_void_p]
            self.layer.u.SetForegroundWindow(self.layer.hwnd)
        # Sous Windows, tk_popup ne rend la main qu'une fois le menu ferme
        with self.behind():
            try:
                self.menu.tk_popup(x, y)
            finally:
                self.menu.grab_release()

    def quit(self):
        self.store.save()
        self.stop_hotkeys()
        self.obs.stop()
        self.shell.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    if not getattr(sys, "frozen", False):
        # Lance via pythonw : sans identifiant propre, Windows grouperait le bouton de la
        # barre des taches avec Python (et son logo). L'exe, lui, est groupe avec son icone.
        with contextlib.suppress(AttributeError, OSError):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RLOverlay.App")
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
        lock.listen(2)
    except OSError:
        # Deja lance : on demande a l'instance en cours de se reafficher
        with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", LOCK_PORT), timeout=1):
            pass
        return
    try:
        Overlay(lock).run()
    except Exception as e:
        log(f"Crash: {e!r}")
        raise


if __name__ == "__main__":
    main()
