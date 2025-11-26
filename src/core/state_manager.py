"""State capture and storage management system."""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from PIL import Image
from dataclasses import dataclass, asdict

from utils import log, config, ImageProcessor


@dataclass
class CapturedStep:
    """Represents a single captured step in a workflow."""
    step_number: int
    description: str
    action_type: str
    action_target: str
    screenshot_path: str
    url: str
    timestamp: str
    reasoning: str = ""
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.metadata is None:
            data['metadata'] = {}
        return data


@dataclass
class WorkflowDataset:
    """Represents a complete workflow dataset."""
    task_id: str
    task_query: str
    app_name: str
    start_url: str
    timestamp: str
    steps: List[CapturedStep]
    total_steps: int
    duration_seconds: float
    success: bool
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_query": self.task_query,
            "app_name": self.app_name,
            "start_url": self.start_url,
            "timestamp": self.timestamp,
            "steps": [step.to_dict() for step in self.steps],
            "total_steps": self.total_steps,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_message": self.error_message
        }


class StateManager:
    """Manages capture and storage of UI states."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the state manager.
        
        Args:
            base_path: Base directory for dataset storage
        """
        self.base_path = base_path or config.dataset_dir
        self.image_processor = ImageProcessor()
        
        self.current_workflow: Optional[str] = None
        self.current_path: Optional[Path] = None
        self.captured_steps: List[CapturedStep] = []
        self.start_time: Optional[datetime] = None
        
    def start_workflow(
        self,
        app_name: str,
        task_id: str,
        task_query: str
    ) -> Path:
        """
        Start a new workflow capture session.
        
        Args:
            app_name: Name of the application
            task_id: Unique task identifier
            task_query: The task being performed
        
        Returns:
            Path to the workflow directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workflow_name = f"{task_id}_{timestamp}"
        
        self.current_workflow = workflow_name
        self.current_path = self.base_path / app_name / workflow_name
        self.current_path.mkdir(parents=True, exist_ok=True)
        
        self.captured_steps = []
        self.start_time = datetime.now()
        
        log.info(f"Started workflow capture: {self.current_path}")
        
        # Save initial metadata
        metadata = {
            "task_id": task_id,
            "task_query": task_query,
            "app_name": app_name,
            "workflow_name": workflow_name,
            "start_time": self.start_time.isoformat(),
            "status": "in_progress"
        }
        
        metadata_path = self.current_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return self.current_path
    
    def capture_step(
        self,
        screenshot: Image.Image,
        description: str,
        action_type: str,
        action_target: str,
        url: str,
        reasoning: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CapturedStep:
        """
        Capture a single step in the workflow.
        
        Args:
            screenshot: Screenshot of this step
            description: Human-readable description
            action_type: Type of action performed
            action_target: What was acted upon
            url: Current page URL
            reasoning: Why this action was taken
            metadata: Additional metadata
        
        Returns:
            CapturedStep object
        """
        if not self.current_path:
            raise RuntimeError("No workflow started. Call start_workflow() first.")
        
        step_number = len(self.captured_steps) + 1
        screenshot_filename = f"step_{step_number:02d}_{action_type}.png"
        screenshot_path = self.current_path / screenshot_filename
        
        # Save screenshot
        self.image_processor.save_image(
            screenshot,
            screenshot_path,
            quality=config.screenshot_quality
        )
        
        log.info(f"Captured step {step_number}: {description}")
        
        # Create step object
        step = CapturedStep(
            step_number=step_number,
            description=description,
            action_type=action_type,
            action_target=action_target,
            screenshot_path=screenshot_filename,  # Relative path
            url=url,
            timestamp=datetime.now().isoformat(),
            reasoning=reasoning,
            metadata=metadata or {}
        )
        
        self.captured_steps.append(step)
        
        # Update metadata file incrementally
        self._update_metadata()
        
        return step
    
    def _update_metadata(self):
        """Update the metadata file with current progress."""
        if not self.current_path:
            return
        
        metadata_path = self.current_path / "metadata.json"
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Update with current progress
            metadata.update({
                "total_steps": len(self.captured_steps),
                "last_update": datetime.now().isoformat(),
                "steps": [step.to_dict() for step in self.captured_steps]
            })
            
            if self.start_time:
                duration = (datetime.now() - self.start_time).total_seconds()
                metadata["duration_seconds"] = duration
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            log.error(f"Failed to update metadata: {e}")
    
    def end_workflow(
        self,
        success: bool = True,
        error_message: str = ""
    ) -> WorkflowDataset:
        """
        End the current workflow and finalize dataset.
        
        Args:
            success: Whether the workflow completed successfully
            error_message: Error message if failed
        
        Returns:
            WorkflowDataset object
        """
        if not self.current_path or not self.start_time:
            raise RuntimeError("No workflow in progress")
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        log.info(f"Ending workflow: {self.current_workflow} (success={success})")
        
        # Load metadata
        metadata_path = self.current_path / "metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Create workflow dataset
        dataset = WorkflowDataset(
            task_id=metadata["task_id"],
            task_query=metadata["task_query"],
            app_name=metadata["app_name"],
            start_url=metadata.get("start_url", ""),
            timestamp=metadata["start_time"],
            steps=self.captured_steps,
            total_steps=len(self.captured_steps),
            duration_seconds=duration,
            success=success,
            error_message=error_message
        )
        
        # Save final metadata
        metadata.update({
            "status": "completed" if success else "failed",
            "success": success,
            "error_message": error_message,
            "duration_seconds": duration,
            "total_steps": len(self.captured_steps),
            "end_time": datetime.now().isoformat()
        })
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create a summary README
        self._create_readme(dataset)
        
        # Reset state
        self.current_workflow = None
        self.current_path = None
        self.captured_steps = []
        self.start_time = None
        
        return dataset
    
    def _create_readme(self, dataset: WorkflowDataset):
        """Create a README file for the workflow."""
        readme_path = self.current_path / "README.md"
        
        content = f"""# {dataset.task_query}

## Workflow Information

- **Task ID**: {dataset.task_id}
- **App**: {dataset.app_name}
- **Timestamp**: {dataset.timestamp}
- **Duration**: {dataset.duration_seconds:.2f} seconds
- **Total Steps**: {dataset.total_steps}
- **Status**: {'✅ Success' if dataset.success else '❌ Failed'}

## Steps

"""
        
        for step in dataset.steps:
            content += f"""### Step {step.step_number}: {step.description}

- **Action**: {step.action_type}
- **Target**: {step.action_target}
- **URL**: {step.url}
- **Screenshot**: `{step.screenshot_path}`
- **Reasoning**: {step.reasoning}

"""
        
        with open(readme_path, 'w') as f:
            f.write(content)
    
    def get_current_step_count(self) -> int:
        """Get the number of steps captured so far."""
        return len(self.captured_steps)
    
    def get_last_step(self) -> Optional[CapturedStep]:
        """Get the most recently captured step."""
        return self.captured_steps[-1] if self.captured_steps else None
    
    def export_dataset(
        self,
        output_path: Path,
        format: str = "json"
    ) -> Path:
        """
        Export the dataset in a specific format.
        
        Args:
            output_path: Where to export
            format: Export format ("json", "jsonl", or "archive")
        
        Returns:
            Path to exported file
        """
        if not self.current_path:
            raise RuntimeError("No workflow to export")
        
        if format == "json":
            # Copy the metadata.json
            shutil.copy(
                self.current_path / "metadata.json",
                output_path
            )
        elif format == "archive":
            # Create a zip archive of the entire workflow
            shutil.make_archive(
                str(output_path.with_suffix('')),
                'zip',
                self.current_path
            )
            output_path = output_path.with_suffix('.zip')
        
        log.info(f"Exported dataset to: {output_path}")
        return output_path
    
    @staticmethod
    def load_workflow(workflow_path: Path) -> WorkflowDataset:
        """
        Load a workflow dataset from disk.
        
        Args:
            workflow_path: Path to workflow directory
        
        Returns:
            WorkflowDataset object
        """
        metadata_path = workflow_path / "metadata.json"
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        steps = [
            CapturedStep(**step_data)
            for step_data in data.get("steps", [])
        ]
        
        return WorkflowDataset(
            task_id=data["task_id"],
            task_query=data["task_query"],
            app_name=data["app_name"],
            start_url=data.get("start_url", ""),
            timestamp=data["start_time"],
            steps=steps,
            total_steps=data["total_steps"],
            duration_seconds=data.get("duration_seconds", 0),
            success=data.get("success", True),
            error_message=data.get("error_message", "")
        )
    
    def get_all_workflows(self, app_name: Optional[str] = None) -> List[Path]:
        """
        Get all workflow directories.
        
        Args:
            app_name: Filter by app name (optional)
        
        Returns:
            List of workflow directory paths
        """
        if app_name:
            search_path = self.base_path / app_name
        else:
            search_path = self.base_path
        
        workflows = []
        for path in search_path.rglob("metadata.json"):
            workflows.append(path.parent)
        
        return sorted(workflows)

