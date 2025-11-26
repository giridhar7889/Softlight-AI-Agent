import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "ag_grid_language_filter_sort"
TASK_QUERY = "AG Grid: Filter the Language column to French and sort Balance high to low"
APP_NAME = "Linear"
START_URL = "https://www.ag-grid.com/example/"


async def main():
    state_manager = StateManager()
    workflow_path = state_manager.start_workflow(APP_NAME, TASK_ID, TASK_QUERY)

    metadata_path = workflow_path / "metadata.json"
    metadata = metadata_path.read_text()
    import json
    metadata_obj = json.loads(metadata)
    metadata_obj["start_url"] = START_URL
    metadata_path.write_text(json.dumps(metadata_obj, indent=2))

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
            reasoning="Initial state before filtering"
        )

        language_input = page.locator("input[aria-label='Language Filter Input']:not([disabled])").first
        await language_input.click()
        await language_input.fill("French")
        await language_input.press("Enter")
        await page.wait_for_timeout(1000)

        await capture_step(
            action_type="filter",
            description="Filtered Language column to show only French rows",
            target="Language floating filter input",
            reasoning="Typed 'French' into the floating filter and pressed Enter to apply"
        )

        balance_header = page.locator(".ag-header-cell[col-id='bankBalance']").first
        await balance_header.click()
        await balance_header.click()
        await page.wait_for_timeout(1000)

        await capture_step(
            action_type="sort",
            description="Sorted Bank Balance column from high to low",
            target="Bank Balance header",
            reasoning="Clicked the Bank Balance header twice to toggle descending order"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

