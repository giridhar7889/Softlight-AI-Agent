import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "ag_grid_game_chess_selection"
TASK_QUERY = "AG Grid: Select first 3 rows where Game Name contains Chess"
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
            description="Opened AG Grid example landing page",
            target=START_URL,
            reasoning="Initial state before filtering for Chess"
        )

        game_input = page.locator("input[aria-label='Game Name Filter Input']:not([disabled])").first
        await game_input.click()
        await game_input.fill("Chess")
        await game_input.press("Enter")
        await page.wait_for_timeout(1000)

        await capture_step(
            action_type="filter",
            description="Filtered Game Name column to rows containing 'Chess'",
            target="Game Name floating filter input",
            reasoning="Typed 'Chess' into the floating filter and pressed Enter"
        )

        checkboxes = page.locator(".ag-selection-checkbox input")
        for i in range(3):
            await checkboxes.nth(i).check()
        await page.wait_for_timeout(500)

        await capture_step(
            action_type="select",
            description="Selected first three filtered rows with Game Name containing 'Chess'",
            target="Row selection checkboxes",
            reasoning="Checked the first three row selection boxes after filtering"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

