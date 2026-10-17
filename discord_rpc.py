"""Statut Discord (Rich Presence) via le canal local de l'application Discord.

Protocole : paquets [opcode u32][longueur u32][JSON] sur \\\\.\\pipe\\discord-ipc-N.
Opcode 0 = poignee de main, 1 = commande. Necessite un "Application ID" cree sur
https://discord.com/developers/applications (le nom de l'application est affiche
dans "Joue a ...", l'image "logo" dans Rich Presence > Art Assets).
"""

import json
import os
import struct
import threading
import time
import uuid

MIN_INTERVAL = 5  # Discord limite a 5 mises a jour / 20 s


class DiscordPresence(threading.Thread):
    def __init__(self, client_id, log=print):
        super().__init__(daemon=True)
        self.client_id = client_id
        self.log = log
        self.enabled = False
        self.activity = None
        self.sent = object()  # derniere activite envoyee (valeur impossible au depart)
        self.wake = threading.Event()
        self.pipe = None

    def update(self, activity, enabled):
        self.activity = activity
        self.enabled = enabled
        self.wake.set()

    def _send(self, op, payload):
        data = json.dumps(payload).encode("utf-8")
        self.pipe.write(struct.pack("<II", op, len(data)) + data)
        self.pipe.flush()
        header = self.pipe.read(8)
        if len(header) < 8:
            raise OSError("Discord a ferme la connexion")
        _, length = struct.unpack("<II", header)
        return json.loads(self.pipe.read(length) or b"{}")

    def _connect(self):
        for i in range(10):
            try:
                self.pipe = open(rf"\\.\pipe\discord-ipc-{i}", "r+b", buffering=0)
                break
            except OSError:
                continue
        else:
            return False
        reply = self._send(0, {"v": 1, "client_id": self.client_id})
        if reply.get("evt") != "READY":
            raise OSError(f"Discord a refuse la connexion : {reply.get('data')}")
        self.log("Discord connecte")
        self.sent = object()
        return True

    def _close(self):
        if self.pipe:
            try:
                self.pipe.close()
            except OSError:
                pass
        self.pipe = None

    def run(self):
        last_send = 0.0
        while True:
            self.wake.wait(15)
            self.wake.clear()
            wanted = self.activity if self.enabled else None
            if not self.pipe and not self.enabled:
                continue
            try:
                if not self.pipe and not self._connect():
                    continue  # Discord n'est pas lance : on reessaie plus tard
                if wanted == self.sent:
                    continue
                pause = MIN_INTERVAL - (time.monotonic() - last_send)
                if pause > 0:
                    time.sleep(pause)
                    wanted = self.activity if self.enabled else None
                args = {"pid": os.getpid()}
                if wanted:
                    args["activity"] = wanted
                self._send(1, {"cmd": "SET_ACTIVITY", "args": args, "nonce": str(uuid.uuid4())})
                self.sent = wanted
                last_send = time.monotonic()
                if not self.enabled:
                    self._close()  # statut efface : on libere Discord
            except (OSError, ValueError) as e:
                self.log(f"Discord : {e}")
                self._close()
