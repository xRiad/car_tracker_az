import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        
        try:
            await page.goto("https://turbo.az", timeout=15000)
            print("Заголовок:", await page.title())
        except Exception as e:
            print("Ошибка:", e)
        
        await browser.close()

asyncio.run(main())