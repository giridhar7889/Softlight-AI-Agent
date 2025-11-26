"""Adapter for Notion (notion.so)."""

import asyncio
from typing import Dict, Any
from playwright.async_api import Page

from adapters.base_adapter import BaseAdapter
from utils import log, AppConfig


class NotionAdapter(BaseAdapter):
    """Adapter for Notion workspace."""
    
    def get_base_url(self) -> str:
        """Get the base URL for Notion."""
        workspace = self.app_config.workspace
        if workspace:
            return f"https://www.notion.so/{workspace}"
        return "https://www.notion.so"
    
    async def setup_authentication(self, page: Page, credentials: Dict[str, str]) -> bool:
        """
        Handle Notion authentication.
        
        Args:
            page: Playwright page
            credentials: Dict with 'email' and 'password'
        
        Returns:
            True if authentication successful
        """
        try:
            log.info("Setting up Notion authentication")
            
            # Navigate to login page
            await page.goto(self.app_config.login_url or "https://www.notion.so/login")
            await asyncio.sleep(2)
            
            # Check if already logged in
            current_url = page.url
            if "/login" not in current_url:
                log.info("Already authenticated")
                return True
            
            email = credentials.get("email")
            password = credentials.get("password")
            
            if not email or not password:
                log.warning("No credentials provided, manual login may be required")
                # Wait for manual login
                await page.wait_for_url("**/notion.so/**", timeout=60000)
                return True
            
            # Fill in email
            email_input = await page.wait_for_selector("input[type='email']", timeout=5000)
            await email_input.fill(email)
            
            # Click continue with email
            continue_button = await page.query_selector("button:has-text('Continue with email')")
            if continue_button:
                await continue_button.click()
                await asyncio.sleep(2)
            
            # Fill in password if present
            try:
                password_input = await page.wait_for_selector("input[type='password']", timeout=3000)
                await password_input.fill(password)
                
                # Submit
                submit_button = await page.query_selector("button:has-text('Continue')")
                if submit_button:
                    await submit_button.click()
            except:
                log.info("Password-less login flow")
            
            # Wait for redirect
            await page.wait_for_url("**/notion.so/**", timeout=15000)
            
            log.info("Notion authentication successful")
            return True
            
        except Exception as e:
            log.error(f"Notion authentication failed: {e}")
            return False
    
    def get_initial_context(self) -> Dict[str, Any]:
        """Get Notion-specific context."""
        context = super().get_initial_context()
        context.update({
            "workspace": self.app_config.workspace,
            "common_actions": [
                "Create page",
                "Create database",
                "Filter database",
                "Add property",
                "Add view",
                "Create block"
            ]
        })
        return context
    
    def get_element_hints(self, task_query: str) -> Dict[str, Any]:
        """Get hints for Notion-specific tasks."""
        query_lower = task_query.lower()
        
        hints = {}
        
        if "create" in query_lower and "database" in query_lower:
            hints = {
                "likely_elements": [
                    "button:has-text('Database')",
                    "[aria-label*='database']",
                    ".notion-focusable:has-text('Table')"
                ],
                "menu_selectors": [
                    "[role='menu']",
                    ".notion-menu"
                ]
            }
        
        elif "filter" in query_lower and "database" in query_lower:
            hints = {
                "likely_elements": [
                    "button:has-text('Filter')",
                    "[aria-label='Filter']",
                    ".notion-database-view-filter-button"
                ],
                "dropdown_selectors": [
                    "[role='menu']",
                    ".notion-dropdown"
                ]
            }
        
        elif "property" in query_lower or "add property" in query_lower:
            hints = {
                "likely_elements": [
                    "button:has-text('+')",
                    "[aria-label='Add property']",
                    ".notion-property-add-button"
                ],
                "property_types": [
                    "Select",
                    "Multi-select",
                    "Text",
                    "Number",
                    "Date"
                ]
            }
        
        elif "create" in query_lower and "page" in query_lower:
            hints = {
                "likely_elements": [
                    "button:has-text('New page')",
                    "[aria-label='New page']",
                    ".notion-focusable:has-text('Add a page')"
                ]
            }
        
        return hints
    
    async def pre_task_setup(self, page: Page) -> bool:
        """Setup before starting a Notion task."""
        try:
            # Wait for Notion's app to load
            await page.wait_for_selector(".notion-app-inner", timeout=10000)
            log.info("Notion UI loaded")
            
            # Additional wait for full hydration
            await asyncio.sleep(2)
            return True
        except Exception as e:
            log.warning(f"Notion pre-task setup issue: {e}")
            return True  # Continue anyway
    
    def get_common_selectors(self) -> Dict[str, str]:
        """Get common Notion selectors."""
        return {
            "new_page_button": "button:has-text('New page')",
            "add_block": "[placeholder='Type \\'\\' for commands']",
            "database_filter": "button:has-text('Filter')",
            "add_property": "button:has-text('+')",
            "menu": "[role='menu']",
            "modal": "[role='dialog']"
        }

