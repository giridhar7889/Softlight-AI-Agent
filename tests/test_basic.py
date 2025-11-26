"""Basic tests to verify the system is working."""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import config, ImageProcessor
from core import Action


def test_config_loaded():
    """Test that configuration loads successfully."""
    assert config is not None
    assert config.root_dir.exists()


def test_apps_config():
    """Test that apps are configured."""
    assert len(config.apps) > 0
    assert "linear" in config.apps


def test_tasks_config():
    """Test that tasks are configured."""
    assert len(config.tasks) > 0


def test_image_processor():
    """Test basic image processing functions."""
    processor = ImageProcessor()
    assert processor is not None


def test_action_creation():
    """Test Action object creation."""
    action = Action(
        action_type="click",
        description="Test action",
        selector="button",
        reasoning="Testing"
    )
    assert action.action_type == "click"
    assert action.description == "Test action"
    
    # Test to_dict
    action_dict = action.to_dict()
    assert action_dict["action_type"] == "click"


def test_dataset_directory_exists():
    """Test that dataset directory exists."""
    assert config.dataset_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

