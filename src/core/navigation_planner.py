"""Smart navigation planning for human-like web browsing."""

from typing import List, Dict, Any, Optional
import re


class NavigationPlanner:
    """Plans intelligent navigation strategies based on tasks."""
    
    @staticmethod
    def extract_task_intent(task_query: str) -> Dict[str, Any]:
        """
        Analyze the task to understand user intent.
        
        Args:
            task_query: The user's task
        
        Returns:
            Dictionary with task analysis
        """
        task_lower = task_query.lower()
        
        intent = {
            "action": None,
            "target": None,
            "keywords": [],
            "navigation_hints": []
        }
        
        # Determine primary action
        if any(word in task_lower for word in ["find", "search", "look for", "locate"]):
            intent["action"] = "search"
        elif any(word in task_lower for word in ["create", "make", "build", "add"]):
            intent["action"] = "create"
        elif any(word in task_lower for word in ["how to", "tutorial", "guide", "learn"]):
            intent["action"] = "learn"
        elif any(word in task_lower for word in ["navigate", "go to", "visit"]):
            intent["action"] = "navigate"
        
        # Determine target
        if "article" in task_lower or "blog" in task_lower or "post" in task_lower:
            intent["target"] = "articles"
            intent["navigation_hints"].append("Look for 'Perspectives', 'Blog', 'News', or 'Articles' links")
            intent["keywords"] = ["perspectives", "blog", "news", "articles", "insights"]
        
        elif "team" in task_lower or "people" in task_lower or "member" in task_lower:
            intent["target"] = "team"
            intent["navigation_hints"].append("Look for 'Team', 'About', 'People', or 'Our Team' links")
            intent["keywords"] = ["team", "people", "about", "members", "staff"]
        
        elif "tutorial" in task_lower or "guide" in task_lower or "documentation" in task_lower:
            intent["target"] = "documentation"
            intent["navigation_hints"].append("Look for 'Docs', 'Tutorial', 'Getting Started', or 'Guide' links")
            intent["keywords"] = ["documentation", "docs", "tutorial", "guide", "getting started"]
        
        elif "product" in task_lower or "portfolio" in task_lower or "company" in task_lower:
            intent["target"] = "portfolio"
            intent["navigation_hints"].append("Look for 'Portfolio', 'Companies', or 'Products' links")
            intent["keywords"] = ["portfolio", "companies", "products", "investments"]
        
        # Extract specific search terms
        search_terms = []
        
        # Look for quoted terms
        quoted = re.findall(r'"([^"]+)"', task_query)
        search_terms.extend(quoted)
        
        # Look for proper nouns (capitalized words)
        proper_nouns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', task_query)
        search_terms.extend(proper_nouns)
        
        intent["search_terms"] = list(set(search_terms))
        
        return intent
    
    @staticmethod
    def generate_search_strategy(task_intent: Dict[str, Any]) -> str:
        """
        Generate a search strategy prompt for the AI.
        
        Args:
            task_intent: Task intent analysis
        
        Returns:
            Strategy string for AI prompt
        """
        strategy = []
        
        if task_intent["action"] == "search" and task_intent["search_terms"]:
            terms = ", ".join(task_intent["search_terms"])
            strategy.append(f"🔍 You're searching for: {terms}")
            strategy.append(f"Strategy: Find search box OR navigate to relevant section")
        
        if task_intent["target"]:
            strategy.append(f"🎯 Target section: {task_intent['target']}")
        
        if task_intent["keywords"]:
            keywords = ", ".join(task_intent["keywords"])
            strategy.append(f"🔑 Look for these words in navigation: {keywords}")
        
        if task_intent["navigation_hints"]:
            strategy.extend(task_intent["navigation_hints"])
        
        return "\n".join(strategy) if strategy else ""
    
    @staticmethod
    def should_try_search(task_query: str, step_count: int) -> bool:
        """
        Determine if the agent should try using a search box.
        
        Args:
            task_query: The task
            step_count: Current step number
        
        Returns:
            True if search might be helpful
        """
        task_lower = task_query.lower()
        
        # If looking for specific content and have taken several steps
        if step_count >= 3 and any(word in task_lower for word in ["find", "search", "articles about", "posts about"]):
            return True
        
        return False
    
    @staticmethod
    def generate_smart_prompt_additions(
        task_query: str,
        step_count: int,
        page_url: str,
        previous_actions: List
    ) -> str:
        """
        Generate smart prompt additions based on context.
        
        Args:
            task_query: The user's task
            step_count: Current step number
            page_url: Current URL
            previous_actions: Actions taken so far
        
        Returns:
            Additional prompt guidance
        """
        additions = []
        
        # If stuck on homepage for multiple steps
        if step_count > 3 and "homepage" in page_url.lower() or page_url.count('/') <= 3:
            additions.append("⚠️ You're still on the homepage after 3+ steps. Try the MENU or NAVIGATION BAR!")
        
        # If searching for content
        if "find" in task_query.lower() or "search" in task_query.lower():
            if step_count >= 2:
                additions.append("💡 TIP: Look for a SEARCH box or navigate to the blog/content section")
        
        # If looking for specific company/name
        proper_nouns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', task_query)
        if proper_nouns and step_count >= 2:
            terms = ", ".join(proper_nouns)
            additions.append(f"🎯 REMEMBER: You're looking for '{terms}' - keep this in mind!")
        
        return "\n".join(additions) if additions else ""


