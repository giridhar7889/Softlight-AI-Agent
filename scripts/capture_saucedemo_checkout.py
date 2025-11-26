import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "saucedemo_checkout_flow"
TASK_QUERY = "SauceDemo: Checkout with Agent Smith, zip 12345, and verify Thank You page"
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
        await page.locator("button[data-test='add-to-cart-sauce-labs-backpack']").click()
        await page.locator("button[data-test='add-to-cart-sauce-labs-bike-light']").click()
        await capture_step(
            action_type="prepare",
            description="Added Backpack and Bike Light prior to checkout",
            target="Inventory grid buttons",
            reasoning="Cart now has two items before starting checkout"
        )

        await page.locator(".shopping_cart_link").click()
        await page.click("#checkout")
        await page.fill("#first-name", "Agent")
        await page.fill("#last-name", "Smith")
        await page.fill("#postal-code", "12345")
        await capture_step(
            action_type="form",
            description="Filled checkout information with Agent Smith 12345",
            target="Checkout form",
            reasoning="Ready to continue to order summary"
        )

        await page.click("#continue")
        await capture_step(
            action_type="summary",
            description="Viewed order summary before finishing",
            target="Checkout overview",
            reasoning="Verifying items and totals before completion"
        )

        await page.click("#finish")
        await page.wait_for_selector(".complete-header", timeout=5000)
        await capture_step(
            action_type="confirmation",
            description="Finished order and saw 'Thank You' message",
            target="Thank you screen",
            reasoning="Confirms checkout completion with success banner"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

