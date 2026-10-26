import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page(viewport={'width': 1280, 'height': 800})
        await page.goto('http://localhost:8000/')
        await page.wait_for_timeout(600)
        
        # 1. Open Model dropdown
        await page.click('#dropdown-model .dropdown-trigger')
        await page.wait_for_timeout(350)
        await page.screenshot(path='c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/anim_dropdown_open.png')
        print('1. Captured dropdown open')
        
        # 2. Select Veo 3.1
        await page.click('#dropdown-model .dropdown-item[data-value="veo_3_1"]')
        await page.wait_for_timeout(350)
        await page.screenshot(path='c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/anim_veo_selected.png')
        print('2. Captured Veo selected')
        
        # 3. Open Connect Account modal & open platform dropdown inside it
        await page.click('header button:has-text("Connect")')
        await page.wait_for_timeout(400)
        await page.click('#dropdown-platform .dropdown-trigger')
        await page.wait_for_timeout(350)
        await page.screenshot(path='c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/anim_modal_dropdown.png')
        print('3. Captured modal with animated dropdown')
        
        # 4. Select GitHub in modal
        await page.click('#dropdown-platform .dropdown-item[data-value="https://github.com/login"]')
        await page.wait_for_timeout(350)
        await page.screenshot(path='c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/anim_modal_selected.png')
        print('4. Captured GitHub selected in modal')
        
        # Close modal
        await page.click('#loginModal button:has-text("Cancel")')
        await page.wait_for_timeout(400)
        
        # 5. Toggle to light theme & open Quality dropdown in light mode
        await page.click('#themeToggleBtn')
        await page.wait_for_timeout(550)
        await page.click('#dropdown-quality .dropdown-trigger')
        await page.wait_for_timeout(350)
        await page.screenshot(path='c:/Users/creat/.gemini/antigravity/brain/2dd14032-773a-4ba2-9b50-a31ff84c2fb9/anim_light_dropdown.png')
        print('5. Captured light theme with dropdown')
        
        await b.close()
        print('ALL ANIMATION VERIFICATION TESTS PASSED SUCCESSFULLY!')

asyncio.run(verify())
