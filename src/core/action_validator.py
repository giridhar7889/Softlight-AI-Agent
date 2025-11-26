"""Action validation and loop prevention for intelligent navigation."""

from typing import List, Optional, Dict, Any
from collections import Counter
from .llm_agent import Action
from utils import log


class ActionValidator:
    """Validates actions and prevents repetitive loops to enable human-like navigation."""
    
    def __init__(self, max_repeats: int = 2):
        """
        Initialize the action validator.
        
        Args:
            max_repeats: Maximum times the same action can be repeated
        """
        self.max_repeats = max_repeats
        self.action_history: List[Action] = []
        self.element_click_count: Counter = Counter()
        self.page_url_actions: Dict[str, List[str]] = {}
        
    def add_action(self, action: Action, current_url: str):
        """Record an action in history."""
        self.action_history.append(action)
        
        # Track element clicks
        if action.element_id is not None:
            self.element_click_count[action.element_id] += 1
        
        # Track actions per URL
        if current_url not in self.page_url_actions:
            self.page_url_actions[current_url] = []
        
        action_signature = f"{action.action_type}:{action.element_id or action.selector}"
        self.page_url_actions[current_url].append(action_signature)
    
    def is_repetitive(self, action: Action, current_url: str) -> bool:
        """
        Check if an action is repetitive and should be avoided.
        
        Args:
            action: Proposed action
            current_url: Current page URL
        
        Returns:
            True if action is repetitive and should be rejected
        """
        # Check element click count
        if action.element_id is not None:
            if self.element_click_count[action.element_id] >= self.max_repeats:
                log.warning(f"Element #{action.element_id} already clicked {self.element_click_count[action.element_id]} times")
                return True
        
        # Check for same action at same URL
        if current_url in self.page_url_actions:
            action_signature = f"{action.action_type}:{action.element_id or action.selector}"
            count = self.page_url_actions[current_url].count(action_signature)
            
            if count >= self.max_repeats:
                log.warning(f"Action '{action_signature}' already performed {count} times at this URL")
                return True
        
        # Check for recent identical actions
        if len(self.action_history) >= 2:
            last_two = self.action_history[-2:]
            if all(
                a.action_type == action.action_type and 
                a.element_id == action.element_id 
                for a in last_two
            ):
                log.warning("Same action repeated 3 times in a row - likely stuck")
                return True
        
        return False
    
    def get_avoided_elements(self) -> List[int]:
        """Get list of element IDs that should be avoided (already clicked too much)."""
        return [
            element_id 
            for element_id, count in self.element_click_count.items() 
            if count >= self.max_repeats
        ]
    
    def suggest_alternative(
        self, 
        rejected_action: Action,
        available_elements: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Suggest an alternative action when one is rejected.
        
        Args:
            rejected_action: The action that was rejected
            available_elements: List of available elements on page
        
        Returns:
            Suggestion string for the AI
        """
        avoided_ids = self.get_avoided_elements()
        
        suggestion = f"\nElement #{rejected_action.element_id} has been clicked too many times. "
        suggestion += f"Please choose a DIFFERENT element. Avoid elements: {avoided_ids}. "
        suggestion += "Try exploring other navigation options like menus, search, or different links."
        
        return suggestion
    
    def get_exploration_hints(self, task_query: str) -> str:
        """
        Get hints for more intelligent exploration based on the task.
        
        Args:
            task_query: The user's task
        
        Returns:
            Hints string to help AI navigate better
        """
        hints = []
        
        # Analyze task for key terms
        task_lower = task_query.lower()
        
        if "find" in task_lower or "search" in task_lower:
            hints.append("Look for search boxes, navigation menus, or 'Perspectives/Blog' sections")
        
        if "article" in task_lower or "blog" in task_lower or "post" in task_lower:
            hints.append("Navigate to Perspectives, Blog, News, or Articles sections")
        
        if "team" in task_lower or "people" in task_lower:
            hints.append("Look for Team, About Us, or People navigation links")
        
        if "create" in task_lower or "how to" in task_lower:
            hints.append("Look for Getting Started, Tutorial, or Documentation links")
        
        if hints:
            return "NAVIGATION HINTS: " + "; ".join(hints)
        
        return ""
    
    def reset(self):
        """Reset the validator for a new workflow."""
        self.action_history = []
        self.element_click_count = Counter()
        self.page_url_actions = {}


