"""Adapter for Linear app (linear.app)."""

import asyncio
from typing import Dict, Any
from playwright.async_api import Page

from adapters.base_adapter import BaseAdapter
from utils import log, AppConfig


class LinearAdapter(BaseAdapter):
    """Adapter for Linear project management tool."""
    
    def get_base_url(self) -> str:
        """Get the base URL for Linear."""
        workspace = self.app_config.workspace
        team = self.app_config.team
        
        if workspace and team:
            return f"https://linear.app/{workspace}/team/{team}/active"
        return "https://linear.app"
    
    async def setup_authentication(self, page: Page, credentials: Dict[str, str]) -> bool:
        """
        Handle Linear authentication.
        
        Note: Linear uses various auth methods. For production, you'd want to use
        stored session cookies. This is a basic email/password flow.
        
        Args:
            page: Playwright page
            credentials: Dict with 'email' and 'password'
        
        Returns:
            True if authentication successful
        """
        try:
            log.info("Setting up Linear authentication")
            
            # Navigate to login page
            await page.goto(self.app_config.login_url or "https://linear.app/login")
            await asyncio.sleep(2)
            
            # Check if already logged in
            if "linear.app/login" not in page.url:
                log.info("Already authenticated")
                return True
            
            email = credentials.get("email")
            password = credentials.get("password")
            
            if not email or not password:
                log.warning("No credentials provided, manual login may be required")
                # Wait for manual login
                await page.wait_for_url("**/linear.app/**", timeout=60000)
                return True
            
            # Fill in email
            email_input = await page.wait_for_selector("input[type='email']", timeout=5000)
            await email_input.fill(email)
            
            # Click continue or submit
            continue_button = await page.query_selector("button:has-text('Continue')")
            if continue_button:
                await continue_button.click()
                await asyncio.sleep(1)
            
            # Fill in password
            password_input = await page.wait_for_selector("input[type='password']", timeout=5000)
            await password_input.fill(password)
            
            # Submit
            submit_button = await page.query_selector("button[type='submit']")
            if submit_button:
                await submit_button.click()
            
            # Wait for redirect
            await page.wait_for_url("**/linear.app/**", timeout=10000)
            
            log.info("Linear authentication successful")
            return True
            
        except Exception as e:
            log.error(f"Linear authentication failed: {e}")
            return False
    
    def get_initial_context(self) -> Dict[str, Any]:
        """Get Linear-specific context."""
        context = super().get_initial_context()
        context.update({
            "workspace": self.app_config.workspace,
            "team": self.app_config.team,
            "common_actions": [
                "Create project",
                "Create issue",
                "Filter issues",
                "Change status",
                "Assign issue",
                "Add label"
            ]
        })
        return context
    
    def get_element_hints(self, task_query: str) -> Dict[str, Any]:
        """Get hints for Linear-specific tasks."""
        query_lower = task_query.lower()
        
        hints = {}
        
        if "create" in query_lower and "project" in query_lower:
            hints = {
                "likely_elements": [
                    "button:has-text('New project')",
                    "button:has-text('Create project')",
                    "[aria-label='Create project']"
                ],
                "modal_selectors": [
                    "[role='dialog']",
                    ".modal",
                    "[data-radix-popper-content-wrapper]"
                ]
            }
        
        elif "create" in query_lower and "issue" in query_lower:
            hints = {
                "likely_elements": [
                    "button:has-text('New issue')",
                    "button:has-text('Create issue')",
                    "[aria-label='Create issue']",
                    "button:has-text('C')"  # Keyboard shortcut button
                ],
                "form_fields": [
                    "input[placeholder*='Issue title']",
                    "textarea[placeholder*='Add description']"
                ]
            }
        
        elif "filter" in query_lower:
            hints = {
                "likely_elements": [
                    "button:has-text('Filter')",
                    "[aria-label='Filter']",
                    ".filter-button"
                ],
                "dropdown_selectors": [
                    "[role='menu']",
                    "[role='listbox']"
                ]
            }
        
        elif "status" in query_lower:
            hints = {
                "likely_elements": [
                    "[data-status]",
                    ".status-button",
                    "button:has-text('Todo')",
                    "button:has-text('In Progress')",
                    "button:has-text('Done')"
                ]
            }
        
        return hints
    
    async def pre_task_setup(self, page: Page) -> bool:
        """Setup before starting a Linear task."""
        try:
            # Wait for Linear's main UI to load
            await page.wait_for_selector("[data-radix-scroll-area-viewport]", timeout=10000)
            log.info("Linear UI loaded")
            return True
        except Exception as e:
            log.warning(f"Linear pre-task setup issue: {e}")
            return True  # Continue anyway
    
    def get_common_selectors(self) -> Dict[str, str]:
        """Get common Linear selectors."""
        return {
            "create_project_button": "button:has-text('New project')",
            "create_issue_button": "button:has-text('New issue')",
            "filter_button": "button:has-text('Filter')",
            "search_input": "input[placeholder*='Search']",
            "modal": "[role='dialog']",
            "dropdown": "[role='menu']"
        }

