"""Base adapter interface for web applications."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from playwright.async_api import Page

from utils import log, AppConfig


class BaseAdapter(ABC):
    """Base class for application-specific adapters."""
    
    def __init__(self, app_config: AppConfig):
        """
        Initialize the adapter.
        
        Args:
            app_config: Configuration for this app
        """
        self.app_config = app_config
    
    @abstractmethod
    def get_base_url(self) -> str:
        """
        Get the base URL for the application.
        
        Returns:
            Base URL string
        """
        pass
    
    @abstractmethod
    async def setup_authentication(self, page: Page, credentials: Dict[str, str]) -> bool:
        """
        Handle authentication for the application.
        
        Args:
            page: Playwright page object
            credentials: Dictionary with authentication credentials
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    def get_initial_context(self) -> Dict[str, Any]:
        """
        Get initial context information about the app.
        This helps the LLM understand the app structure.
        
        Returns:
            Dictionary with context information
        """
        return {
            "app_name": self.app_config.name,
            "base_url": self.get_base_url()
        }
    
    def get_common_selectors(self) -> Dict[str, str]:
        """
        Get common CSS selectors for this app.
        
        Returns:
            Dictionary mapping element names to selectors
        """
        return self.app_config.selectors
    
    async def pre_task_setup(self, page: Page) -> bool:
        """
        Perform any setup needed before starting a task.
        
        Args:
            page: Playwright page object
        
        Returns:
            True if setup successful, False otherwise
        """
        return True
    
    async def post_task_cleanup(self, page: Page) -> bool:
        """
        Perform any cleanup after completing a task.
        
        Args:
            page: Playwright page object
        
        Returns:
            True if cleanup successful, False otherwise
        """
        return True
    
    def get_element_hints(self, task_query: str) -> Dict[str, Any]:
        """
        Get hints about relevant elements for a specific task.
        This helps the LLM find the right elements faster.
        
        Args:
            task_query: The task being performed
        
        Returns:
            Dictionary with hints
        """
        return {}

