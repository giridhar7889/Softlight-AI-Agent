"""Configuration management for the SoftLight system."""

import os
import platform
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class AppConfig(BaseModel):
    """Configuration for a single app."""
    name: str
    base_url: str
    workspace: str = ""
    team: str = ""
    login_required: bool = True
    login_url: Optional[str] = None
    wait_after_action: float = 1.0
    wait_for_navigation: float = 3.0
    page_load_timeout: int = 30000
    action_timeout: int = 7000
    change_threshold: float = 0.15
    selectors: Dict[str, str] = Field(default_factory=dict)
    ignore_regions: list = Field(default_factory=list)


class TaskConfig(BaseModel):
    """Configuration for a single task."""
    id: str
    app: str
    query: str
    description: str = ""
    max_steps: int = 15
    start_url: Optional[str] = None


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.config_dir = self.root_dir / "config"
        self.dataset_dir = Path(os.getenv("DATASET_PATH", str(self.root_dir / "dataset")))
        
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # App Credentials
        self.linear_email = os.getenv("LINEAR_EMAIL")
        self.linear_password = os.getenv("LINEAR_PASSWORD")
        self.notion_email = os.getenv("NOTION_EMAIL")
        self.notion_password = os.getenv("NOTION_PASSWORD")
        
        # General Settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.headless = os.getenv("HEADLESS", "false").lower() == "true"
        self.screenshot_quality = int(os.getenv("SCREENSHOT_QUALITY", "95"))
        self.max_steps_per_task = int(os.getenv("MAX_STEPS_PER_TASK", "15"))
        self.ui_change_threshold = float(os.getenv("UI_CHANGE_THRESHOLD", "0.15"))
        default_browser = "chromium"
        if platform.system().lower() == "darwin":
            default_browser = "webkit"
        self.browser_type = os.getenv("PLAYWRIGHT_BROWSER", default_browser)
        
        # Load app and task configs
        self.apps: Dict[str, AppConfig] = self._load_apps()
        self.tasks: Dict[str, TaskConfig] = self._load_tasks()
        
        # Create necessary directories
        self._ensure_directories()
    
    def _load_apps(self) -> Dict[str, AppConfig]:
        """Load app configurations from YAML."""
        apps_file = self.config_dir / "apps.yaml"
        if not apps_file.exists():
            return {}
        
        with open(apps_file, 'r') as f:
            apps_data = yaml.safe_load(f)
        
        apps = {}
        for app_id, app_data in apps_data.items():
            if app_id != 'default':
                try:
                    apps[app_id] = AppConfig(**app_data)
                except Exception as e:
                    print(f"Warning: Failed to load config for {app_id}: {e}")
        
        return apps
    
    def _load_tasks(self) -> Dict[str, TaskConfig]:
        """Load task configurations from YAML."""
        tasks_file = self.config_dir / "tasks.yaml"
        if not tasks_file.exists():
            return {}
        
        with open(tasks_file, 'r') as f:
            tasks_data = yaml.safe_load(f)
        
        tasks = {}
        for task_data in tasks_data.get('tasks', []):
            try:
                task = TaskConfig(**task_data)
                tasks[task.id] = task
            except Exception as e:
                print(f"Warning: Failed to load task {task_data.get('id')}: {e}")
        
        return tasks
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        (self.root_dir / "logs").mkdir(exist_ok=True)
    
    def get_app_config(self, app_name: str) -> Optional[AppConfig]:
        """Get configuration for a specific app."""
        return self.apps.get(app_name.lower())
    
    def get_task_config(self, task_id: str) -> Optional[TaskConfig]:
        """Get configuration for a specific task."""
        return self.tasks.get(task_id)
    
    def get_credentials(self, app_name: str) -> Optional[Dict[str, str]]:
        """Get credentials for a specific app."""
        app_name = app_name.lower()
        if app_name == "linear":
            return {
                "email": self.linear_email,
                "password": self.linear_password
            }
        elif app_name == "notion":
            return {
                "email": self.notion_email,
                "password": self.notion_password
            }
        return None


# Global config instance
config = Config()

