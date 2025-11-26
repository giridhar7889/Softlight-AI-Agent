import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "airbnb_paris_map"
TASK_QUERY = "Airbnb: Search Paris stays and explore the map view"
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

        await page.fill("input[data-testid='structured-search-input-field-query']", "Paris")
        await page.click("button[data-testid='structured-search-input-search-button']")
        await page.wait_for_selector("div[data-testid='listing-card-title']", timeout=20000)
        await capture_step(
            action_type="search",
            description="Viewed Paris stay results",
            target="Search results grid",
            reasoning="Baseline after running the Paris search"
        )

        map_markers = page.locator("[data-testid='map/markers/BasePillMarker']")
        if await map_markers.count() == 0:
            try:
                show_map_button = page.locator("button:has-text('Show map')")
                if await show_map_button.count():
                    await show_map_button.click()
            except Exception:
                pass
        await map_markers.first.wait_for(timeout=20000)
        await capture_step(
            action_type="map",
            description="Opened the interactive map for Paris stays",
            target="Show map toggle",
            reasoning="Map view reveals clustered price pins for the search"
        )

        try:
            zoom_in = page.locator("[data-testid='map/ZoomInButton']")
            await zoom_in.wait_for(timeout=10000)
            await zoom_in.click()
            await page.wait_for_timeout(1500)
            await capture_step(
                action_type="zoom",
                description="Zoomed in on the Paris map",
                target="Map zoom controls",
                reasoning="Adjusting zoom provides a closer look at clustered listings"
            )
        except Exception:
            pass

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

