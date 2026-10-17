"""Mode streamer : petite page web locale a ajouter dans OBS comme "source navigateur".

http://127.0.0.1:49124/ affiche le compteur ; la page relit /state chaque seconde.
Le serveur n'ecoute que sur 127.0.0.1 (invisible depuis le reseau).
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OBS_PORT = 49124
OBS_URL = f"http://127.0.0.1:{OBS_PORT}/"

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>RL Overlay</title>
<style>
  :root { --win: #2ee66b; --loss: #ff4d4d; --panel: rgba(11,19,34,.92); --mid: rgba(20,31,54,.92);
          --edge: #344666; --fg: #f1f5f9; --muted: #8c98ad; --amber: #f59e0b; }
  html, body { margin: 0; background: transparent; overflow: hidden; }
  body { font-family: Bahnschrift, "Segoe UI", sans-serif; font-weight: 600; font-stretch: 75%;
         color: var(--fg); display: flex; justify-content: center; padding-top: 40px; }
  #wrap { position: relative; width: 420px; }
  #board { display: grid; grid-template-columns: 1fr 1.2fr 1fr; gap: 4px; height: 70px; position: relative; z-index: 1; }
  .side { background: var(--panel); border: 1.5px solid var(--edge); display: flex; align-items: center;
          justify-content: center; gap: 12px; position: relative; transition: background .4s; }
  .side::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 5px; }
  #win { clip-path: polygon(0 0, 100% 0, 100% 100%, 18px 100%); }
  #loss { clip-path: polygon(0 0, 100% 0, calc(100% - 18px) 100%, 0 100%); }
  #win::before { background: var(--win); }  #loss::before { background: var(--loss); }
  .tag { font-size: 22px; font-style: italic; }  #win .tag { color: var(--win); }  #loss .tag { color: var(--loss); }
  .num { font-size: 46px; font-style: italic; font-variant-numeric: tabular-nums; }
  #mid { background: var(--mid); border: 1.5px solid var(--edge); display: flex; flex-direction: column;
         align-items: center; justify-content: center; }
  #pct { font-size: 32px; font-style: italic; line-height: 1; }
  #sub { font-size: 14px; color: var(--muted); letter-spacing: .04em; margin-top: 4px; }
  #info { margin: 5px auto 0; width: 62%; text-align: center; font-size: 16px; padding: 3px 0;
          clip-path: polygon(0 0, 100% 0, calc(100% - 10px) 100%, 10px 100%); visibility: hidden; }
  #goal { margin: 6px auto 0; width: 62%; height: 8px; background: var(--panel); border: 1px solid var(--edge);
          border-radius: 4px; overflow: hidden; visibility: hidden; }
  #goal div { height: 100%; background: var(--win); border-radius: 4px; transition: width .6s; }
  #fx { position: absolute; left: -90px; top: -40px; width: 600px; height: 260px; pointer-events: none; z-index: 2; }
  .glow-w #board { filter: drop-shadow(0 0 14px var(--win)); }
  .glow-l #board { filter: drop-shadow(0 0 14px var(--loss)); }
  .pop { animation: pop .7s cubic-bezier(.3,1.6,.5,1); }
  .shake { animation: shake .6s; }
  @keyframes pop { 0% { transform: scale(1); } 35% { transform: scale(1.12); } 100% { transform: scale(1); } }
  @keyframes shake { 0%,100% { transform: translateX(0); } 15% { transform: translateX(-9px); }
                     30% { transform: translateX(8px); } 45% { transform: translateX(-6px); }
                     60% { transform: translateX(4px); } 75% { transform: translateX(-2px); } }
</style></head>
<body>
<div id="wrap">
  <div id="board">
    <div class="side" id="win"><span class="tag">W</span><span class="num" id="w">0</span></div>
    <div id="mid"><div id="pct">0%</div><div id="sub"></div></div>
    <div class="side" id="loss"><span class="num" id="l">0</span><span class="tag">L</span></div>
  </div>
  <div id="info"></div>
  <div id="goal"><div></div></div>
  <canvas id="fx" width="600" height="260"></canvas>
</div>
<script>
const $ = id => document.getElementById(id);
let lastEvent = null, particles = [], raf = null;

function burst(kind) {
  const css = getComputedStyle(document.documentElement);
  const win = css.getPropertyValue("--win").trim(), loss = css.getPropertyValue("--loss").trim();
  const colors = kind === "w" ? [win, "#facc15", "#f1f5f9", "#38bdf8"] : [loss, "#991b1b", "#475569"];
  for (let i = 0; i < (kind === "w" ? 80 : 30); i++) {
    const a = kind === "w" ? (Math.random() * 130 + 25) * Math.PI / 180 : Math.random() * Math.PI;
    const v = kind === "w" ? 4 + Math.random() * 6 : Math.random() * 2;
    particles.push({ x: 300 + (Math.random() - .5) * 260, y: kind === "w" ? 80 : 110,
      vx: Math.cos(a) * v, vy: kind === "w" ? -Math.sin(a) * v : -Math.random() * 2,
      r: Math.random() * 6, s: (Math.random() - .5) * .3, c: colors[i % colors.length],
      w: 4 + Math.random() * 5, h: 2 + Math.random() * 3, life: 1, tri: kind !== "w" });
  }
  if (!raf) raf = requestAnimationFrame(step);
}

function step() {
  const ctx = $("fx").getContext("2d");
  ctx.clearRect(0, 0, 600, 260);
  particles = particles.filter(p => p.life > 0 && p.y < 280);
  for (const p of particles) {
    p.vy += p.tri ? .18 : .14; p.vx *= .985; p.x += p.vx; p.y += p.vy; p.r += p.s; p.life -= .006;
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.globalAlpha = Math.min(1, p.life * 3);
    ctx.fillStyle = p.c; ctx.beginPath();
    if (p.tri) { ctx.moveTo(0, -p.w); ctx.lineTo(p.w * .8, p.h); ctx.lineTo(-p.w * .6, p.h * .7); }
    else ctx.rect(-p.w / 2, -p.h / 2, p.w, p.h);
    ctx.fill(); ctx.restore();
  }
  raf = particles.length ? requestAnimationFrame(step) : null;
}

function play(kind) {
  const wrap = $("wrap");
  wrap.classList.remove("pop", "shake", "glow-w", "glow-l");
  void wrap.offsetWidth;  // relance l'animation CSS
  wrap.classList.add(kind === "w" ? "pop" : "shake", "glow-" + kind);
  setTimeout(() => wrap.classList.remove("glow-" + kind), 2600);
  burst(kind);
}

async function refresh() {
  try {
    const s = await (await fetch("/state", { cache: "no-store" })).json();
    const root = document.documentElement.style;
    root.setProperty("--win", s.win_color); root.setProperty("--loss", s.loss_color);
    $("w").textContent = s.w; $("l").textContent = s.l; $("pct").textContent = s.pct + "%";
    $("sub").textContent = s.sub;
    const info = $("info");
    if (s.info) {
      info.textContent = s.info.text; info.style.visibility = "visible";
      info.style.background = s.info.filled ? s.info.color : "var(--panel)";
      info.style.color = s.info.filled ? "#0b1322" : s.info.color;
    } else info.style.visibility = "hidden";
    const goal = $("goal");
    goal.style.visibility = s.goal ? "visible" : "hidden";
    if (s.goal) goal.firstElementChild.style.width = Math.min(100, s.goal.w * 100 / s.goal.goal) + "%";
    $("win").style.background = s.flash === "w" ? "color-mix(in srgb, var(--win) 35%, #0b1322)" : "";
    $("loss").style.background = s.flash === "l" ? "color-mix(in srgb, var(--loss) 35%, #0b1322)" : "";
    if (s.event && lastEvent !== null && s.event.id !== lastEvent && s.animations) play(s.event.kind);
    lastEvent = s.event ? s.event.id : 0;
    document.body.style.visibility = s.hidden ? "hidden" : "visible";
  } catch (e) { /* overlay ferme : on garde le dernier affichage */ }
}
refresh();
setInterval(refresh, 1000);
</script>
</body></html>
"""


class ObsServer:
    def __init__(self, log=print):
        self.log = log
        self.state = {}
        self.server = None

    def update(self, state):
        self.state = state  # remplacement atomique, lu par le thread du serveur

    def start(self):
        if self.server:
            return True
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.split("?")[0] == "/state":
                    body, ctype = json.dumps(owner.state).encode("utf-8"), "application/json"
                elif self.path.split("?")[0] in ("/", "/index.html"):
                    body, ctype = PAGE.encode("utf-8"), "text/html; charset=utf-8"
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", OBS_PORT), Handler)
        except OSError as e:
            self.log(f"Mode streamer : port {OBS_PORT} indisponible ({e})")
            return False
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.log(f"Mode streamer actif : {OBS_URL}")
        return True

    def stop(self):
        if self.server:
            server, self.server = self.server, None
            threading.Thread(target=lambda: (server.shutdown(), server.server_close()), daemon=True).start()
