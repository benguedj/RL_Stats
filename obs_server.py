"""Mode streamer : petite page web locale a ajouter dans OBS comme "source navigateur".

http://127.0.0.1:49124/ affiche l'overlay avec le design choisi dans le menu Apparence : l'appli
y envoie son rendu (/overlay.png) ; la page relit /state chaque seconde.
Le serveur n'ecoute que sur 127.0.0.1 (invisible depuis le reseau).
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OBS_PORT = 49124
OBS_URL = f"http://127.0.0.1:{OBS_PORT}/"
OBS_K = 1.0  # echelle de l'image envoyee (1440p, interface a 100 %) : on la redimensionne dans OBS

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>RL Stats</title>
<style>
  :root { --win: #2ee66b; --loss: #ff4d4d; }
  html, body { margin: 0; width: 100%; height: 100%; background: transparent; overflow: hidden; }
  #wrap { position: absolute; visibility: hidden; }
  #ov { display: block; }
  #fx { position: absolute; width: 600px; height: 260px; pointer-events: none; }
  .glow-w #ov { filter: drop-shadow(0 0 14px var(--win)); }
  .glow-l #ov { filter: drop-shadow(0 0 14px var(--loss)); }
  .pop { animation: pop .7s cubic-bezier(.3,1.6,.5,1); }
  .shake { animation: shake .6s; }
  @keyframes pop { 0% { transform: scale(1); } 35% { transform: scale(1.12); } 100% { transform: scale(1); } }
  @keyframes shake { 0%,100% { transform: translateX(0); } 15% { transform: translateX(-9px); }
                     30% { transform: translateX(8px); } 45% { transform: translateX(-6px); }
                     60% { transform: translateX(4px); } 75% { transform: translateX(-2px); } }
</style></head>
<body>
<div id="wrap">
  <img id="ov" alt="">
  <canvas id="fx" width="600" height="260"></canvas>
</div>
<script>
const $ = id => document.getElementById(id);
const MARGIN = 24;  // place pour le rebond et le halo
let lastEvent = null, particles = [], raf = null, wanted = null, shown = null;

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

// Meme ancrage que dans le jeu : les designs verticaux collent au bord droit, les autres
// sont centres en bas (l'image grandit vers le haut quand un bandeau apparait).
function place() {
  if (!shown) return;
  const s = shown, [w, h] = s.size, [ax, ay] = s.anchor, [x0, y0, x1, y1] = s.box;
  const wrap = $("wrap"), fx = $("fx"), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  wrap.style.width = w + "px"; wrap.style.height = h + "px";
  wrap.style.left = (s.kind === "edge" ? innerWidth - MARGIN - w : innerWidth / 2 - ax) + "px";
  wrap.style.top = (s.kind === "edge" ? innerHeight / 2 - ay : innerHeight - MARGIN - h) + "px";
  wrap.style.transformOrigin = cx + "px " + cy + "px";
  fx.style.left = (cx - 300) + "px"; fx.style.top = (cy - 75) + "px";
  wrap.style.visibility = "visible";
}

async function refresh() {
  try {
    const s = await (await fetch("/state", { cache: "no-store" })).json();
    if (!s.img) return;
    const root = document.documentElement.style;
    root.setProperty("--win", s.win_color); root.setProperty("--loss", s.loss_color);
    if (s.img !== wanted) {  // nouvelle image : chargee a part, puis echangee d'un coup
      wanted = s.img;
      const next = new Image();
      next.onload = () => { if (s.img === wanted) { $("ov").src = next.src; shown = s; place(); } };
      next.src = "/overlay.png?v=" + s.img;
    }
    if (s.event && lastEvent !== null && s.event.id !== lastEvent && s.animations) play(s.event.kind);
    lastEvent = s.event ? s.event.id : 0;
  } catch (e) { /* overlay ferme : on garde le dernier affichage */ }
}
addEventListener("resize", place);
refresh();
setInterval(refresh, 1000);
</script>
</body></html>
"""


class ObsServer:
    def __init__(self, log=print):
        self.log = log
        self.state = ({}, b"")  # (etat, image PNG)
        self.version = 0
        self.server = None

    def update(self, state, png):
        self.version += 1
        self.state = (dict(state, img=self.version), png)  # remplacement atomique, lu par le thread du serveur

    def start(self):
        if self.server:
            return True
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                state, png = owner.state
                if self.path.split("?")[0] == "/state":
                    body, ctype = json.dumps(state).encode("utf-8"), "application/json"
                elif self.path.split("?")[0] == "/overlay.png" and png:
                    body, ctype = png, "image/png"
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
