"""
Deterministic Context-Aware Rule-Based Classifier for Task 6.
Serves as the standard mock provider for unit tests, offline development,
and fallback when external LLM APIs are unavailable.
Accurately distinguishes genuine community WASH programs from industrial water management.
"""

import time
from typing import Dict, List, Set, Tuple
from ai_service.classification.policy import WASHPolicy
from ai_service.classification.providers.base import BaseLLMProvider
from ai_service.schemas.classification import (
    EvidenceStrengthEnum,
    WASHClassificationEnum,
    WASHClassificationResult,
    WASHEvidenceItem,
)
from ai_service.schemas.preprocessing import CleanedCSRData


class MockRuleBasedProvider(BaseLLMProvider):
    """
    Context-aware rule-based classifier evaluating CSR text and structured records.
    Produces evidence-first classifications with calibrated confidence scores.
    """

    def __init__(self, model_name: str = "mock-wash-classifier-v1"):
        self.model_name = model_name

    def classify_csr_data(
        self,
        cleaned_data: CleanedCSRData,
        cleaned_text_by_page: Dict[int, str],
    ) -> WASHClassificationResult:
        start_time = time.time()
        evidence_items: List[WASHEvidenceItem] = []
        errors: List[str] = []

        total_text_chars = sum(len(t.strip()) for t in cleaned_text_by_page.values())
        records = cleaned_data.records or []

        # Check for insufficient evidence
        if total_text_chars < 30 and not records:
            return WASHClassificationResult(
                classification=WASHClassificationEnum.INSUFFICIENT_EVIDENCE.value,
                confidence=0.10,
                water_relevance=False,
                sanitation_relevance=False,
                hygiene_relevance=False,
                reasoning=(
                    "Document contains negligible extractable text and zero structured CSR project records. "
                    "Insufficient data to evaluate WASH relevance."
                ),
                evidence=[],
                evidence_pages=[],
                model_used=self.model_name,
                document_metadata={},
                processing_time_seconds=round(time.time() - start_time, 4),
                errors=errors,
            )

        # 1. Evaluate structured records
        water_found = False
        sanitation_found = False
        hygiene_found = False
        watershed_found = False
        industrial_found = False

        for rec in records:
            combined_rec_text = " ".join(
                filter(None, [rec.project_name, rec.category, rec.location, rec.beneficiaries])
            ).lower()

            page_num = rec.page_number or 1

            # Check industrial exclusion
            ind_terms = self._find_matching_terms(combined_rec_text, WASHPolicy.INDUSTRIAL_EXCLUSION_TERMS)
            if ind_terms:
                industrial_found = True
                evidence_items.append(
                    WASHEvidenceItem(
                        text=f"Project '{rec.project_name}': {', '.join(ind_terms)}",
                        page=page_num,
                        category="negative_industrial",
                        project_name=rec.project_name,
                        strength=EvidenceStrengthEnum.NEGATIVE.value,
                    )
                )

            # Check safe drinking water
            w_terms = self._find_matching_terms(combined_rec_text, WASHPolicy.DRINKING_WATER_TERMS)
            if w_terms:
                water_found = True
                evidence_items.append(
                    WASHEvidenceItem(
                        text=f"Project '{rec.project_name}': {', '.join(w_terms)} (Category: {rec.category or 'N/A'})",
                        page=page_num,
                        category="water",
                        project_name=rec.project_name,
                        strength=EvidenceStrengthEnum.STRONG.value,
                    )
                )

            # Check sanitation
            s_terms = self._find_matching_terms(combined_rec_text, WASHPolicy.SANITATION_TERMS)
            if s_terms:
                sanitation_found = True
                evidence_items.append(
                    WASHEvidenceItem(
                        text=f"Project '{rec.project_name}': {', '.join(s_terms)}",
                        page=page_num,
                        category="sanitation",
                        project_name=rec.project_name,
                        strength=EvidenceStrengthEnum.STRONG.value,
                    )
                )

            # Check hygiene
            h_terms = self._find_matching_terms(combined_rec_text, WASHPolicy.HYGIENE_TERMS)
            if h_terms:
                hygiene_found = True
                evidence_items.append(
                    WASHEvidenceItem(
                        text=f"Project '{rec.project_name}': {', '.join(h_terms)}",
                        page=page_num,
                        category="hygiene",
                        project_name=rec.project_name,
                        strength=EvidenceStrengthEnum.STRONG.value,
                    )
                )

            # Check watershed
            ws_terms = self._find_matching_terms(combined_rec_text, WASHPolicy.WATERSHED_COMMUNITY_TERMS)
            if ws_terms and not (w_terms or s_terms or h_terms):
                watershed_found = True
                evidence_items.append(
                    WASHEvidenceItem(
                        text=f"Project '{rec.project_name}': {', '.join(ws_terms)}",
                        page=page_num,
                        category="community_wash",
                        project_name=rec.project_name,
                        strength=EvidenceStrengthEnum.WEAK.value,
                    )
                )

        # 2. Evaluate page-by-page text for additional narrative evidence
        for page_num, page_text in cleaned_text_by_page.items():
            text_lower = page_text.lower()

            # Industrial check
            ind_page_terms = self._find_matching_terms(text_lower, WASHPolicy.INDUSTRIAL_EXCLUSION_TERMS)
            if ind_page_terms and not industrial_found:
                industrial_found = True
                snippet = self._extract_snippet(page_text, list(ind_page_terms)[0])
                evidence_items.append(
                    WASHEvidenceItem(
                        text=snippet,
                        page=page_num,
                        category="negative_industrial",
                        strength=EvidenceStrengthEnum.NEGATIVE.value,
                    )
                )

            # Drinking water check
            w_page_terms = self._find_matching_terms(text_lower, WASHPolicy.DRINKING_WATER_TERMS)
            if w_page_terms:
                water_found = True
                snippet = self._extract_snippet(page_text, list(w_page_terms)[0])
                evidence_items.append(
                    WASHEvidenceItem(
                        text=snippet,
                        page=page_num,
                        category="water",
                        strength=EvidenceStrengthEnum.STRONG.value,
                    )
                )

            # Sanitation check
            s_page_terms = self._find_matching_terms(text_lower, WASHPolicy.SANITATION_TERMS)
            if s_page_terms:
                sanitation_found = True
                snippet = self._extract_snippet(page_text, list(s_page_terms)[0])
                evidence_items.append(
                    WASHEvidenceItem(
                        text=snippet,
                        page=page_num,
                        category="sanitation",
                        strength=EvidenceStrengthEnum.STRONG.value,
                    )
                )

            # Hygiene check
            h_page_terms = self._find_matching_terms(text_lower, WASHPolicy.HYGIENE_TERMS)
            if h_page_terms:
                hygiene_found = True
                snippet = self._extract_snippet(page_text, list(h_page_terms)[0])
                evidence_items.append(
                    WASHEvidenceItem(
                        text=snippet,
                        page=page_num,
                        category="hygiene",
                        strength=EvidenceStrengthEnum.STRONG.value,
                    )
                )

            # Watershed check
            ws_page_terms = self._find_matching_terms(text_lower, WASHPolicy.WATERSHED_COMMUNITY_TERMS)
            if ws_page_terms and not (water_found or sanitation_found or hygiene_found):
                watershed_found = True
                snippet = self._extract_snippet(page_text, list(ws_page_terms)[0])
                evidence_items.append(
                    WASHEvidenceItem(
                        text=snippet,
                        page=page_num,
                        category="community_wash",
                        strength=EvidenceStrengthEnum.WEAK.value,
                    )
                )

        # Unique evidence pages
        evidence_pages = sorted(list({ev.page for ev in evidence_items if ev.page is not None}))

        # 3. Apply Decision Policy
        # Case A: Genuine Strong Community WASH
        if water_found or sanitation_found or hygiene_found:
            active_pillars = []
            if water_found:
                active_pillars.append("Safe Drinking Water")
            if sanitation_found:
                active_pillars.append("Community Sanitation")
            if hygiene_found:
                active_pillars.append("Hygiene")

            confidence = 0.92 if len(active_pillars) > 1 else 0.86
            classification = WASHClassificationEnum.WASH_RELEVANT.value
            reasoning = (
                f"Document provides explicit evidence of community CSR programs in {', '.join(active_pillars)}. "
                f"Identified {len(evidence_items)} supporting evidence records across pages {evidence_pages}."
            )

        # Case B: Industrial operational water only (ETP, cooling, ZLD) -> NOT_WASH_RELEVANT
        elif industrial_found and not (water_found or sanitation_found or hygiene_found or watershed_found):
            classification = WASHClassificationEnum.NOT_WASH_RELEVANT.value
            confidence = 0.88
            reasoning = (
                "Water-related mentions pertain strictly to internal industrial operational water management, "
                "effluent treatment plants (ETP), cooling water, or zero liquid discharge (ZLD). "
                "No community-facing drinking water or sanitation CSR programs were found."
            )

        # Case C: Broad rural watershed / check dams without direct drinking water or sanitation -> PARTIALLY_RELEVANT
        elif watershed_found:
            classification = WASHClassificationEnum.PARTIALLY_RELEVANT.value
            confidence = 0.65
            reasoning = (
                "Document contains community water conservation or rural watershed development initiatives. "
                "However, direct safe drinking water access, sanitation, or hygiene infrastructure was not explicitly detailed."
            )

        # Case D: Non-WASH CSR (Education, Healthcare, Sports, Rural infra without water)
        else:
            classification = WASHClassificationEnum.NOT_WASH_RELEVANT.value
            confidence = 0.85
            reasoning = (
                "CSR activities focus on non-WASH sectors (e.g. education, general healthcare, livelihood, sports). "
                "No meaningful safe drinking water, sanitation, or hygiene initiatives were identified."
            )

        return WASHClassificationResult(
            classification=classification,
            confidence=round(confidence, 2),
            water_relevance=water_found,
            sanitation_relevance=sanitation_found,
            hygiene_relevance=hygiene_found,
            reasoning=reasoning,
            evidence=evidence_items,
            evidence_pages=evidence_pages,
            model_used=self.model_name,
            document_metadata={},
            processing_time_seconds=round(time.time() - start_time, 4),
            errors=errors,
        )

    def _find_matching_terms(self, text: str, term_set: Set[str]) -> Set[str]:
        matches = set()
        for term in term_set:
            if term in text:
                matches.add(term)
        return matches

    def _extract_snippet(self, text: str, term: str, window: int = 100) -> str:
        idx = text.lower().find(term.lower())
        if idx == -1:
            return text[:window * 2]
        start = max(0, idx - window)
        end = min(len(text), idx + len(term) + window)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet
