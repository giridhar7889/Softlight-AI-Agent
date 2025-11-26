"""Helper script to save authentication cookies for reuse."""

import asyncio
import json
from playwright.async_api import async_playwright

async def save_auth_cookies(app_url: str, output_file: str):
    """
    Manually log in to an app and save cookies for later use.
    
    Usage:
        python auth_helper.py
    """
    async with async_playwright() as p:
        # Launch browser in non-headless mode for manual login
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"Opening {app_url}...")
        print("Please log in manually in the browser window.")
        print("After logging in, press Enter here to save cookies...")
        
        await page.goto(app_url)
        
        # Wait for user to log in
        input("Press Enter after you've logged in...")
        
        # Save cookies
        cookies = await context.cookies()
        with open(output_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"✅ Cookies saved to {output_file}")
        print("You can now use these cookies for headless automation!")
        
        await browser.close()

if __name__ == "__main__":
    print("Authentication Cookie Helper")
    print("=" * 50)
    print("\nAvailable apps:")
    print("1. Linear (https://linear.app)")
    print("2. Notion (https://notion.so)")
    
    choice = input("\nChoose app (1-2): ")
    
    if choice == "1":
        asyncio.run(save_auth_cookies(
            "https://linear.app",
            "linear_cookies.json"
        ))
    elif choice == "2":
        asyncio.run(save_auth_cookies(
            "https://notion.so",
            "notion_cookies.json"
        ))
    else:
        print("Invalid choice")

