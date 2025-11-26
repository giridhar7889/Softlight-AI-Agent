"""Application adapters for different web apps."""

from adapters.base_adapter import BaseAdapter
from adapters.linear_adapter import LinearAdapter
from adapters.notion_adapter import NotionAdapter

__all__ = [
    'BaseAdapter',
    'LinearAdapter',
    'NotionAdapter'
]


def get_adapter(app_name: str, app_config) -> BaseAdapter:
    """
    Get the appropriate adapter for an app.
    
    Args:
        app_name: Name of the app
        app_config: Configuration for the app
    
    Returns:
        Adapter instance
    """
    app_name = app_name.lower()
    
    if app_name == "linear":
        return LinearAdapter(app_config)
    elif app_name == "notion":
        return NotionAdapter(app_config)
    else:
        # Return base adapter for unknown apps
        return BaseAdapter(app_config)

