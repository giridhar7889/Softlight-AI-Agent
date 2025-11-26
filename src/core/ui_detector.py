"""UI change detection system for identifying when to capture screenshots."""

from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
from PIL import Image
from dataclasses import dataclass
from datetime import datetime

from utils import log, ImageProcessor


@dataclass
class UIState:
    """Represents a captured UI state."""
    screenshot: Image.Image
    hash: str
    timestamp: datetime
    metadata: Dict[str, Any]


class UIChangeDetector:
    """Detects significant changes in UI state."""
    
    def __init__(self, change_threshold: float = 0.15, method: str = "hash"):
        """
        Initialize the UI change detector.
        
        Args:
            change_threshold: Minimum difference to consider a change (0-1)
            method: Detection method ("hash" or "structural")
        """
        self.change_threshold = change_threshold
        self.method = method
        self.image_processor = ImageProcessor()
        
        self.current_state: Optional[UIState] = None
        self.state_history: List[UIState] = []
        
    def update_state(
        self,
        screenshot: Image.Image,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, str]:
        """
        Update the current UI state and check if there's a significant change.
        
        Args:
            screenshot: New screenshot to analyze
            metadata: Additional metadata about this state
        
        Returns:
            Tuple of (changed: bool, difference: float, reason: str)
        """
        # Compute hash of new screenshot
        new_hash = self.image_processor.compute_hash(screenshot)
        
        # Create new state
        new_state = UIState(
            screenshot=screenshot,
            hash=new_hash,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # If this is the first state, always consider it a change
        if self.current_state is None:
            log.info("First UI state - capturing")
            self.current_state = new_state
            self.state_history.append(new_state)
            return True, 1.0, "Initial state"
        
        # Compare with current state
        changed, difference = self.image_processor.detect_change(
            self.current_state.screenshot,
            screenshot,
            threshold=self.change_threshold,
            method=self.method
        )
        
        reason = self._determine_change_reason(difference, metadata)
        
        if changed:
            log.info(f"Significant UI change detected (diff: {difference:.3f})")
            self.current_state = new_state
            self.state_history.append(new_state)
        else:
            log.debug(f"No significant change (diff: {difference:.3f})")
        
        return changed, difference, reason
    
    def _determine_change_reason(
        self,
        difference: float,
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Determine the reason for a change based on metadata and difference."""
        
        if difference < self.change_threshold:
            return "No significant change"
        
        if metadata:
            action = metadata.get("action")
            if action:
                return f"Change after {action}"
        
        if difference > 0.5:
            return "Major UI change (navigation/modal)"
        elif difference > 0.3:
            return "Moderate UI change (content update)"
        else:
            return "Minor UI change (element interaction)"
    
    def should_capture(
        self,
        screenshot: Image.Image,
        force: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, str]:
        """
        Determine if this screenshot should be captured.
        
        Args:
            screenshot: Screenshot to evaluate
            force: Force capture regardless of change detection
            metadata: Additional context about this state
        
        Returns:
            Tuple of (should_capture: bool, difference: float, reason: str)
        """
        if force:
            log.info("Forced capture")
            return True, 1.0, "Forced capture"
        
        return self.update_state(screenshot, metadata)
    
    def reset(self):
        """Reset the detector state."""
        log.info("Resetting UI change detector")
        self.current_state = None
        self.state_history = []
    
    def get_state_count(self) -> int:
        """Get the number of captured states."""
        return len(self.state_history)
    
    def get_last_state(self) -> Optional[UIState]:
        """Get the most recent state."""
        return self.current_state
    
    def compare_with_previous(
        self,
        screenshot: Image.Image,
        steps_back: int = 1
    ) -> Tuple[bool, float]:
        """
        Compare screenshot with a previous state.
        
        Args:
            screenshot: Screenshot to compare
            steps_back: How many steps back to compare with
        
        Returns:
            Tuple of (different: bool, difference: float)
        """
        if len(self.state_history) < steps_back + 1:
            return True, 1.0
        
        previous_state = self.state_history[-(steps_back + 1)]
        
        changed, difference = self.image_processor.detect_change(
            previous_state.screenshot,
            screenshot,
            threshold=self.change_threshold,
            method=self.method
        )
        
        return changed, difference
    
    def detect_specific_changes(
        self,
        screenshot1: Image.Image,
        screenshot2: Image.Image
    ) -> Dict[str, Any]:
        """
        Perform detailed analysis of changes between two screenshots.
        
        Returns:
            Dictionary with change analysis
        """
        # Hash-based similarity
        hash_similarity = self.image_processor.compute_similarity(
            screenshot1,
            screenshot2
        )
        
        # Try structural similarity (more accurate but slower)
        try:
            structural_similarity = self.image_processor.compute_structural_similarity(
                screenshot1,
                screenshot2
            )
        except Exception as e:
            log.warning(f"Could not compute structural similarity: {e}")
            structural_similarity = hash_similarity
        
        return {
            "hash_similarity": hash_similarity,
            "structural_similarity": structural_similarity,
            "hash_difference": 1 - hash_similarity,
            "structural_difference": 1 - structural_similarity,
            "significant_change": (1 - hash_similarity) >= self.change_threshold
        }
    
    def get_change_summary(self) -> Dict[str, Any]:
        """Get summary of all detected changes."""
        if not self.state_history:
            return {
                "total_states": 0,
                "time_span": 0,
                "average_interval": 0
            }
        
        timestamps = [state.timestamp for state in self.state_history]
        
        if len(timestamps) > 1:
            time_span = (timestamps[-1] - timestamps[0]).total_seconds()
            average_interval = time_span / (len(timestamps) - 1)
        else:
            time_span = 0
            average_interval = 0
        
        return {
            "total_states": len(self.state_history),
            "time_span_seconds": time_span,
            "average_interval_seconds": average_interval,
            "first_capture": timestamps[0].isoformat(),
            "last_capture": timestamps[-1].isoformat()
        }
    
    def create_diff_visualization(
        self,
        output_path: Path,
        steps_back: int = 1
    ) -> Optional[Path]:
        """
        Create a visual diff between current and previous state.
        
        Args:
            output_path: Where to save the diff image
            steps_back: How many steps back to compare with
        
        Returns:
            Path to created diff image or None if failed
        """
        if len(self.state_history) < steps_back + 1:
            log.warning("Not enough states for diff visualization")
            return None
        
        try:
            previous_state = self.state_history[-(steps_back + 1)]
            current_state = self.current_state
            
            diff_image = self.image_processor.create_diff_image(
                previous_state.screenshot,
                current_state.screenshot,
                output_path
            )
            
            log.info(f"Created diff visualization: {output_path}")
            return output_path
            
        except Exception as e:
            log.error(f"Failed to create diff visualization: {e}")
            return None

