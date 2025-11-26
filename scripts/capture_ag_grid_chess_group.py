import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "ag_grid_chess_group"
TASK_QUERY = "AG Grid: Filter to Chess games, group by Language, and select top three rows"
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
            reasoning="Starting point before narrowing down to Chess data"
        )

        game_input = page.locator("input[aria-label='Game Name Filter Input']:not([disabled])").first
        await game_input.fill("Chess")
        await game_input.press("Enter")
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="filter",
            description="Filtered Game Name column to rows containing 'Chess'",
            target="Game Name floating filter",
            reasoning="Limits the dataset to Chess-related records"
        )

        menu_button = page.locator("div[col-id='language'] .ag-header-cell-menu-button").first
        await menu_button.click()
        await page.locator(".ag-menu-option:has-text('Group by Language')").first.click()
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="group",
            description="Grouped Chess rows by Language",
            target="Language column menu",
            reasoning="Organizes Chess entries by the player's language via the built-in grouping feature"
        )

        checkboxes = page.locator(".ag-selection-checkbox input")
        for i in range(3):
            await checkboxes.nth(i).check()
        await page.wait_for_timeout(500)
        await capture_step(
            action_type="select",
            description="Selected the first three grouped Chess rows",
            target="Row selection checkboxes",
            reasoning="Highlights a subset of the filtered, grouped rows for follow-up"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

