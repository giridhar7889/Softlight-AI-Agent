"""LLM agent with vision capabilities for UI understanding and action decision."""

import json
from typing import Dict, Any, Optional, List, Literal
from pathlib import Path
from PIL import Image
import base64
import io

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from utils import log, config, ImageProcessor


ActionType = Literal["click", "type", "press_key", "hover", "scroll", "wait", "done", "navigate"]


class Action:
    """Represents an action to be performed in the browser."""
    
    def __init__(
        self,
        action_type: ActionType,
        description: str,
        selector: Optional[str] = None,
        coordinates: Optional[tuple] = None,
        text: Optional[str] = None,
        key: Optional[str] = None,
        direction: Optional[str] = None,
        reasoning: str = "",
        element_id: Optional[int] = None  # SoM element ID
    ):
        self.action_type = action_type
        self.description = description
        self.selector = selector
        self.coordinates = coordinates
        self.text = text
        self.key = key
        self.direction = direction
        self.reasoning = reasoning
        self.element_id = element_id  # Set-of-Marks ID (preferred)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type,
            "description": self.description,
            "selector": self.selector,
            "coordinates": self.coordinates,
            "text": self.text,
            "key": self.key,
            "direction": self.direction,
            "reasoning": self.reasoning,
            "element_id": self.element_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        """Create action from dictionary."""
        return cls(**data)


class LLMAgent:
    """Agent that uses LLM with vision to understand UI and make decisions."""
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Initialize the LLM agent.
        
        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model name (defaults to gpt-4-vision-preview or claude-3-opus)
        """
        self.provider = provider.lower()
        
        if self.provider == "openai":
            self.client = AsyncOpenAI(api_key=config.openai_api_key)
            self.model = model or "gpt-4o"  # Updated to use gpt-4o which has vision
        elif self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=config.anthropic_api_key)
            self.model = model or "claude-3-5-sonnet-20241022"  # Updated to latest
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        self.conversation_history: List[Dict[str, Any]] = []
        self.image_processor = ImageProcessor()
    
    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64."""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def analyze_ui(
        self,
        screenshot: Image.Image,
        task_query: str,
        page_info: Dict[str, Any],
        previous_actions: List[Action],
        additional_context: str = "",
        som_elements: Optional[List[Dict[str, Any]]] = None
    ) -> Action:
        """
        Analyze UI screenshot and decide next action.
        
        Args:
            screenshot: Current page screenshot (with SoM labels if available)
            task_query: The task the user wants to accomplish
            page_info: Information about current page (URL, title, etc.)
            previous_actions: List of actions taken so far
            additional_context: Additional context about the app or task
            som_elements: List of labeled elements with their IDs (Set-of-Marks)
        
        Returns:
            Next action to perform
        """
        log.info("Analyzing UI with LLM vision (SoM mode)..." if som_elements else "Analyzing UI with LLM vision...")
        
        # Build the prompt
        prompt = self._build_analysis_prompt(
            task_query,
            page_info,
            previous_actions,
            additional_context,
            som_elements
        )
        
        # Call LLM with vision
        if self.provider == "openai":
            action = await self._analyze_with_openai(screenshot, prompt)
        else:
            action = await self._analyze_with_anthropic(screenshot, prompt)
        
        log.info(f"LLM decided action: {action.action_type} - {action.description}")
        return action
    
    def _build_analysis_prompt(
        self,
        task_query: str,
        page_info: Dict[str, Any],
        previous_actions: List[Action],
        additional_context: str,
        som_elements: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build the prompt for UI analysis."""
        
        actions_summary = "\n".join([
            f"{i+1}. {action.action_type}: {action.description}"
            for i, action in enumerate(previous_actions)
        ])
        
        # Build element map if using Set-of-Marks
        som_mode = som_elements is not None and len(som_elements) > 0
        element_info = ""
        
        if som_mode:
            # Create a concise summary of labeled elements
            key_elements = []
            for el in som_elements[:50]:  # Limit to first 50 to avoid token overload
                desc = el.get('text', '')[:50] or el.get('ariaLabel', '')[:50] or f"{el.get('tagName', 'element')}"
                key_elements.append(f"  #{el['id']}: {el.get('tagName', 'element')} - {desc}")
            
            element_info = f"\n\nLabeled Interactive Elements (Red numbers on screenshot):\n" + "\n".join(key_elements)
        
        if som_mode:
            # Set-of-Marks mode: AI identifies numbered elements
            prompt = f"""You are an INTELLIGENT AUTONOMOUS WEB AGENT that navigates like a HUMAN.

🎯 YOUR MISSION: {task_query}

🌐 CURRENT STATE:
- URL: {page_info.get('url', 'Unknown')}
- Page: {page_info.get('title', 'Unknown')}
{f'- Context: {additional_context}' if additional_context else ''}

📜 WHAT YOU'VE DONE SO FAR:
{actions_summary if actions_summary else 'Nothing yet - this is your first action'}

🏷️ INTERACTIVE ELEMENTS (Red numbered labels on screenshot):
{element_info}

🧠 THINK LIKE A HUMAN:
1. **Understand the goal**: What are you trying to find/accomplish?
2. **Scan the page**: What navigation options do you see?
3. **Choose intelligently**: Which element gets you closer to the goal?
4. **Don't repeat**: If you've clicked something twice, try something else!
5. **Look for key sections**: Menus, navigation bars, search boxes, "Perspectives/Blog" links

🎯 NAVIGATION STRATEGY:
- If looking for articles/blog posts → Find "Perspectives", "Blog", "News", or "Articles" link
- If looking for people/team → Find "Team", "About", or "People" link  
- If looking for products → Find "Products", "Solutions", or "Portfolio" link
- If stuck on homepage → Try the menu/hamburger icon or main navigation
- If you keep seeing the same elements → You might be in a loop, try a DIFFERENT element!

⚠️ AVOID LOOPS:
- DON'T click the same element more than twice
- If you just clicked element #5, try a DIFFERENT element
- Look for new/unexplored navigation options
- Humans don't click the same button 10 times!

💭 THINK STEP-BY-STEP:
1. "What am I looking for?" (e.g., blog posts, team page, tutorial)
2. "What elements help me get there?" (navigation menus, search, specific links)
3. "Have I tried this before?" (avoid repetition)
4. "Am I making progress?" (new pages = good, same state = try something else)

RESPONSE FORMAT (JSON):
{{
    "action_type": "click" | "type" | "press_key" | "scroll" | "done",
    "element_id": <NUMBER>,  // ← THE RED LABEL NUMBER
    "description": "Brief action description",
    "reasoning": "Why this advances the task AND why this element (not others)",
    "text": "text to type (only if action_type is 'type')"
}}

EXAMPLES:

1. Click a button (using element ID):
{{
    "action_type": "click",
    "element_id": 12,
    "description": "Click 'Create Project' button",
    "reasoning": "Opens project creation modal"
}}

2. Fill input field:
{{
    "action_type": "type",
    "element_id": 5,
    "text": "My New Project",
    "description": "Enter project name",
    "reasoning": "Providing the required project name"
}}

3. Task complete:
{{
    "action_type": "done",
    "description": "Task completed",
    "reasoning": "Project created and visible in list"
}}

Now analyze the screenshot with RED LABELS and return JSON with the next action:"""
        
        else:
            # Fallback mode: AI generates selectors (less reliable)
            prompt = f"""You are an AI agent helping to create a visual tutorial for: "{task_query}"

Current Page Information:
- URL: {page_info.get('url', 'Unknown')}
- Title: {page_info.get('title', 'Unknown')}

{f'Additional Context: {additional_context}' if additional_context else ''}

Previous Actions Taken:
{actions_summary if actions_summary else 'None yet - this is the first step'}

Your task is to analyze the screenshot and determine the NEXT action to accomplish the goal.

IMPORTANT GUIDELINES:
1. Think step-by-step about what needs to be done to complete the task
2. Focus on UI elements that are relevant to the task
3. If you see a button, menu, or modal that should be captured for the tutorial, interact with it
4. Prefer clicking visible buttons/links over trying to guess selectors
5. If a modal or dropdown appears, that's a new UI state worth capturing
6. Be specific about what you're clicking and why
7. If the task appears complete, return action_type "done"

RESPONSE FORMAT:
You MUST respond with valid JSON in this exact format:
{{
    "action_type": "click" | "type" | "press_key" | "hover" | "scroll" | "wait" | "done",
    "description": "Brief description of what this action does",
    "reasoning": "Why this action helps accomplish the task",
    "selector": "CSS selector for the element (if applicable)",
    "text": "text to type (if action_type is 'type')",
    "key": "key to press (if action_type is 'press_key', e.g., 'Enter', 'Escape')",
    "direction": "up or down (if action_type is 'scroll')"
}}

Example responses:
1. Click button:
{{
    "action_type": "click",
    "description": "Click the 'Create Project' button",
    "reasoning": "This opens the project creation modal which is needed for the tutorial",
    "selector": "button:has-text('Create Project')"
}}

2. Fill form:
{{
    "action_type": "type",
    "description": "Enter project name",
    "reasoning": "Need to provide a name for the new project",
    "selector": "input[placeholder='Project name']",
    "text": "Tutorial Project"
}}

3. Task complete:
{{
    "action_type": "done",
    "description": "Task completed successfully",
    "reasoning": "The project has been created and is now visible in the list"
}}

Now analyze the screenshot and provide the next action as JSON:"""
        
        return prompt
    
    async def _analyze_with_openai(self, screenshot: Image.Image, prompt: str) -> Action:
        """Analyze UI using OpenAI GPT-4 Vision."""
        
        # Encode image
        base64_image = self._encode_image(screenshot)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1000,
            temperature=0.1
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        return self._parse_action_response(response_text)
    
    async def _analyze_with_anthropic(self, screenshot: Image.Image, prompt: str) -> Action:
        """Analyze UI using Anthropic Claude."""
        
        # Encode image
        base64_image = self._encode_image(screenshot)
        
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # Parse response
        response_text = message.content[0].text
        return self._parse_action_response(response_text)
    
    def _parse_action_response(self, response_text: str) -> Action:
        """Parse LLM response into an Action object."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Create Action object (supports both SoM and selector modes)
            return Action(
                action_type=data.get("action_type", "wait"),
                description=data.get("description", "No description"),
                selector=data.get("selector"),
                coordinates=tuple(data["coordinates"]) if data.get("coordinates") else None,
                text=data.get("text"),
                key=data.get("key"),
                direction=data.get("direction"),
                reasoning=data.get("reasoning", ""),
                element_id=data.get("element_id")  # Set-of-Marks ID
            )
            
        except Exception as e:
            log.error(f"Failed to parse LLM response: {e}")
            log.error(f"Response was: {response_text}")
            
            # Return a wait action as fallback
            return Action(
                action_type="wait",
                description="Failed to parse action, waiting",
                reasoning=f"Parse error: {e}"
            )
    
    async def describe_ui_state(
        self,
        screenshot: Image.Image,
        task_query: str
    ) -> str:
        """
        Generate a natural language description of the current UI state.
        Useful for dataset annotations.
        
        Args:
            screenshot: Screenshot to describe
            task_query: The task being performed
        
        Returns:
            Natural language description of the UI
        """
        base64_image = self._encode_image(screenshot)
        
        prompt = f"""Describe this UI screenshot in the context of the task: "{task_query}"

Focus on:
1. What page or screen is shown
2. What interactive elements are visible
3. What state the interface is in (e.g., "modal open", "form filled", etc.)
4. How this relates to the task

Provide a concise 1-2 sentence description suitable for a tutorial step."""
        
        if self.provider == "openai":
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content
        
        else:  # anthropic
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
            )
            
            return message.content[0].text
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

