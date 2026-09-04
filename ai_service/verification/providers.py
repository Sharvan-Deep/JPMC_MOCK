"""
Semantic Change Detection Providers for Task 9.

Implements provider abstraction for semantic project matching and policy analysis:
- BaseChangeDetectionProvider (ABC)
- MockChangeDetectionProvider (Deterministic/offline token and semantic similarity)
- GeminiChangeDetectionProvider (Google GenAI integration with graceful fallback)
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from ai_service.schemas.verification import (
    CSRProjectSnapshot,
    ProjectSemanticMatch,
)


class BaseChangeDetectionProvider(ABC):
    """Abstract interface for semantic AI-assisted comparisons."""

    @abstractmethod
    def find_semantic_project_matches(
        self,
        unmatched_prev: List[CSRProjectSnapshot],
        unmatched_curr: List[CSRProjectSnapshot],
    ) -> List[ProjectSemanticMatch]:
        """Identifies projects that describe substantially similar activity despite different names."""
        pass

    @abstractmethod
    def analyze_policy_shifts(
        self,
        prev_priorities: List[str],
        curr_priorities: List[str],
    ) -> Dict[str, Any]:
        """Provides semantic analysis of CSR policy priority shifts."""
        pass


class MockChangeDetectionProvider(BaseChangeDetectionProvider):
    """
    Mock/offline semantic provider for deterministic testing.
    Uses token overlap, semantic synonym mapping (e.g. potable water <-> safe drinking water,
    rural communities <-> villages), and configurable responses.
    """

    SYNONYM_GROUPS = [
        {"potable", "drinking", "safe", "clean", "water"},
        {"rural", "village", "villages", "communities"},
        {"sanitation", "toilet", "toilets", "wash", "hygiene"},
        {"school", "schools", "children", "students"},
        {"health", "healthcare", "medical", "clinic"},
    ]

    def __init__(self, forced_matches: Optional[List[ProjectSemanticMatch]] = None):
        self.forced_matches = forced_matches or []

    def _compute_semantic_score(self, text_a: str, text_b: str) -> float:
        """Computes semantic overlap score based on synonym clusters."""
        tokens_a = {t.lower().strip(".,;:()") for t in text_a.split() if t}
        tokens_b = {t.lower().strip(".,;:()") for t in text_b.split() if t}

        if not tokens_a or not tokens_b:
            return 0.0

        # Direct token jaccard
        direct_intersection = len(tokens_a & tokens_b)

        # Synonym matches
        synonym_matches = 0
        for group in self.SYNONYM_GROUPS:
            if (tokens_a & group) and (tokens_b & group):
                synonym_matches += 1

        union = len(tokens_a | tokens_b)
        raw_score = (direct_intersection * 1.5 + synonym_matches * 1.2) / max(union, 1)
        return min(round(raw_score, 2), 1.0)

    def find_semantic_project_matches(
        self,
        unmatched_prev: List[CSRProjectSnapshot],
        unmatched_curr: List[CSRProjectSnapshot],
    ) -> List[ProjectSemanticMatch]:
        if self.forced_matches:
            return self.forced_matches

        matches: List[ProjectSemanticMatch] = []
        matched_curr_names = set()

        for p_proj in unmatched_prev:
            p_text = f"{p_proj.project_name} {p_proj.description or ''}"
            best_score = 0.0
            best_curr = None

            for c_proj in unmatched_curr:
                if c_proj.project_name in matched_curr_names:
                    continue
                c_text = f"{c_proj.project_name} {c_proj.description or ''}"
                score = self._compute_semantic_score(p_text, c_text)

                if score > best_score and score >= 0.35:
                    best_score = score
                    best_curr = c_proj

            if best_curr and best_score >= 0.35:
                matched_curr_names.add(best_curr.project_name)
                matches.append(
                    ProjectSemanticMatch(
                        previous_project=p_proj.project_name,
                        current_project=best_curr.project_name,
                        similarity_score=best_score,
                        rationale=(
                            f"Semantic equivalence detected between '{p_proj.project_name}' and "
                            f"'{best_curr.project_name}' with similarity {best_score}."
                        ),
                    )
                )

        return matches

    def analyze_policy_shifts(
        self,
        prev_priorities: List[str],
        curr_priorities: List[str],
    ) -> Dict[str, Any]:
        return {
            "strengthened": [],
            "reduced": [],
            "summary": "Policy priorities evaluated via rule-based comparison.",
        }


class GeminiChangeDetectionProvider(BaseChangeDetectionProvider):
    """
    Live Gemini change detection provider using Google GenAI.
    Falls back to MockChangeDetectionProvider if GEMINI_API_KEY is not set or network fails.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._fallback = MockChangeDetectionProvider()

    def find_semantic_project_matches(
        self,
        unmatched_prev: List[CSRProjectSnapshot],
        unmatched_curr: List[CSRProjectSnapshot],
    ) -> List[ProjectSemanticMatch]:
        if not self.api_key:
            return self._fallback.find_semantic_project_matches(unmatched_prev, unmatched_curr)

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            prev_items = [
                {"name": p.project_name, "desc": p.description or ""} for p in unmatched_prev
            ]
            curr_items = [
                {"name": p.project_name, "desc": p.description or ""} for p in unmatched_curr
            ]

            prompt = (
                "You are an expert CSR analyst. Compare the following previously active CSR projects "
                "with the current CSR projects. Identify pairs of projects that represent substantially "
                "the same initiative despite differences in phrasing or naming.\n\n"
                f"Previous Projects: {prev_items}\n\n"
                f"Current Projects: {curr_items}\n\n"
                "Return a JSON array of objects with keys: 'previous_project', 'current_project', "
                "'similarity_score' (0.0 to 1.0), and 'rationale'."
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text or ""
            # Fallback if empty
            if not text.strip():
                return self._fallback.find_semantic_project_matches(unmatched_prev, unmatched_curr)

            import json
            clean_json = text.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_json)
            matches = []
            for item in parsed:
                matches.append(
                    ProjectSemanticMatch(
                        previous_project=item["previous_project"],
                        current_project=item["current_project"],
                        similarity_score=float(item.get("similarity_score", 0.8)),
                        rationale=item.get("rationale", "Gemini semantic similarity match"),
                    )
                )
            return matches
        except Exception:
            # Clean fallback to mock on API error or network failure
            return self._fallback.find_semantic_project_matches(unmatched_prev, unmatched_curr)

    def analyze_policy_shifts(
        self,
        prev_priorities: List[str],
        curr_priorities: List[str],
    ) -> Dict[str, Any]:
        return self._fallback.analyze_policy_shifts(prev_priorities, curr_priorities)
