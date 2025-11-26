import asyncio
import io
import json
from pathlib import Path
import sys

from PIL import Image
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from core.state_manager import StateManager


TASK_ID = "ag_grid_audit_view_french"
TASK_QUERY = "AG Grid: Build an audit view (quick filter French, pin Language left, sort Balance high to low)"
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
            reasoning="Baseline grid before building the audit view"
        )

        quick_filter = page.locator("#global-filter")
        await quick_filter.fill("French")
        await quick_filter.press("Enter")
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="filter",
            description="Applied global quick filter for 'French'",
            target="#global-filter",
            reasoning="Focused the grid on rows containing the term 'French'"
        )

        menu_button = page.locator("div[col-id='language'] .ag-header-cell-menu-button").first
        await menu_button.click()
        await page.locator(".ag-menu-option:has-text('Pin Column')").first.hover()
        await page.wait_for_timeout(200)
        await page.locator(".ag-menu-option:has-text('Pin Left')").first.click()
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="pin",
            description="Pinned the Language column to the left",
            target="Language column menu",
            reasoning="Keeps Language visible while auditing filtered data"
        )

        balance_header = page.locator(".ag-header-cell[col-id='bankBalance']").first
        await balance_header.click()
        await balance_header.click()
        await page.wait_for_timeout(800)
        await capture_step(
            action_type="sort",
            description="Sorted Bank Balance column descending",
            target="Bank Balance header",
            reasoning="Shows highest balances at the top of the filtered, pinned view"
        )

        await browser.close()

    state_manager.end_workflow(success=True)


if __name__ == "__main__":
    asyncio.run(main())

