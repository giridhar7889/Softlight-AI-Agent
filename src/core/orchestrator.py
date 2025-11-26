"""Workflow orchestrator that coordinates all components."""

import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from PIL import Image

from core.browser_controller import BrowserController
from core.llm_agent import LLMAgent, Action
from core.ui_detector import UIChangeDetector
from core.state_manager import StateManager, WorkflowDataset
from core.action_validator import ActionValidator
from core.navigation_planner import NavigationPlanner
from core.goal_monitor import GoalMonitor
from utils import log, config, AppConfig, TaskConfig, console


class WorkflowOrchestrator:
    """Coordinates workflow execution and state capture."""
    
    def __init__(
        self,
        app_config: AppConfig,
        llm_provider: str = "openai",
        headless: bool = False,
        browser_type: str = "chromium"
    ):
        """
        Initialize the orchestrator.
        
        Args:
            app_config: Configuration for the target app
            llm_provider: LLM provider to use
            headless: Run browser in headless mode
        """
        self.app_config = app_config
        self.headless = headless
        self.browser_type = browser_type
        
        # Initialize components
        self.browser: Optional[BrowserController] = None
        self.llm_agent = LLMAgent(provider=llm_provider)
        self.ui_detector = UIChangeDetector(
            change_threshold=app_config.change_threshold
        )
        self.state_manager = StateManager()
        self.action_validator = ActionValidator(max_repeats=2)  # Prevent loops
        self.goal_monitor: Optional[GoalMonitor] = None
        
        # Workflow state
        self.current_task: Optional[str] = None
        self.actions_taken: List[Action] = []
        self.max_steps = config.max_steps_per_task
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start the orchestrator and browser."""
        log.info("Starting workflow orchestrator")
        self.browser = BrowserController(
            app_config=self.app_config,
            headless=self.headless,
            browser_type=self.browser_type
        )
        await self.browser.start()
    
    async def stop(self):
        """Stop the orchestrator and cleanup."""
        log.info("Stopping workflow orchestrator")
        if self.browser:
            await self.browser.close()
    
    async def execute_workflow(
        self,
        task_query: str,
        task_id: str,
        start_url: Optional[str] = None,
        max_steps: Optional[int] = None
    ) -> WorkflowDataset:
        """
        Execute a complete workflow for a task.
        
        Args:
            task_query: The task to accomplish
            task_id: Unique identifier for this task
            start_url: Starting URL (defaults to app base URL)
            max_steps: Maximum steps to take (overrides default)
        
        Returns:
            WorkflowDataset with all captured steps
        """
        console.print(f"\n[bold blue]🚀 Starting workflow: {task_query}[/bold blue]\n")
        
        self.current_task = task_query
        self.actions_taken = []
        max_steps = max_steps or self.max_steps
        step_limit = max_steps
        self.goal_monitor = GoalMonitor(task_query)
        
        # Start workflow capture
        self.state_manager.start_workflow(
            app_name=self.app_config.name,
            task_id=task_id,
            task_query=task_query
        )
        
        # Reset UI detector and action validator
        self.ui_detector.reset()
        self.action_validator.reset()
        
        # Navigate to starting URL
        start_url = start_url or self.app_config.base_url
        success = await self.browser.navigate(start_url)
        
        if not success:
            log.error("Failed to navigate to start URL")
            return self.state_manager.end_workflow(
                success=False,
                error_message="Failed to navigate to start URL"
            )
        
        # Capture initial state
        await self._capture_current_state(
            action=Action(
                action_type="navigate",
                description=f"Navigate to {start_url}",
                reasoning="Initial page load"
            ),
            force_capture=True
        )
        
        # Main execution loop
        step_count = 0
        error_message = ""
        task_completed = False
        
        try:
            while True:
                if step_count >= step_limit:
                    extra_steps = self.goal_monitor.request_extension() if self.goal_monitor else 0
                    if extra_steps:
                        step_limit += extra_steps
                        console.print(f"[blue]Extending workflow limit to {step_limit} steps to finish the task[/blue]")
                    else:
                        log.warning(f"Reached maximum steps ({step_limit})")
                        error_message = f"Maximum steps ({step_limit}) reached"
                        break
                
                step_count += 1
                console.print(f"[cyan]Step {step_count}/{step_limit}[/cyan]")
                
                # Get current page info
                page_info = await self.browser.get_page_info()
                
                # === DUAL-SCREENSHOT APPROACH (Set-of-Marks) ===
                
                # 1. Take CLEAN screenshot first (for dataset/tutorial)
                clean_screenshot = await self.browser.take_screenshot()
                
                # 2. Inject Set-of-Marks labels (numbered overlays)
                som_data = await self.browser.inject_som_labels()
                som_elements = som_data.get('elements', [])
                
                if som_elements:
                    console.print(f"  🏷️  Labeled {som_data['count']} interactive elements")
                
                # 3. Take LABELED screenshot (for AI analysis)
                labeled_screenshot = await self.browser.take_screenshot()
                
                # 4. Ask LLM to analyze LABELED screenshot with INTELLIGENT navigation
                exploration_hints = self.action_validator.get_exploration_hints(task_query)
                avoided_elements = self.action_validator.get_avoided_elements()
                smart_additions = NavigationPlanner.generate_smart_prompt_additions(
                    task_query, step_count, page_info["url"], self.actions_taken
                )
                
                enhanced_context = f"App: {self.app_config.name}"
                if avoided_elements:
                    enhanced_context += f"\n⚠️ AVOID clicking these elements (already tried): {avoided_elements}"
                if exploration_hints:
                    enhanced_context += f"\n{exploration_hints}"
                if smart_additions:
                    enhanced_context += f"\n{smart_additions}"
                if self.goal_monitor:
                    goal_hint = self.goal_monitor.get_prompt_hint()
                    if goal_hint:
                        enhanced_context += f"\n{goal_hint}"
                
                action = await self.llm_agent.analyze_ui(
                    screenshot=labeled_screenshot,  # AI sees labeled version
                    task_query=task_query,
                    page_info=page_info,
                    previous_actions=self.actions_taken,
                    additional_context=enhanced_context,
                    som_elements=som_elements  # Pass element mapping
                )
                
                console.print(f"  → [yellow]{action.action_type}[/yellow]: {action.description}")
                if action.element_id is not None:
                    console.print(f"     [dim]Target: Element #{action.element_id}[/dim]")
                
                # 4.5. Validate action (prevent loops!)
                if action.action_type in ["click", "type"]:
                    if self.action_validator.is_repetitive(action, page_info["url"]):
                        console.print(f"  [yellow]⚠️  Repetitive action detected - requesting alternative[/yellow]")
                        
                        # Ask AI for a different action
                        suggestion = self.action_validator.suggest_alternative(action, som_elements)
                        enhanced_context += f"\n{suggestion}"
                        
                        # Re-analyze with the suggestion
                        action = await self.llm_agent.analyze_ui(
                            screenshot=labeled_screenshot,
                            task_query=task_query,
                            page_info=page_info,
                            previous_actions=self.actions_taken,
                            additional_context=enhanced_context,
                            som_elements=som_elements
                        )
                        
                        console.print(f"  → [green]New action[/green]: {action.description}")
                        if action.element_id is not None:
                            console.print(f"     [dim]Target: Element #{action.element_id}[/dim]")
                
                # 5. Remove labels before executing action
                await self.browser.remove_som_labels()
                
                # Check if task is complete
                if action.action_type == "done":
                    log.info("Task marked as complete by LLM")
                    task_completed = True
                    final_screenshot = await self.browser.take_screenshot()
                    await self._capture_current_state(
                        action,
                        force_capture=True,
                        screenshot=final_screenshot
                    )
                    break
                
                # Execute the action (using SoM if available)
                success = await self._execute_action(action)
                
                if not success:
                    log.warning(f"Action failed: {action.description}")
                    # Continue anyway, sometimes failures are recoverable
                
                # Record action in both history and validator
                self.actions_taken.append(action)
                self.action_validator.add_action(action, page_info["url"])
                
                # Wait for UI to stabilize
                await self.browser.wait_for_stability()
                
                # Capture state using CLEAN screenshot (no labels in dataset)
                await self._capture_current_state(action, screenshot=clean_screenshot)

                # Goal monitoring to decide if task is already satisfied
                if self.goal_monitor:
                    page_text = await self.browser.get_page_text()
                    goal_status = self.goal_monitor.evaluate(page_text)
                    if goal_status.get("done"):
                        task_completed = True
                        matches = goal_status.get("matches", [])[:5]
                        console.print(f"  🎯 [green]Goal satisfied[/green] (keywords: {', '.join(matches)})")
                        final_screenshot = await self.browser.take_screenshot()
                        await self._capture_current_state(
                            Action(
                                action_type="done",
                                description="GoalMonitor detected target information",
                                reasoning="Required keywords present on page"
                            ),
                            force_capture=True,
                            screenshot=final_screenshot
                        )
                        break
                    else:
                        console.print(f"  [dim]{self.goal_monitor.get_status_message()}[/dim]")
                
                # Small delay between actions
                await asyncio.sleep(0.5)
            
        except Exception as e:
            log.error(f"Workflow execution failed: {e}")
            error_message = str(e)
            task_completed = False
        
        # End workflow and save dataset
        dataset = self.state_manager.end_workflow(
            success=task_completed and not error_message,
            error_message=error_message
        )
        
        console.print(f"\n[bold green]✅ Workflow completed: {dataset.total_steps} steps captured[/bold green]\n")
        
        return dataset
    
    async def _execute_action(self, action: Action) -> bool:
        """
        Execute a single action in the browser.
        Supports both Set-of-Marks (element_id) and selector-based approaches.
        
        Args:
            action: Action to execute
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if action.action_type == "click":
                # Prefer SoM element_id over selector (more reliable)
                if action.element_id is not None:
                    return await self.browser.click_by_som_id(
                        element_id=action.element_id,
                        description=action.description
                    )
                else:
                    return await self.browser.click_element(
                        selector=action.selector,
                        coordinates=action.coordinates,
                        description=action.description
                    )
            
            elif action.action_type == "type":
                # Prefer SoM element_id over selector
                if action.element_id is not None:
                    if not action.text:
                        log.error("Type action requires text")
                        return False
                    return await self.browser.type_by_som_id(
                        element_id=action.element_id,
                        text=action.text,
                        description=action.description
                    )
                else:
                    if not action.selector or not action.text:
                        log.error("Type action requires selector and text")
                        return False
                    return await self.browser.type_text(
                        selector=action.selector,
                        text=action.text,
                        description=action.description
                    )
            
            elif action.action_type == "press_key":
                if not action.key:
                    log.error("Press key action requires key")
                    return False
                return await self.browser.press_key(action.key)
            
            elif action.action_type == "hover":
                if not action.selector:
                    log.error("Hover action requires selector")
                    return False
                return await self.browser.hover_element(
                    selector=action.selector,
                    description=action.description
                )
            
            elif action.action_type == "scroll":
                direction = action.direction or "down"
                return await self.browser.scroll(direction=direction)
            
            elif action.action_type == "wait":
                await asyncio.sleep(2.0)
                return True
            
            elif action.action_type == "navigate":
                if not action.text:  # URL stored in text field
                    return False
                return await self.browser.navigate(action.text)
            
            else:
                log.warning(f"Unknown action type: {action.action_type}")
                return False
        
        except Exception as e:
            log.error(f"Action execution failed: {e}")
            return False
    
    async def _capture_current_state(
        self,
        action: Action,
        force_capture: bool = False,
        screenshot: Optional[Any] = None
    ):
        """
        Capture current UI state if it has changed significantly.
        
        Args:
            action: Action that was just performed
            force_capture: Force capture regardless of change detection
            screenshot: Pre-captured screenshot (if available, avoids re-capture)
        """
        # Take screenshot if not provided
        if screenshot is None:
            screenshot = await self.browser.take_screenshot()
        
        # Check if UI changed
        should_capture, difference, reason = self.ui_detector.should_capture(
            screenshot,
            force=force_capture,
            metadata={"action": action.action_type}
        )
        
        if should_capture:
            # Get page info
            page_info = await self.browser.get_page_info()
            
            # Capture the step
            self.state_manager.capture_step(
                screenshot=screenshot,
                description=action.description,
                action_type=action.action_type,
                action_target=action.selector or str(action.coordinates) or "N/A",
                url=page_info["url"],
                reasoning=action.reasoning,
                metadata={
                    "difference": difference,
                    "reason": reason,
                    "page_title": page_info["title"]
                }
            )
            
            console.print(f"  📸 [green]Captured step[/green] (diff: {difference:.3f})")
        else:
            log.debug(f"Skipped capture (diff: {difference:.3f}, threshold: {self.ui_detector.change_threshold})")
    
    async def execute_task_config(self, task_config: TaskConfig) -> WorkflowDataset:
        """
        Execute a workflow from a TaskConfig object.
        
        Args:
            task_config: Task configuration
        
        Returns:
            WorkflowDataset with all captured steps
        """
        return await self.execute_workflow(
            task_query=task_config.query,
            task_id=task_config.id,
            start_url=task_config.start_url,
            max_steps=task_config.max_steps
        )
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current workflow progress information."""
        return {
            "current_task": self.current_task,
            "actions_taken": len(self.actions_taken),
            "states_captured": self.ui_detector.get_state_count(),
            "steps_saved": self.state_manager.get_current_step_count()
        }

