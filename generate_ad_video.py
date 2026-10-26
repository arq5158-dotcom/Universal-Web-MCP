"""
Automated Video Ad Generator for Google Flow using Universal-Web-MCP.
Uses authenticated storage state to submit video generation prompts,
capture internal batchexecute RPCs, and track video generation status.
"""

import asyncio
import json
import logging
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FlowVideoGenerator")

PROJECT_URL = "https://flow.google.com/project/5730a6a6-a00a-4a95-8f22-20942efd1413"
AUTH_FILE = Path(__file__).resolve().parent / "flow_auth_state.json"
SCREENSHOT_FILE = Path(__file__).resolve().parent / "video_generation_live.png"

PROMPT = (
    "Generate a 30-second commercial ad for Universal-Web-MCP: A cinematic 4K hyperrealistic "
    "tech commercial showing an AI terminal instantly bypassing slow browser lag with emerald "
    "and neon blue sub-second JSON data streams, futuristic developer workstation, and a glowing "
    "Universal-Web-MCP logo."
)


async def generate_video():
    print("\n=======================================================")
    print("Submitting Video Generation Request to Google Flow...")
    print(f"Project: {PROJECT_URL}")
    print(f"Prompt: {PROMPT[:80]}...")
    print("=======================================================\n")

    captured_rpcs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=str(AUTH_FILE),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = await context.new_page()

        # Listen to batchexecute network calls
        async def on_response(response):
            if "batchexecute" in response.url:
                try:
                    text = await response.text()
                    captured_rpcs.append({
                        "url": response.url,
                        "status": response.status,
                        "text": text[:300]
                    })
                    print(f"Intercepted Flow RPC response (Status {response.status})")
                except Exception:
                    pass

        page.on("response", on_response)

        print("Loading project workspace...")
        await page.goto(PROJECT_URL, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(4000)

        # Target the exact ProseMirror prompt box in Google Flow
        prompt_box = page.locator("div.ProseMirror").first
        print(f"Prompt box (ProseMirror) found: {await prompt_box.count() > 0}")

        if await prompt_box.count() > 0:
            await prompt_box.click()
            await prompt_box.fill(PROMPT)
            print("Successfully filled prompt into Google Flow ProseMirror input!")
            await page.wait_for_timeout(1500)

            # Find send / submit button (arrow_forward icon button)
            send_btn = page.locator("button:has-text('arrow_forward')").first
            if await send_btn.count() == 0:
                send_btn = page.locator("button[aria-label*='Send'], button[aria-label*='Generate']").first

            if await send_btn.count() > 0:
                print("Clicking arrow_forward button to submit video generation...")
                await send_btn.click()
            else:
                print("Pressing Enter to submit prompt...")
                await prompt_box.press("Enter")

            print("Waiting 12 seconds for generation response...")
            await page.wait_for_timeout(12000)

            # Capture live screenshot
            await page.screenshot(path=str(SCREENSHOT_FILE))
            print(f"Live screenshot captured at: {SCREENSHOT_FILE}")

        await browser.close()

    print(f"\nCaptured {len(captured_rpcs)} internal RPC responses during execution.")
    return {
        "status": "submitted",
        "project": PROJECT_URL,
        "screenshot": str(SCREENSHOT_FILE),
        "captured_rpcs_count": len(captured_rpcs)
    }


if __name__ == "__main__":
    res = asyncio.run(generate_video())
    print("\nResult:", json.dumps(res, indent=2))
