"""
Takes the README screenshots (docs/screenshots/*.png) with sample data.

Starts its own copy of the app on port 8799 (your open dashboard is not touched), fills it with sample
accounts, videos and a generation in progress, and captures light and dark versions.

    python scripts/capture_screenshots.py            # needs: pip install -r requirements.txt, playwright chromium
    python scripts/capture_screenshots.py --port 8800

ffmpeg (optional) makes the sample video thumbnails.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import DEMO_STUDIO_HTML, ROOT, PrivateApp, b64, make_demo_media, post  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
MEDIA = ROOT / "scripts" / "_out" / "demo_media"
NOW = int(time.time() * 1000)

PROMPT = ("Lia, a young woman with a short black bob and a mustard raincoat, walks across a wet neon rooftop at dusk, "
          "slow dolly-in, soft rim light, light rain, city bokeh behind her. Hands, phone and umbrella rendered correctly.")


def demo_sessions():
    return {"status": "success", "sessions": [
        {"id": "s1", "name": "Google Flow", "email": "lia.studio@example.com", "domain": "flow.google.com", "is_active": True, "cookie_count": 14},
        {"id": "s2", "name": "GitHub", "email": "", "domain": "github.com", "is_active": False, "cookie_count": 6},
        {"id": "s3", "name": "Notion", "email": "", "domain": "www.notion.so", "is_active": False, "cookie_count": 0},
    ]}


def demo_generations(media):
    def file(name, clip):
        return [{"name": name, "url": f"/demo-media/{clip}", "size_mb": 6.4, "scene": 1}] if clip in media else []
    refs = [{"role": "first", "name": "first.jpg", "url": "/demo-media/first.jpg" if "first.jpg" in media else None}]
    return [
        {"id": "g2", "title": "lia_rooftop_clip1", "prompt": PROMPT, "model": "omni_flash", "model_label": "Gemini Omni Flash 1.1",
         "duration": "8", "aspect_ratio": "9:16", "quality": "1080p", "references": refs, "source": "mcp-agent", "state": "ready",
         "progress": 100, "message": "Done · 1 video saved to the vault.", "chat": [{"text": "Your video is ready. Want another take?"}],
         "started_at": NOW - 900_000, "finished_at": NOW - 640_000, "files": file("lia_rooftop_clip1_OmniFlash_8s.mp4", "clip_b.mp4")},
        {"id": "g1", "title": "shed_timelapse", "prompt": "Timelapse of a tiny garden shed being built from pallets, overhead view, sunny afternoon.",
         "model": "veo_3_1", "model_label": "Veo 3.1", "duration": "8", "aspect_ratio": "9:16", "quality": "1080p", "references": [],
         "source": "dashboard", "state": "ready", "progress": 100, "message": "Done", "chat": [{"text": "Here is your timelapse."}],
         "started_at": NOW - 4_000_000, "finished_at": NOW - 3_700_000, "files": file("shed_timelapse_Veo31_8s.mp4", "clip_a.mp4")},
    ]


def demo_downloads(media):
    names = [("lia_rooftop_clip1_OmniFlash_8s_20261026_171204.mp4", "clip_b.mp4", 6.4),
             ("shed_timelapse_Veo31_8s_20261026_160811.mp4", "clip_a.mp4", 7.9),
             ("pool_hack_clip3_OmniFlash_10s_20261025_221530.mp4", "clip_c.mp4", 8.2)]
    return [{"name": n, "rel": n, "url": f"/demo-media/{c}", "size_mb": s, "modified": "2026-10-26 17:12"} for n, c, s in names]


def active_card(media):
    return {"id": "g3", "title": "lia_rooftop_clip2", "prompt": PROMPT.replace("walks across", "stops at the edge of"),
            "model": "omni_flash", "model_label": "Gemini Omni Flash 1.1", "duration": "8", "aspect_ratio": "9:16",
            "quality": "1080p", "source": "mcp-agent", "state": "rendering", "progress": 62,
            "message": "Rendering your video · 1:35 · Flow shows 62%",
            "references": [{"role": "first", "url": "/demo-media/first.jpg" if "first.jpg" in media else None},
                           {"role": "last", "url": "/demo-media/last.jpg" if "last.jpg" in media else None}],
            "chat": [{"text": "Got it. Generating your clip now."}], "started_at": NOW - 95_000, "files": [],
            "sent_message": "Generate 1 video with Gemini Omni Flash 1.1, 8 seconds long, aspect ratio 9:16.\n"
                            "Use the first attached image as the first frame and the second attached image as the last frame."}


def push_live(base, frame_b64, media):
    card = active_card(media)
    post(base, "/api/live/broadcast", {"type": "agent", "message": "flow_generate_video started (prompt: Lia, a young woman…)", "source": "mcp-agent"})
    post(base, "/api/live/broadcast", {"type": "generation", "message": "Queued", "data": {**card, "state": "submitting", "progress": 14}, "source": "mcp-agent"})
    post(base, "/api/live/broadcast", {"type": "progress", "message": "Sent to Flow's agent. Waiting for it to start your video…", "stage": "waiting", "progress": 20,
                                       "data": {"job_id": "g3", "title": card["title"], "kind": "flow", "started_at": card["started_at"]}, "source": "mcp-agent"})
    post(base, "/api/live/broadcast", {"type": "flow_chat", "message": "Got it. Generating your clip now.", "data": {"job_id": "g3"}, "source": "mcp-agent"})
    post(base, "/api/live/broadcast", {"type": "flow_chat", "message": "Using your first and last frames, 8 seconds, vertical.", "data": {"job_id": "g3"}, "source": "mcp-agent"})
    post(base, "/api/live/broadcast", {"type": "progress", "message": card["message"], "stage": "rendering", "progress": 62,
                                       "data": {"job_id": "g3", "title": card["title"], "kind": "flow", "started_at": card["started_at"]}, "source": "mcp-agent"})
    post(base, "/api/live/broadcast", {"type": "generation", "message": card["message"], "data": card, "source": "mcp-agent"})
    post(base, "/api/live/ingest", {"kind": "frame", "payload": {"type": "frame", "image": frame_b64, "ts": int(time.time() * 1000),
                                                                 "meta": {"title": "Demo project", "url": "Ashzo Browser (sample page)"}}})


CARD_HOST = """<!doctype html><html><body style="margin:0;background:#1f1f1f;padding:28px">
<iframe id="f" sandbox="allow-scripts" style="width:600px;border:0;height:300px;display:block"></iframe>
<script>
const f = document.getElementById('f');
window.addEventListener('message', (e) => {
  if (e.source !== f.contentWindow) return; const m = e.data; if (!m || m.jsonrpc !== '2.0') return;
  const reply = (result) => f.contentWindow.postMessage({jsonrpc: '2.0', id: m.id, result}, '*');
  if (m.method === 'ui/initialize') reply({protocolVersion: '2026-01-26', hostContext: {theme: 'dark'}});
  else if (m.method === 'ui/notifications/initialized') window.__ready = true;
  else if (m.method === 'ui/notifications/size-changed') f.style.height = (m.params.height + 2) + 'px';
  else if (m.method === 'tools/call') reply({structuredContent: window.__card});
  else if (m.id !== undefined) reply({});
});
</script></body></html>"""


async def capture_chat_card(browser, media):
    """The live card an agent's flow_generate_video call shows inside Claude / ChatGPT / VS Code."""
    import base64
    card = active_card(media)
    thumbs = {}
    for role in ("first", "last"):
        f = MEDIA / f"{role}.jpg"
        thumbs[role] = "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else None
    card = {**card, "started_at": int(time.time() * 1000) - 95_000, "chat": ["Got it. Generating your clip now.",
            "Using your first and last frames, 8 seconds, vertical."],
            "references": [{"role": r, "thumb": thumbs[r]} for r in ("first", "last")]}
    page = await browser.new_page(viewport={"width": 656, "height": 520}, device_scale_factor=1.5)
    await page.set_content(CARD_HOST)
    await page.evaluate("(c) => { window.__card = c }", card)
    await page.evaluate("(html) => { document.getElementById('f').srcdoc = html }", (ROOT / "web" / "chat_card.html").read_text(encoding="utf-8"))
    await page.wait_for_function("window.__ready === true", timeout=10000)
    await page.evaluate("""(c) => document.getElementById('f').contentWindow.postMessage({jsonrpc: '2.0',
        method: 'ui/notifications/tool-result', params: {structuredContent: {result: {status: 'started', job: {id: c.id}}}}}, '*')""", card)
    await page.wait_for_timeout(1500)
    await page.screenshot(path=str(OUT / "chat-card-dark.png"), full_page=True)
    print("saved", OUT / "chat-card-dark.png")
    await page.close()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8799)
    args = ap.parse_args()
    from playwright.async_api import async_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    media = make_demo_media(MEDIA)
    with PrivateApp(args.port) as app:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            # the "browser" picture shown in Live View
            pg = await browser.new_page(viewport={"width": 1280, "height": 800})
            await pg.set_content(DEMO_STUDIO_HTML)
            frame = await pg.screenshot(type="jpeg", quality=72)
            await pg.close()
            import base64
            frame_b64 = base64.b64encode(frame).decode()

            await capture_chat_card(browser, media)

            for theme in ("dark", "light"):
                ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
                await ctx.add_init_script(f"try{{localStorage.setItem('ashzo_theme','{theme}')}}catch(e){{}}")

                async def route(r):
                    url = r.request.url
                    path = url.split(str(args.port), 1)[-1].split("?")[0]
                    if path.startswith("/demo-media/"):
                        f = MEDIA / path.rsplit("/", 1)[-1]
                        if f.exists():
                            return await r.fulfill(body=f.read_bytes(), content_type=mimetypes.guess_type(f.name)[0] or "application/octet-stream")
                        return await r.fulfill(status=404, body="")
                    data = {
                        "/api/sessions": demo_sessions(),
                        "/api/flow/generations": demo_generations(media),
                        "/api/flow/downloads": demo_downloads(media),
                        "/api/flow/credits": {"status": "success", "live_credits": 1240, "tier": "PRO", "checked_at": NOW - 60_000},
                        "/api/browser/status": {"running": True, "visible": True, "port": 9333, "page": "https://flow.google.com/", "chrome": "chrome"},
                    }.get(path)
                    if data is None:
                        return await r.continue_()
                    return await r.fulfill(body=json.dumps(data), content_type="application/json")
                await ctx.route("**/*", route)

                page = await ctx.new_page()
                await page.goto(app.base + "/")
                await page.wait_for_timeout(1200)
                push_live(app.base, frame_b64, media)
                await page.wait_for_timeout(1500)
                await page.evaluate("document.querySelectorAll('video').forEach(v=>{try{v.currentTime=1.2}catch(e){}})")
                await page.wait_for_timeout(800)
                await page.screenshot(path=str(OUT / f"flow-{theme}.png"))
                print("saved", OUT / f"flow-{theme}.png")

                if theme == "dark":
                    await page.add_style_tag(content="header{position:static!important}")  # sticky header would cover element shots
                    grid = await page.query_selector("#generationsGrid")
                    section = await grid.evaluate_handle("e => e.closest('.ashzo-glass') || e.parentElement")
                    await section.as_element().screenshot(path=str(OUT / "generations-dark.png"))
                    await page.click("[data-live-tab='chat']")
                    await page.wait_for_timeout(300)
                    live = await page.query_selector("#live-chat")
                    card = await live.evaluate_handle("e => e.closest('.ashzo-glass')")
                    await card.as_element().screenshot(path=str(OUT / "live-chat-dark.png"))
                    await page.click("[data-live-tab='screen']")

                    await page.click("#dropdown-model .dropdown-trigger")
                    await page.wait_for_timeout(350)
                    gen = await page.evaluate_handle("document.querySelector('#dropdown-model').closest('.ashzo-glass')")
                    await gen.as_element().screenshot(path=str(OUT / "dropdown-overlay-dark.png"))
                    await page.keyboard.press("Escape")

                    await page.evaluate("""() => { openLoginModal(); paintLogin({id:'demo', phase:'waiting', deadline: Date.now()+262000,
                        message:'Sign in on the Chrome window that just opened. This updates by itself.'}); }""")
                    await page.wait_for_timeout(500)
                    await page.screenshot(path=str(OUT / "connect-dark.png"))
                    await page.evaluate("closeLoginModal()")

                    await page.evaluate("switchTab('learner')")
                    for i, (m, u, s) in enumerate([("POST", "aisandbox-pa.googleapis.com/v1/projects:list", 200),
                                                    ("GET", "flow.google.com/api/credits", 200),
                                                    ("POST", "aisandbox-pa.googleapis.com/v1/video:generate", 200)]):
                        post(app.base, "/api/live/broadcast", {"type": "recorder", "message": f"{m} {u} → {s}", "data": {"recording": True}})
                    await page.wait_for_timeout(500)
                    await page.screenshot(path=str(OUT / "explorer-dark.png"))

                await page.evaluate("switchTab('sessions')")
                await page.wait_for_timeout(700)
                await page.screenshot(path=str(OUT / f"accounts-{theme}.png"))
                await ctx.close()
            await browser.close()
    print("Screenshots are in", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
