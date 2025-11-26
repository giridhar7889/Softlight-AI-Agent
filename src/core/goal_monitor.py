"""Goal monitoring and automatic completion detection."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from core.navigation_planner import NavigationPlanner
from utils import log

STOPWORDS = {
    "how",
    "what",
    "when",
    "where",
    "which",
    "show",
    "tell",
    "give",
    "with",
    "that",
    "this",
    "from",
    "into",
    "page",
    "site",
    "website",
    "like",
    "need",
    "about",
    "want",
    "step",
    "steps",
    "task",
    "check",
    "find",
    "view",
    "see",
}

ROLE_KEYWORDS = [
    "director",
    "manager",
    "engineer",
    "designer",
    "scientist",
    "analyst",
    "lead",
    "developer",
    "specialist",
    "writer",
    "consultant",
    "architect",
]

SALARY_SYNONYMS = [
    "salary",
    "compensation",
    "total compensation",
    "total comp",
    "pay",
    "bonus",
    "tc",
    "base pay",
]


class GoalMonitor:
    """Tracks goal completion and manages dynamic step extensions."""

    def __init__(
        self,
        task_query: str,
        extension_chunk: int = 3,
        max_extensions: int = 4,
    ):
        self.task_query = task_query
        self.intent = NavigationPlanner.extract_task_intent(task_query)
        (
            self.company_terms,
            self.role_terms,
            self.context_terms,
        ) = self._build_terms()

        self.company_phrases = [t for t in self.company_terms if " " in t]
        self.role_phrases = [t for t in self.role_terms if " " in t]

        self.require_currency = any(
            keyword in self.task_query.lower()
            for keyword in ["salary", "compensation", "pay", "income", "total comp"]
        )

        self.all_terms = list(
            dict.fromkeys(self.company_terms + self.role_terms + self.context_terms)
        )
        self.required_hits = max(2, round(len(self.all_terms) * 0.45)) if self.all_terms else 0

        self.extension_chunk = extension_chunk
        self.max_extensions = max_extensions
        self.extensions_used = 0

        self.completed = False
        self.matched_terms: List[str] = []
        self.best_ratio = 0.0

    def _normalize(self, term: str) -> str:
        return re.sub(r"\s+", " ", term.strip().lower())

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[A-Za-z0-9]+", text)

    def _build_terms(self) -> Tuple[List[str], List[str], List[str]]:
        company_terms: List[str] = []
        role_terms: List[str] = []
        context_terms: List[str] = []

        # Proper nouns / quoted strings become company terms
        for term in self.intent.get("search_terms", []):
            normalized = self._normalize(term)
            if not normalized:
                continue
            company_terms.append(normalized)
            company_terms.append(normalized.replace(" ", ""))

        # Keywords from NavigationPlanner hints
        for keyword in self.intent.get("keywords", []):
            normalized = self._normalize(keyword)
            if normalized not in STOPWORDS:
                context_terms.append(normalized)

        # Tokenize query for additional hints
        tokens = self._tokenize(self.task_query)
        skip_tokens = set()

        # Capture multi-word role phrases like "Managing Director"
        joined = self.task_query.lower()
        for key in ROLE_KEYWORDS:
            if key in joined:
                pass  # detection still handled below

        for token in tokens:
            token_lower = token.lower()
            if len(token_lower) <= 3 or token_lower in STOPWORDS:
                continue

            if any(key in token_lower for key in ROLE_KEYWORDS):
                role_terms.append(token_lower)
            elif "salary" in token_lower or "comp" in token_lower:
                context_terms.append("salary")
            else:
                context_terms.append(token_lower)

        # Add salary synonyms if the query mentions salary/compensation
        if "salary" in self.task_query.lower() or "compensation" in self.task_query.lower():
            context_terms.extend(SALARY_SYNONYMS)

        # Ensure critical phrases remain
        if "managing director" in self.task_query.lower():
            role_terms.append("managing director")
            role_terms.append("managingdirector")
            # Avoid counting individual words when phrase is present
            role_terms = [term for term in role_terms if term not in {"managing", "director"}]

        return (
            [t for t in dict.fromkeys(company_terms)],
            [t for t in dict.fromkeys(role_terms)],
            [t for t in dict.fromkeys(context_terms)],
        )

    def evaluate(self, page_text: str) -> Dict[str, object]:
        """Evaluate page text to determine if goal is complete."""
        if not page_text:
            return {
                "done": False,
                "matches": [],
                "ratio": 0.0,
                "company_hit": False,
                "role_hit": False,
            }

        lower_text = page_text.lower()
        matches = [term for term in self.all_terms if term and term in lower_text]
        unique_matches = sorted(set(matches))

        total_terms = len(self.all_terms) or 1
        ratio = len(unique_matches) / total_terms
        self.best_ratio = max(self.best_ratio, ratio)

        def _phrase_hit(phrases: List[str], fallback_terms: List[str]) -> bool:
            if phrases:
                return any(phrase in lower_text for phrase in phrases)
            return not fallback_terms or any(term in lower_text for term in fallback_terms)

        company_hit = _phrase_hit(self.company_phrases, self.company_terms)
        role_hit = _phrase_hit(self.role_phrases, self.role_terms)

        currency_hit = True
        if self.require_currency:
            currency_hit = bool(re.search(r"\$[\s]*[0-9]", lower_text)) or "usd" in lower_text

        hit_threshold = self.required_hits or max(2, min(4, len(self.all_terms)))
        goal_met = (
            company_hit
            and role_hit
            and len(unique_matches) >= hit_threshold
            and currency_hit
        )

        self.completed = goal_met
        self.matched_terms = unique_matches

        return {
            "done": goal_met,
            "matches": unique_matches,
            "ratio": ratio,
            "company_hit": company_hit,
            "role_hit": role_hit,
            "currency_hit": currency_hit,
            "min_hits": hit_threshold,
        }

    def request_extension(self) -> int:
        """Request more steps if goal not achieved."""
        if self.completed:
            return 0
        if self.extensions_used >= self.max_extensions:
            return 0
        self.extensions_used += 1
        log.info(f"GoalMonitor extending workflow (extension {self.extensions_used}/{self.max_extensions})")
        return self.extension_chunk

    def get_prompt_hint(self) -> str:
        """Provide hint text for the LLM prompt."""
        if self.completed:
            return "Goal conditions satisfied - respond with action_type 'done' if the final screenshot already shows the answer."

        remaining = [term for term in self.all_terms if term not in self.matched_terms]
        if not remaining:
            return ""

        snippet = ", ".join(remaining[:4])
        return f"Still need UI that clearly shows: {snippet}. Surface this information before finishing."

    def get_status_message(self) -> str:
        """Return a human-readable progress summary."""
        if self.completed:
            return f"Goal satisfied (keywords: {', '.join(self.matched_terms[:5])})"

        if not self.matched_terms:
            if self.require_currency:
                return "Still looking for UI that shows actual salary figures (e.g., $XXX)."
            return "Goal keywords not observed yet."

        parts = [f"Matched keywords so far: {', '.join(self.matched_terms[:5])}"]
        if self.require_currency:
            parts.append("Need to capture the actual salary numbers before finishing.")
        return " ".join(parts)


