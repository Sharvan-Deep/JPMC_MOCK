"""
Gemini LLM Provider Implementation for Task 6.
Invokes Google Gemini API when configured; gracefully falls back to the deterministic
rule-based engine when API keys are absent or network is unavailable.
Never fakes successful external API calls.
"""

import json
import os
import time
from typing import Dict, Optional
import httpx

from ai_service.classification.policy import WASHPolicy
from ai_service.classification.providers.base import BaseLLMProvider
from ai_service.classification.providers.mock_provider import MockRuleBasedProvider
from ai_service.logging_config import logger
from ai_service.schemas.classification import (
    WASHClassificationResult,
    WASHEvidenceItem,
)
from ai_service.schemas.preprocessing import CleanedCSRData


class GeminiProvider(BaseLLMProvider):
    """Integrates Google Gemini API for structured CSR WASH classification."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.fallback_provider = MockRuleBasedProvider(model_name=f"fallback-{model_name}")

    def classify_csr_data(
        self,
        cleaned_data: CleanedCSRData,
        cleaned_text_by_page: Dict[int, str],
    ) -> WASHClassificationResult:
        start_time = time.time()

        if not self.api_key:
            logger.info("No GEMINI_API_KEY configured. Executing deterministic classification.")
            result = self.fallback_provider.classify_csr_data(cleaned_data, cleaned_text_by_page)
            result.model_used = f"gemini-offline-rulebased ({self.model_name})"
            return result

        # Prepare payload for Gemini REST API
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        prompt = self._build_prompt(cleaned_data, cleaned_text_by_page)

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(
                    endpoint,
                    headers={"Content-Type": "application/json"},
                    json={
                        "system_instruction": {"parts": [{"text": WASHPolicy.get_system_prompt()}]},
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "response_mime_type": "application/json",
                            "temperature": 0.0,
                        },
                    },
                )

            if resp.status_code != 200:
                logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text[:200]}")
                fallback_res = self.fallback_provider.classify_csr_data(cleaned_data, cleaned_text_by_page)
                fallback_res.errors.append(f"Gemini API HTTP {resp.status_code}; utilized deterministic fallback")
                return fallback_res

            response_json = resp.json()
            candidates = response_json.get("candidates", [])
            if not candidates:
                fallback_res = self.fallback_provider.classify_csr_data(cleaned_data, cleaned_text_by_page)
                fallback_res.errors.append("Gemini returned 0 candidates; utilized fallback")
                return fallback_res

            text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            parsed_data = json.loads(text_content)

            evidence_items = [
                WASHEvidenceItem(
                    text=ev.get("text", ""),
                    page=ev.get("page"),
                    category=ev.get("category", "water"),
                    project_name=ev.get("project_name"),
                    strength=ev.get("strength", "STRONG"),
                )
                for ev in parsed_data.get("evidence", [])
            ]

            evidence_pages = sorted(list({ev.page for ev in evidence_items if ev.page is not None}))

            return WASHClassificationResult(
                classification=parsed_data.get("classification", "NOT_WASH_RELEVANT"),
                confidence=float(parsed_data.get("confidence", 0.70)),
                water_relevance=bool(parsed_data.get("water_relevance", False)),
                sanitation_relevance=bool(parsed_data.get("sanitation_relevance", False)),
                hygiene_relevance=bool(parsed_data.get("hygiene_relevance", False)),
                reasoning=parsed_data.get("reasoning", "Classified via Gemini model"),
                evidence=evidence_items,
                evidence_pages=evidence_pages,
                model_used=f"gemini ({self.model_name})",
                document_metadata={},
                processing_time_seconds=round(time.time() - start_time, 4),
                errors=[],
            )

        except Exception as exc:
            logger.warning(f"Gemini invocation failed ({exc}); executing fallback")
            fallback_res = self.fallback_provider.classify_csr_data(cleaned_data, cleaned_text_by_page)
            fallback_res.errors.append(f"Gemini invocation exception: {str(exc)}")
            return fallback_res

    def _build_prompt(self, cleaned_data: CleanedCSRData, cleaned_text_by_page: Dict[int, str]) -> str:
        records_summary = []
        for r in cleaned_data.records:
            records_summary.append(
                f"- Page {r.page_number}: Project='{r.project_name}', Category='{r.category}', "
                f"Location='{r.location}', Spent={r.raw_amount_spent} (Norm: {r.normalized_amount_spent_crore} Cr)"
            )

        text_sample = "\n\n".join(
            f"[Page {p}]:\n{t[:1000]}" for p, t in list(cleaned_text_by_page.items())[:5]
        )

        return (
            f"Company: {cleaned_data.canonical_company_name or cleaned_data.raw_company_name}\n"
            f"Financial Year: {cleaned_data.normalized_financial_year}\n"
            f"Total CSR Expenditure: {cleaned_data.raw_total_csr_amount}\n\n"
            f"Cleaned Project Records ({len(cleaned_data.records)} items):\n"
            f"{chr(10).join(records_summary) if records_summary else 'No structured table records'}\n\n"
            f"Page Text Excerpts:\n{text_sample}\n\n"
            "Classify whether this CSR report represents genuine community WASH activity."
        )
