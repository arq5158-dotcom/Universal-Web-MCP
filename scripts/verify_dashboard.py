"""
Checks the dashboard the way a person would notice problems. Run after any UI change:

    python scripts/verify_dashboard.py

Starts its own copy of the app (port 8798) and checks:
- no JavaScript errors, fonts/icons/CSS load offline
- dropdowns and the Activity panel are overlays (nothing else moves when they open)
- spinners are square and rotate around their centre (no wobble)
- elements marked hidden are really hidden
- theme switch works (light / dark)
- live updates arrive without a refresh: progress, Flow chat, generation cards, Live View pictures
Prints PASS/FAIL per check and exits 1 on any failure. Pictures go to scripts/_out/.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import DEMO_STUDIO_HTML, ROOT, PrivateApp, post  # noqa: E402

OUT = ROOT / "scripts" / "_out"


async def main() -> int:
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))

    with PrivateApp(8798) as app:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            await page.goto(app.base + "/")
            await page.wait_for_timeout(1500)

            check("fonts load offline", await page.evaluate("document.fonts.check('12px \"Plus Jakarta Sans\"')"))
            check("Tailwind CSS loaded", await page.evaluate("getComputedStyle(document.querySelector('header .flex')).display") == "flex")
            check("icons loaded", "Font Awesome" in await page.evaluate("getComputedStyle(document.querySelector('.fa-solid'),'::before').fontFamily"))
            check("live connection", (await page.inner_text("#liveConnText")).strip() == "Live")

            hidden_leaks = await page.evaluate("""[...document.querySelectorAll('.hidden')].filter(e =>
                !/\\b(sm|md|lg|xl):/.test(e.className) && getComputedStyle(e).display !== 'none').map(e => e.id || e.className)""")
            check("hidden elements stay hidden", not hidden_leaks, str(hidden_leaks))

            layout = "[...document.querySelectorAll('#tab-flow > *')].map(e => { const r = e.getBoundingClientRect(); return [r.top, r.height] })"
            before = await page.evaluate(layout)
            await page.click("#dropdown-model .dropdown-trigger")
            await page.wait_for_timeout(350)
            check("model dropdown is an overlay", before == await page.evaluate(layout))
            await page.screenshot(path=str(OUT / "dropdown.png"))
            await page.keyboard.press("Escape")
            await page.click(".popover-anchor > button")
            await page.wait_for_timeout(300)
            check("Activity panel is an overlay", before == await page.evaluate(layout))
            await page.keyboard.press("Escape")

            spin = await page.evaluate("""(() => { const s = document.createElement('span'); s.className = 'spin-ring'; document.body.appendChild(s);
                const r = s.getBoundingClientRect(), c = getComputedStyle(s); const out = [r.width, r.height, c.transformOrigin, c.animationName]; s.remove(); return out })()""")
            check("spinner is square and centred", spin[0] == spin[1] and [float(v.rstrip("px")) for v in spin[2].split()[:2]] == [spin[0] / 2, spin[1] / 2] and spin[3] != "none", str(spin))

            await page.click("[data-theme-opt='light']")
            await page.wait_for_timeout(900)
            light = await page.evaluate("document.documentElement.dataset.theme")
            await page.click("[data-theme-opt='dark']")
            await page.wait_for_timeout(900)
            dark = await page.evaluate("document.documentElement.classList.contains('dark')")
            check("theme switch", light == "light" and dark)

            # live updates, no refresh
            now = int(time.time() * 1000)
            card = {"id": "verify1", "title": "verify_clip", "prompt": "A test prompt", "model_label": "Gemini Omni Flash 1.1",
                    "duration": "8", "aspect_ratio": "9:16", "state": "rendering", "progress": 40, "message": "Rendering",
                    "references": [], "chat": [], "started_at": now, "files": [], "source": "mcp-agent"}
            post(app.base, "/api/live/broadcast", {"type": "progress", "message": "Rendering your video", "stage": "rendering", "progress": 40,
                                                   "data": {"job_id": "verify1", "title": "verify_clip", "kind": "flow", "started_at": now}})
            post(app.base, "/api/live/broadcast", {"type": "generation", "message": "Rendering", "data": card})
            post(app.base, "/api/live/broadcast", {"type": "flow_chat", "message": "Working on it.", "data": {"job_id": "verify1"}})
            shot = await browser.new_page(viewport={"width": 1280, "height": 800})
            await shot.set_content(DEMO_STUDIO_HTML)
            import base64
            frame = base64.b64encode(await shot.screenshot(type="jpeg", quality=60)).decode()
            await shot.close()
            post(app.base, "/api/live/ingest", {"kind": "frame", "payload": {"type": "frame", "image": frame, "ts": now, "meta": {"url": "sample"}}})
            await page.wait_for_timeout(1200)
            check("progress updates live", (await page.inner_text("#liveAgentBadge")).strip() == "RENDERING")
            check("generation card appears live", await page.evaluate("!!document.getElementById('gen-verify1')"))
            check("Flow chat updates live", "Working on it." in await page.inner_text("#chatList"))
            check("Live View picture updates", await page.evaluate("!document.querySelector('#screenImg').classList.contains('hidden')"))
            post(app.base, "/api/live/broadcast", {"type": "progress", "message": "Done", "stage": "ready", "progress": 100,
                                                   "data": {"job_id": "verify1", "kind": "flow"}})
            await page.wait_for_timeout(600)
            check("spinner stops when the job ends", (await page.inner_text("#liveAgentBadge")).strip() == "READY"
                  and not await page.evaluate("!!document.querySelector('#hudIcon .spin-ring')"))
            await page.screenshot(path=str(OUT / "after_live_updates.png"), full_page=True)
            check("no JavaScript errors", not errors, "; ".join(errors[:3]))
            await browser.close()

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} checks passed. Pictures: {OUT}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
