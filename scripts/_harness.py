"""Shared helpers for the dashboard scripts: a private app instance and demo data."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def post(base: str, path: str, payload: dict) -> None:
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10).read()


class PrivateApp:
    """Runs app.py on its own port, so scripts never touch the dashboard you have open."""

    def __init__(self, port: int = 8799):
        self.port = port
        self.base = f"http://127.0.0.1:{port}"
        self.proc = None

    def __enter__(self):
        env = dict(os.environ, ASHZO_PORT=str(self.port), PYTHONUNBUFFERED="1")
        self.proc = subprocess.Popen([sys.executable, str(ROOT / "app.py")], cwd=str(ROOT), env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 40
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(self.base + "/api/health", timeout=1) as r:
                    if json.loads(r.read()).get("app") == "ashzo-mcp":
                        return self
            except Exception:
                time.sleep(0.4)
        self.__exit__(None, None, None)
        raise RuntimeError("The app didn't start. Run `python app.py` to see why.")

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=8)
            except Exception:
                self.proc.kill()


def make_demo_media(folder: Path) -> dict:
    """Short sample clips (needs ffmpeg; without it the cards simply show no picture)."""
    folder.mkdir(parents=True, exist_ok=True)
    out = {}
    ff = shutil.which("ffmpeg")
    if not ff:
        return out
    sources = {
        "clip_a.mp4": "mandelbrot=size=360x640:rate=24:start_scale=2.5:end_scale=0.6",
        "clip_b.mp4": "gradients=size=360x640:rate=24:speed=0.03:c0=0x1e1b4b:c1=0x7c3aed:c2=0x38bdf8:c3=0x0f172a",
        "clip_c.mp4": "cellauto=size=360x640:rate=24:rule=110:random_fill_ratio=0.35",
    }
    for name, src in sources.items():
        target = folder / name
        if not target.exists():
            subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", src, "-t", "3",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)], check=False)
        if target.exists():
            out[name] = target
    for name in ("first.jpg", "last.jpg"):
        target = folder / name
        clip = out.get("clip_b.mp4") or out.get("clip_a.mp4")
        if clip and not target.exists():
            subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", "0.5" if name == "first.jpg" else "2.5",
                            "-i", str(clip), "-frames:v", "1", str(target)], check=False)
        if target.exists():
            out[name] = target
    return out


DEMO_STUDIO_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;width:1280px;height:800px;font-family:system-ui,sans-serif;background:#0d0f14;color:#e5e7eb;display:flex}
.side{width:360px;border-right:1px solid #232634;display:flex;flex-direction:column}
.side h3{margin:0;padding:16px;font-size:13px;color:#9ca3af;font-weight:600;border-bottom:1px solid #232634}
.msgs{flex:1;padding:14px;display:flex;flex-direction:column;gap:10px;font-size:13px;line-height:1.45}
.m{padding:10px 12px;border-radius:12px;background:#171a23;max-width:290px}
.m.me{align-self:flex-end;background:#312e81}
.box{margin:12px;border:1px solid #2d3140;border-radius:14px;padding:12px;font-size:12px;color:#6b7280}
.main{flex:1;padding:22px;display:grid;grid-template-columns:repeat(4,1fr);gap:14px;align-content:start}
.card{aspect-ratio:9/16;border-radius:14px;background:linear-gradient(160deg,#1e1b4b,#7c3aed 55%,#38bdf8);position:relative;overflow:hidden}
.card:nth-child(2){background:linear-gradient(160deg,#0f172a,#2563eb 60%,#a78bfa)}
.card:nth-child(3){background:linear-gradient(160deg,#111827,#0ea5e9 50%,#22d3ee)}
.card.gen{background:#171a23;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:8px;font-size:12px;color:#9ca3af}
.bar{width:60%;height:4px;border-radius:4px;background:#2d3140;overflow:hidden}.bar i{display:block;height:100%;width:62%;background:#818cf8}
.top{grid-column:1/-1;display:flex;justify-content:space-between;font-size:13px;color:#9ca3af}
</style></head><body>
<div class="side"><h3>Assistant (sample page)</h3><div class="msgs">
<div class="m me">Generate 1 video, 8 seconds, 9:16. Use the attached image as the first frame.</div>
<div class="m">Got it. Generating your clip now.</div></div>
<div class="box">Describe what you want to create…</div></div>
<div class="main"><div class="top"><span>Demo project</span><span>Sample screen for screenshots</span></div>
<div class="card"></div><div class="card"></div><div class="card"></div>
<div class="card gen"><span>Generating 62%</span><div class="bar"><i></i></div></div></div>
</body></html>"""


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()
