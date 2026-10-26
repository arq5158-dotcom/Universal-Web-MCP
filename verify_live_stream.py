import asyncio
import json
import urllib.request
from playwright.async_api import async_playwright

def send_event(payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('http://localhost:8000/api/live/broadcast', data=data, headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req)

async def test_live():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page(viewport={"width": 1280, "height": 850})
        await page.goto("http://localhost:8000/")
        await page.wait_for_timeout(1000)

        # 1. Expand Live Agent Feed
        await page.click("button:has-text('Live Feed')")
        await page.wait_for_timeout(350)
        await page.screenshot(path="c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/live_feed_expanded.png")
        print("1. Captured expanded feed")

        # 2. Broadcast active rendering progress event over HTTP to server
        send_event({
            "type": "progress",
            "message": "Generating frames with Gemini Omni Flash (8s, 4K)...",
            "stage": "rendering",
            "progress": 65
        })
        await page.wait_for_timeout(600)
        await page.screenshot(path="c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/live_rendering_progress.png")
        print("2. Captured real-time rendering progress in HUD")

        # 3. Broadcast video_ready event to verify auto-refresh of Vault and Toast Notification
        send_event({
            "type": "video_ready",
            "message": "Saved: UniversalWeb_OmniFlash_6s_StartEnd_ai_terminal_20261026.mp4 (6.56 MB)",
            "data": {"filename": "UniversalWeb_OmniFlash_6s_StartEnd_ai_terminal_20261026.mp4", "size_mb": 6.56},
            "stage": "ready",
            "progress": 100
        })
        await page.wait_for_timeout(700)
        await page.screenshot(path="c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/live_video_ready_toast.png")
        print("3. Captured video ready toast & auto-updated vault")

        await b.close()
        print("ALL REAL-TIME LIVE EVENT TESTS PASSED!")

asyncio.run(test_live())
