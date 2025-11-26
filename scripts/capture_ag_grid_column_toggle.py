import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "ag_grid_column_review"
TASK_QUERY = "AG Grid: Quick filter Spanish, hide the Rating column via column panel, then restore it"
APP_NAME = "Linear"
START_URL = "https://www.ag-grid.com/example/"


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

        await capture_step(
            action_type="navigate",
            description="Opened AG Grid demo landing page",
            target=START_URL,
            reasoning="Baseline view before filtering and toggling columns"
        )

        quick_filter = page.locator("#global-filter")
        await quick_filter.fill("Spanish")
        await quick_filter.press("Enter")
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="filter",
            description="Applied global quick filter for 'Spanish'",
            target="#global-filter",
            reasoning="Shows only the Spanish-related rows in the grid"
        )

        column_search = page.locator("input[aria-label='Filter Columns Input']")
        await column_search.fill("Rating")
        await page.wait_for_timeout(300)
        rating_toggle = page.locator("input[aria-label='Press SPACE to toggle visibility (visible)']").first
        await rating_toggle.click()
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="hide-column",
            description="Hid the Rating column via the column tool panel",
            target="Column tool panel toggle",
            reasoning="Removes the Rating column from the Spanish-focused view"
        )

        hidden_toggle = page.locator("input[aria-label='Press SPACE to toggle visibility (hidden)']").first
        await hidden_toggle.click()
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="show-column",
            description="Restored the Rating column",
            target="Column tool panel toggle",
            reasoning="Brings Rating back into the grid after review"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

