import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


async def download_video_real():
    print("Navigating to Flow project...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state="flow_auth_state.json",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            accept_downloads=True
        )
        page = await context.new_page()
        await page.goto("https://flow.google.com/project/5730a6a6-a00a-4a95-8f22-20942efd1413", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        thumb = page.locator("img[alt*='Generated video'], img[src*='video']").first
        if await thumb.count() > 0:
            print("Clicking video asset...")
            await thumb.click()
            await page.wait_for_timeout(2000)

            dl_btn = page.locator("button:has-text('download'), button[aria-label*='Download']").first
            if await dl_btn.count() > 0:
                print("Clicking download icon button...")
                await dl_btn.click()
                await page.wait_for_timeout(1000)

                # Select 720p quality menuitem from dropdown
                quality_option = page.locator("[role='menuitem']:has-text('720p'), button:has-text('720p')").first
                print("Clicking 720p option...")
                async with page.expect_download(timeout=25000) as download_info:
                    await quality_option.click()

                download = await download_info.value
                dest = DOWNLOAD_DIR / (download.suggested_filename or "flow_clip_720p.mp4")
                await download.save_as(str(dest))
                size = os.path.getsize(dest)
                print(f"\n=======================================================")
                print(f"SUCCESS: Video downloaded to PC locally!")
                print(f"File Path: {dest}")
                print(f"File Size: {size} bytes ({round(size / 1024 / 1024, 2)} MB)")
                print(f"=======================================================\n")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(download_video_real())
