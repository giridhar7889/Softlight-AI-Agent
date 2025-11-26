import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "saucedemo_inventory_filter"
TASK_QUERY = "SauceDemo: Sort inventory by price (high to low) and add cheapest item from the sorted view"
APP_NAME = "Linear"
START_URL = "https://www.saucedemo.com/"
USERNAME = "standard_user"
PASSWORD = "secret_sauce"


async def main():
    state_manager = StateManager()
    workflow_path = state_manager.start_workflow(APP_NAME, TASK_ID, TASK_QUERY)

    metadata_path = workflow_path / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["start_url"] = START_URL
    metadata_path.write_text(json.dumps(metadata, indent=2))

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)
        page = await browser.new_page()
        await page.goto(START_URL, wait_until="networkidle")

        async def capture_step(action_type: str, description: str, target: str, reasoning: str):
            screenshot_bytes = await page.screenshot(full_page=False)
            image = Image.open(io.BytesIO(screenshot_bytes))
            state_manager.capture_step(
                screenshot=image,
                description=description,
                action_type=action_type,
                action_target=target,
                url=page.url,
                reasoning=reasoning,
                metadata={
                    "difference": 1.0,
                    "reason": "Manual capture",
                    "page_title": await page.title()
                }
            )

        await page.fill("#user-name", USERNAME)
        await page.fill("#password", PASSWORD)
        await page.click("#login-button")
        await page.wait_for_selector(".inventory_item", timeout=5000)
        await capture_step(
            action_type="login",
            description="Logged in and reached inventory list",
            target="Inventory container",
            reasoning="Baseline before sorting"
        )

        await page.select_option(".product_sort_container", value="hilo")
        await page.wait_for_timeout(500)
        await capture_step(
            action_type="sort",
            description="Sorted inventory by price high to low",
            target="Sorting dropdown",
            reasoning="Inventory order now shows most expensive items first"
        )

        last_add_button = page.locator(".inventory_item").last.locator("button")
        await last_add_button.click()
        await capture_step(
            action_type="add-to-cart",
            description="Added the cheapest item after sorting",
            target="Last item's Add to Cart button",
            reasoning="Demonstrates grabbing the least expensive product from the sorted view"
        )

        await page.locator(".shopping_cart_link").click()
        await capture_step(
            action_type="cart",
            description="Viewed cart to confirm cheapest item was added",
            target="Cart page",
            reasoning="Cart badge and line item confirm the action"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

