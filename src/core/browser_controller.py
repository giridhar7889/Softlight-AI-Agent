"""Browser automation controller using Playwright."""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    BrowserContext,
    ElementHandle,
    Locator,
    TimeoutError as PlaywrightTimeoutError,
)
from PIL import Image
import io

from utils import log, config, AppConfig


class BrowserController:
    """Manages browser automation using Playwright."""
    
    def __init__(
        self,
        app_config: AppConfig,
        headless: bool = False,
        browser_type: str = "chromium"
    ):
        """
        Initialize the browser controller.
        
        Args:
            app_config: Configuration for the target app
            headless: Whether to run browser in headless mode
        """
        self.app_config = app_config
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.action_timeout = getattr(app_config, "action_timeout", 7000)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start the browser."""
        log.info(f"Starting browser for {self.app_config.name}")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser with appropriate settings
        self.browser, actual_type = await self._launch_browser(self.browser_type)
        self.browser_type = actual_type
    async def _launch_browser(self, browser_type: str) -> Tuple[Browser, str]:
        """Launch the requested browser type, falling back if needed."""
        browser_map = {
            "chromium": self.playwright.chromium,
            "firefox": self.playwright.firefox,
            "webkit": self.playwright.webkit,
        }
        target = browser_map.get(browser_type.lower())
        if not target:
            log.warning(f"Unknown browser_type '{browser_type}', defaulting to Chromium")
            target = self.playwright.chromium
            browser_type = "chromium"
        
        try:
            log.info(f"Launching Playwright browser: {browser_type}")
            browser = await target.launch(headless=self.headless)
            return browser, browser_type
        except Exception as launch_error:
            log.error(f"Failed to launch {browser_type}: {launch_error}")
            if browser_type == "chromium":
                log.info("Attempting fallback to WebKit")
                browser = await self.playwright.webkit.launch(headless=self.headless)
                return browser, "webkit"
            raise
        
        await self._create_context_and_page()
        
        log.info("Browser started successfully")
    
    async def close(self):
        """Close the browser and cleanup."""
        log.info("Closing browser")
        
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def _create_context_and_page(self):
        """Create a fresh browser context and page."""
        if not self.browser:
            return
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        self.context.set_default_timeout(self.app_config.page_load_timeout)
        self.page = await self.context.new_page()
    
    async def _ensure_page(self):
        """Ensure a valid page exists before interacting."""
        if self.page and not self.page.is_closed():
            return
        if not self.context:
            await self._create_context_and_page()
            return
        try:
            self.page = await self.context.new_page()
        except Exception:
            await self._create_context_and_page()
    
    async def navigate(self, url: str, wait_until: str = "networkidle") -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: When to consider navigation successful
                       ("load", "domcontentloaded", "networkidle")
        
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            await self._ensure_page()
            log.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until=wait_until)
            await asyncio.sleep(self.app_config.wait_for_navigation)
            return True
        except Exception as e:
            log.error(f"Navigation failed: {e}")
            return False
    
    async def take_screenshot(self, output_path: Optional[Path] = None) -> Image.Image:
        """
        Take a screenshot of the current page.
        
        Args:
            output_path: Optional path to save screenshot
        
        Returns:
            PIL Image object
        """
        await self._ensure_page()
        screenshot_bytes = await self.page.screenshot(full_page=False)
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        if output_path:
            image.save(output_path, quality=config.screenshot_quality)
        
        return image
    
    async def wait_for_stability(self, timeout: float = 2.0):
        """Wait for page to become stable (no major DOM changes)."""
        await asyncio.sleep(timeout)
    
    async def click_element(self, selector: Optional[str] = None, 
                           coordinates: Optional[Tuple[int, int]] = None,
                           description: str = "") -> bool:
        """
        Click an element either by selector or coordinates.
        
        Args:
            selector: CSS selector for element
            coordinates: (x, y) coordinates to click
            description: Human-readable description of element
        
        Returns:
            True if click successful, False otherwise
        """
        try:
            await self._ensure_page()
            if selector:
                locator = self.page.locator(selector)
                return await self._click_locator(locator, description or selector)
            elif coordinates:
                log.info(f"Clicking at coordinates: {coordinates} ({description})")
                await self.page.mouse.click(coordinates[0], coordinates[1])
            else:
                log.error("Must provide either selector or coordinates")
                return False
            
            await asyncio.sleep(self.app_config.wait_after_action)
            return True
            
        except Exception as e:
            log.error(f"Click failed: {e}")
            return False
    
    async def type_text(self, selector: str, text: str, description: str = "") -> bool:
        """
        Type text into an input field.
        
        Args:
            selector: CSS selector for input element
            text: Text to type
            description: Human-readable description
        
        Returns:
            True if typing successful, False otherwise
        """
        try:
            await self._ensure_page()
            log.info(f"Typing into: {description or selector}")
            locator = self.page.locator(selector)
            if not await self._prepare_locator(locator, description or selector):
                return False
            
            try:
                await locator.fill(text, timeout=self.action_timeout)
            except Exception as first_error:
                log.warning(f"Direct fill failed ({description or selector}): {first_error}")
                try:
                    await locator.click(timeout=self.action_timeout, force=True)
                    await locator.fill(text, timeout=self.action_timeout)
                except Exception as second_error:
                    log.warning(f"Fallback fill failed, trying keyboard typing: {second_error}")
                    try:
                        await locator.focus()
                        await self.page.keyboard.type(text, delay=50)
                    except Exception as final_error:
                        log.error(f"Typing failed: {final_error}")
                        return False
            
            await asyncio.sleep(self.app_config.wait_after_action)
            return True
        except Exception as e:
            log.error(f"Typing failed: {e}")
            return False
    
    async def press_key(self, key: str) -> bool:
        """
        Press a keyboard key.
        
        Args:
            key: Key to press (e.g., "Enter", "Escape", "Tab")
        
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_page()
            log.info(f"Pressing key: {key}")
            await self.page.keyboard.press(key)
            await asyncio.sleep(self.app_config.wait_after_action)
            return True
        except Exception as e:
            log.error(f"Key press failed: {e}")
            return False
    
    async def hover_element(self, selector: str, description: str = "") -> bool:
        """
        Hover over an element.
        
        Args:
            selector: CSS selector for element
            description: Human-readable description
        
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_page()
            log.info(f"Hovering over: {description or selector}")
            await self.page.hover(selector)
            await asyncio.sleep(self.app_config.wait_after_action)
            return True
        except Exception as e:
            log.error(f"Hover failed: {e}")
            return False
    
    async def scroll(self, direction: str = "down", amount: int = 500) -> bool:
        """
        Scroll the page.
        
        Args:
            direction: "up" or "down"
            amount: Pixels to scroll
        
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_page()
            log.info(f"Scrolling {direction} by {amount}px")
            if direction == "down":
                await self.page.mouse.wheel(0, amount)
            else:
                await self.page.mouse.wheel(0, -amount)
            await asyncio.sleep(self.app_config.wait_after_action)
            return True
        except Exception as e:
            log.error(f"Scroll failed: {e}")
            return False
    
    async def get_page_info(self) -> Dict[str, Any]:
        """
        Get information about the current page.
        
        Returns:
            Dictionary with page information
        """
        await self._ensure_page()
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "viewport": self.page.viewport_size
        }

    async def get_page_text(self) -> str:
        """
        Get the visible text content of the current page.
        
        Returns:
            The textual content of the <body> element.
        """
        try:
            return await self.page.inner_text("body", timeout=2000)
        except Exception as e:
            log.warning(f"Failed to get page text: {e}")
            return ""
    
    async def wait_for_selector(self, selector: str, timeout: float = 5000) -> bool:
        """
        Wait for a selector to appear.
        
        Args:
            selector: CSS selector to wait for
            timeout: Maximum time to wait in milliseconds
        
        Returns:
            True if element appeared, False otherwise
        """
        try:
            await self._ensure_page()
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            log.warning(f"Selector not found: {selector}")
            return False
    
    async def get_element_info(self, selector: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an element.
        
        Args:
            selector: CSS selector for element
        
        Returns:
            Dictionary with element information or None if not found
        """
        try:
            await self._ensure_page()
            element = await self.page.query_selector(selector)
            if not element:
                return None
            
            box = await element.bounding_box()
            return {
                "selector": selector,
                "text": await element.text_content(),
                "visible": await element.is_visible(),
                "bounding_box": box
            }
        except Exception as e:
            log.warning(f"Failed to get element info: {e}")
            return None
    
    async def find_elements_by_text(self, text: str, tag: str = "*") -> List[Dict[str, Any]]:
        """
        Find elements containing specific text.
        
        Args:
            text: Text to search for
            tag: HTML tag to limit search (default: any tag)
        
        Returns:
            List of element information dictionaries
        """
        try:
            await self._ensure_page()
            # Use XPath to find elements containing text
            xpath = f"//{tag}[contains(text(), '{text}')]"
            elements = await self.page.query_selector_all(f"xpath={xpath}")
            
            results = []
            for element in elements:
                if await element.is_visible():
                    box = await element.bounding_box()
                    if box:
                        results.append({
                            "text": await element.text_content(),
                            "tag": await element.evaluate("el => el.tagName"),
                            "bounding_box": box
                        })
            
            return results
        except Exception as e:
            log.warning(f"Failed to find elements by text: {e}")
            return []
    
    async def get_accessibility_tree(self) -> Optional[Dict[str, Any]]:
        """
        Get the accessibility tree snapshot of the page.
        Useful for understanding page structure.
        
        Returns:
            Accessibility tree data or None if failed
        """
        try:
            await self._ensure_page()
            snapshot = await self.page.accessibility.snapshot()
            return snapshot
        except Exception as e:
            log.warning(f"Failed to get accessibility tree: {e}")
            return None
    
    async def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript on the page.
        
        Args:
            script: JavaScript code to execute
        
        Returns:
            Result of script execution
        """
        try:
            await self._ensure_page()
            return await self.page.evaluate(script)
        except Exception as e:
            log.error(f"Script execution failed: {e}")
            return None
    
    async def inject_som_labels(self) -> Dict[str, Any]:
        """
        Inject Set-of-Marks labels on all interactive elements.
        This is the key innovation for autonomous web agents.
        
        Returns:
            Dictionary with element count and mapping
        """
        label_script = """
        () => {
            // Remove any existing labels
            document.querySelectorAll('.som-label, .som-overlay').forEach(el => el.remove());
            
            // Find all potentially interactive elements
            const interactiveSelectors = [
                'button',
                'a[href]',
                'input:not([type="hidden"])',
                'textarea',
                'select',
                '[role="button"]',
                '[role="link"]',
                '[role="menuitem"]',
                '[role="tab"]',
                '[role="option"]',
                '[contenteditable="true"]',
                '[onclick]',
                'label[for]',
                '[tabindex]:not([tabindex="-1"])'
            ];
            
            const elements = document.querySelectorAll(interactiveSelectors.join(', '));
            const elementMap = [];
            let labelIndex = 0;
            
            elements.forEach((el) => {
                // Only label visible and interactable elements
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                
                const isVisible = (
                    rect.width > 0 &&
                    rect.height > 0 &&
                    style.visibility !== 'hidden' &&
                    style.display !== 'none' &&
                    style.opacity !== '0' &&
                    rect.top < window.innerHeight &&
                    rect.bottom > 0 &&
                    rect.left < window.innerWidth &&
                    rect.right > 0
                );
                
                if (!isVisible) return;
                
                // Store element reference
                el.setAttribute('data-som-id', labelIndex);
                
                // Create visual label overlay
                const label = document.createElement('div');
                label.className = 'som-label';
                label.textContent = labelIndex;
                label.style.cssText = `
                    position: fixed;
                    left: ${rect.left + window.scrollX}px;
                    top: ${rect.top + window.scrollY}px;
                    background: rgba(255, 0, 0, 0.9);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: monospace;
                    z-index: 2147483647;
                    pointer-events: none;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                `;
                
                document.body.appendChild(label);
                
                // Store element info for reference
                elementMap.push({
                    id: labelIndex,
                    tagName: el.tagName.toLowerCase(),
                    text: el.innerText?.slice(0, 100) || el.value || el.placeholder || '',
                    type: el.type || '',
                    role: el.getAttribute('role') || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    href: el.href || '',
                    x: Math.round(rect.left),
                    y: Math.round(rect.top),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                });
                
                labelIndex++;
            });
            
            return {
                count: labelIndex,
                elements: elementMap
            };
        }
        """
        
        try:
            await self._ensure_page()
            result = await self.page.evaluate(label_script)
            log.info(f"✓ Injected SoM labels on {result['count']} interactive elements")
            return result
        except Exception as e:
            log.error(f"Failed to inject SoM labels: {e}")
            return {"count": 0, "elements": []}
    
    async def remove_som_labels(self):
        """Remove all Set-of-Marks labels from the page."""
        remove_script = """
        () => {
            document.querySelectorAll('.som-label, .som-overlay').forEach(el => el.remove());
        }
        """
        try:
            await self._ensure_page()
            await self.page.evaluate(remove_script)
            log.debug("Removed SoM labels")
        except Exception as e:
            log.warning(f"Failed to remove SoM labels: {e}")
    
    def _som_selector(self, element_id: int) -> str:
        """Return the selector for a Set-of-Marks element."""
        return f'[data-som-id="{element_id}"]'
    
    def _som_locator(self, element_id: int) -> Locator:
        """Return a locator for a Set-of-Marks element."""
        return self.page.locator(self._som_selector(element_id)).first
    
    async def _prepare_locator(self, locator: Locator, description: str = "") -> bool:
        """Ensure a locator is visible and ready for interaction."""
        try:
            await locator.wait_for(state="visible", timeout=self.action_timeout)
        except PlaywrightTimeoutError as e:
            log.error(f"Element not visible in time ({description}): {e}")
            return False
        except Exception as e:
            log.error(f"Failed waiting for element ({description}): {e}")
            return False
        
        try:
            await locator.scroll_into_view_if_needed(timeout=self.action_timeout)
        except Exception as e:
            log.debug(f"Scroll into view skipped ({description}): {e}")
        
        try:
            await locator.hover(timeout=min(1500, self.action_timeout))
        except Exception:
            # Hover can fail for elements that do not accept pointer events; that's fine
            pass
        
        return True
    
    async def _click_via_mouse(self, locator: Locator, description: str = "") -> bool:
        """Fallback click using mouse coordinates."""
        try:
            handle = await locator.element_handle()
            if not handle:
                log.error(f"Cannot fallback-click {description}: element handle missing")
                return False
            
            box = await handle.bounding_box()
            if not box:
                log.error(f"Cannot fallback-click {description}: no bounding box")
                return False
            
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            log.info(f"Fallback clicking via mouse at ({x}, {y}) for {description}")
            await self.page.mouse.click(x, y)
            await asyncio.sleep(self.app_config.wait_after_action)
            return True
        except Exception as e:
            log.error(f"Fallback mouse click failed for {description}: {e}")
            return False
    
    async def _click_locator(self, locator: Locator, description: str = "") -> bool:
        """Attempt to click a locator with retries and fallbacks."""
        if not await self._prepare_locator(locator, description):
            return False
        
        for attempt in range(2):
            force = attempt == 1
            try:
                await locator.click(timeout=self.action_timeout, force=force)
                await asyncio.sleep(self.app_config.wait_after_action)
                return True
            except PlaywrightTimeoutError as e:
                log.warning(f"Click timed out ({description}) attempt {attempt + 1}: {e}")
            except Exception as e:
                log.warning(f"Click failed ({description}) attempt {attempt + 1}: {e}")
        
        # Final fallback using mouse coordinates
        return await self._click_via_mouse(locator, description)
    
    async def click_by_som_id(self, element_id: int, description: str = "") -> bool:
        """
        Click an element by its Set-of-Marks ID.
        This is more reliable than selector-based clicking.
        
        Args:
            element_id: The SoM ID of the element
            description: Human-readable description
        
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_page()
            log.info(f"Clicking SoM element #{element_id}: {description}")
            locator = self._som_locator(element_id)
            return await self._click_locator(locator, description or f"SoM #{element_id}")
        except Exception as e:
            log.error(f"Failed to click SoM element #{element_id}: {e}")
            return False
    
    async def type_by_som_id(self, element_id: int, text: str, description: str = "") -> bool:
        """
        Type text into an element by its Set-of-Marks ID.
        
        Args:
            element_id: The SoM ID of the element
            text: Text to type
            description: Human-readable description
        
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_page()
            log.info(f"Typing into SoM element #{element_id}: {description}")
            locator = self._som_locator(element_id)
            if not await self._prepare_locator(locator, description or f"SoM #{element_id}"):
                return False
            
            try:
                await locator.fill(text, timeout=self.action_timeout)
            except Exception as first_error:
                log.warning(f"Direct SoM fill failed: {first_error}")
                try:
                    await locator.click(timeout=self.action_timeout, force=True)
                    await locator.fill(text, timeout=self.action_timeout)
                except Exception as second_error:
                    log.warning(f"SoM fill retry failed, attempting keyboard input: {second_error}")
                    try:
                        await locator.focus()
                        await self.page.keyboard.type(text, delay=50)
                    except Exception as final_error:
                        log.error(f"Failed typing into SoM element #{element_id}: {final_error}")
                        return False
            
            await asyncio.sleep(self.app_config.wait_after_action)
            return True
        except Exception as e:
            log.error(f"Failed to type into SoM element #{element_id}: {e}")
            return False
    
    async def get_som_element_info(self, element_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific SoM element.
        
        Args:
            element_id: The SoM ID of the element
        
        Returns:
            Element information or None if not found
        """
        await self._ensure_page()
        script = f"""
        () => {{
            const el = document.querySelector('[data-som-id="{element_id}"]');
            if (!el) return null;
            
            const rect = el.getBoundingClientRect();
            return {{
                tagName: el.tagName.toLowerCase(),
                text: el.innerText?.slice(0, 200) || el.value || '',
                type: el.type || '',
                placeholder: el.placeholder || '',
                href: el.href || '',
                disabled: el.disabled || false,
                visible: rect.width > 0 && rect.height > 0
            }};
        }}
        """
        
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            log.warning(f"Failed to get SoM element info: {e}")
            return None

