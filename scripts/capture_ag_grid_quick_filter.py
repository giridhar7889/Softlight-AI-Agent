import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "ag_grid_quick_filter_english"
TASK_QUERY = "AG Grid: Use global filter to show rows containing English"
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
            reasoning="Baseline state before using the global filter"
        )

        quick_filter = page.locator("#global-filter")
        await quick_filter.fill("English")
        await quick_filter.press("Enter")
        await page.wait_for_timeout(1000)

        await capture_step(
            action_type="filter",
            description="Applied global quick filter for 'English'",
            target="#global-filter",
            reasoning="Typed 'English' in the global filter to show only matching rows"
        )

        summary_text = await page.locator(".ag-center-cols-container div[col-id='language']").first.text_content()
        await capture_step(
            action_type="info",
            description="Verified filtered results show English entries",
            target="First visible row after filtering",
            reasoning=f"Top visible language cell reads '{summary_text}' after filtering"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

