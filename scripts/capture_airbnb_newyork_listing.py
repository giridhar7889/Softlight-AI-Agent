import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "airbnb_newyork_listing"
TASK_QUERY = "Airbnb: Open a New York listing and review its details"
APP_NAME = "Airbnb"
START_URL = "https://www.airbnb.com/"


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
        await page.goto(START_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

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

        try:
            await page.click("button:has-text('Got it')", timeout=2000)
        except Exception:
            pass

        await page.fill("input[data-testid='structured-search-input-field-query']", "New York")
        await page.click("button[data-testid='structured-search-input-search-button']")
        await page.wait_for_selector("div[data-testid='card-container']", timeout=20000)
        await capture_step(
            action_type="search",
            description="Viewed New York stay results",
            target="Search results grid",
            reasoning="Baseline before drilling into a listing"
        )

        card = page.locator("div[data-testid='card-container']").first
        link = card.locator("a").first
        try:
            await link.evaluate("node => node.removeAttribute('target')")
        except Exception:
            pass
        await link.scroll_into_view_if_needed()
        await link.click(force=True)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_selector("h1", timeout=20000)
        await capture_step(
            action_type="detail",
            description="Opened the top New York listing",
            target="Listing hero section",
            reasoning="Captures title, rating, and hero media of the selected stay"
        )

        try:
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(1500)
            await capture_step(
                action_type="scroll",
                description="Scrolled further down the listing details",
                target="Mid-page content",
                reasoning="Captures in-depth details like sleeping arrangements and highlights"
            )
        except Exception:
            pass

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

