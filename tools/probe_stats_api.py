"""Enregistre tout ce que la Stats API envoie, pour voir ce que le jeu donne hors match.

Sert a preparer le defi d'engagements en entrainement personnalise : y a-t-il un RoundStarted a
chaque tir ? Le jeu envoie-t-il la vitesse de la voiture, et dans quelle unite ? A quelle frequence ?

Fermer RL Stats avant (le jeu n'accepte peut-etre qu'un client), lancer Rocket League, puis :
  .venv\\Scripts\\python.exe tools\\probe_stats_api.py --seconds 240
et pendant ce temps : quelques tirs d'un pack d'engagements en entrainement personnalise, puis un
peu d'entrainement libre. Resultat : %TEMP%\\rl_stats_probe.jsonl (brut) et rl_stats_probe.txt (resume).
"""

import argparse
import codecs
import importlib.machinery
import importlib.util
import json
import os
import socket
import sys
import tempfile
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(tempfile.gettempdir(), "rl_stats_probe")


def load_app():
    loader = importlib.machinery.SourceFileLoader("rl_stats_probe", os.path.join(ROOT, "rl_stats.pyw"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    rl = importlib.util.module_from_spec(spec)
    loader.exec_module(rl)
    return rl


def record(rl, seconds):
    """Messages [(t, event, data)] recus pendant `seconds` secondes, ecrits au fur et a mesure."""
    messages = []
    end = time.perf_counter() + seconds
    with open(OUT + ".jsonl", "w", encoding="utf-8") as raw_file:
        while time.perf_counter() < end:
            try:
                with socket.create_connection((rl.API_HOST, rl.API_PORT), timeout=3) as sock:
                    print("Connecte a Rocket League, enregistrement...")
                    sock.settimeout(1)
                    stream = rl.JsonStream()
                    decoder = codecs.getincrementaldecoder("utf-8")("replace")
                    while time.perf_counter() < end:
                        try:
                            chunk = sock.recv(65536)
                        except socket.timeout:
                            continue
                        if not chunk:
                            break
                        now = time.perf_counter()
                        for raw in stream.feed(decoder.decode(chunk)):
                            event, data = rl.parse_message(raw)
                            if event:
                                messages.append((now, event, data))
                                raw_file.write(json.dumps({"t": now, "event": event, "data": data},
                                                          ensure_ascii=False) + "\n")
            except OSError:
                print("Jeu introuvable (Rocket League lance ? Stats API active ?), nouvel essai dans 3 s")
                time.sleep(3)
    return messages


def summary(messages):
    lines = []
    if not messages:
        return ["Aucun message recu."]
    t0 = messages[0][0]
    counts = Counter(e for _, e, _ in messages)
    lines.append("Evenements : " + ", ".join(f"{e} x{n}" for e, n in counts.most_common()))
    states = [(t, d) for t, e, d in messages if e == "UpdateState"]
    if len(states) > 1:
        lines.append(f"UpdateState : {len(states) / (states[-1][0] - states[0][0]):.1f} par seconde")
    player_keys, game_keys, ball_keys = Counter(), Counter(), Counter()
    for _, d in states:
        for p in d.get("Players") or []:
            player_keys.update(p.keys())
        game = d.get("Game") or {}
        game_keys.update(game.keys())
        ball_keys.update((game.get("Ball") or {}).keys())
    lines.append("Champs des joueurs : " + ", ".join(f"{k} ({n})" for k, n in player_keys.most_common()))
    lines.append("Champs de Game : " + ", ".join(game_keys))
    lines.append("Champs du ballon : " + ", ".join(ball_keys))
    examples = [p for _, d in states for p in d.get("Players") or [] if "Boost" in p]
    if examples:
        lines.append("Exemple de joueur : " + json.dumps(examples[len(examples) // 2], ensure_ascii=False))
        speeds = [p["Speed"] for p in examples if isinstance(p.get("Speed"), (int, float))]
        if speeds:
            lines.append(f"Speed : min {min(speeds):.1f}, max {max(speeds):.1f}")

    lines.append("")
    lines.append("Chronologie (hors UpdateState et horloge) :")
    for t, e, d in messages:
        if e in ("UpdateState", "ClockUpdatedSeconds"):
            continue
        detail = ""
        if e == "BallHit":
            detail = " ".join(p.get("Name", "?") for p in d.get("Players") or [])
        lines.append(f"  {t - t0:8.3f}  {e} {detail}")

    lines.append("")
    lines.append("Apres chaque RoundStarted : premier mouvement de la voiture et premier contact")
    for i, (t, e, _) in enumerate(messages):
        if e != "RoundStarted":
            continue
        moved = hit = None
        for t2, e2, d2 in messages[i + 1:]:
            if e2 == "RoundStarted":
                break
            if e2 == "UpdateState" and moved is None:
                me = next((p for p in d2.get("Players") or [] if "Boost" in p), None)
                if me and (me.get("Speed") or 0) > 1:
                    moved = t2
            if e2 == "BallHit" and hit is None:
                hit = t2
        lines.append(f"  RoundStarted a {t - t0:.3f} : mouvement {'+%.3f s' % (moved - t) if moved else '-'}, "
                     f"contact {'+%.3f s' % (hit - t) if hit else '-'}")
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=240)
    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")  # pseudos avec des symboles : la console Windows ne les a pas tous
    rl = load_app()
    print(f"Enregistrement pendant {args.seconds:.0f} s : {OUT}.jsonl")
    messages = record(rl, args.seconds)
    text = "\n".join(summary(messages))
    with open(OUT + ".txt", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\nResume : {OUT}.txt")


if __name__ == "__main__":
    main()
