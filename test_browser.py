"""Simple test to verify Playwright works."""
import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    async with async_playwright() as p:
        print("✓ Playwright initialized")
        browser = await p.chromium.launch(headless=False)
        print("✓ Browser launched")
        page = await browser.new_page()
        print("✓ Page created")
        await page.goto("https://example.com")
        print(f"✓ Navigated to: {page.url}")
        await asyncio.sleep(2)
        await browser.close()
        print("✓ Browser closed")
        print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_browser())


