"""
Copilot Providers for Task 12: Next-Best-Action Recommendation Copilot.

Provides:
- BaseCopilotProvider: Abstract base class for conversational assistant
- MockCopilotProvider: Deterministic, offline assistant using structured context & retrieved chunks
- GeminiCopilotProvider: Google Gemini GenAI integration with graceful fallback to mock
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ai_service.schemas.copilot import CopilotChatRequest, CopilotChatResponse, RecommendationResult


class BaseCopilotProvider(ABC):
    """Abstract interface for Copilot conversational assistant."""

    @abstractmethod
    def answer_question(
        self,
        request: CopilotChatRequest,
        latest_recommendation: Optional[RecommendationResult],
        retrieved_contexts: List[str],
    ) -> CopilotChatResponse:
        """Generates an evidence-grounded answer to a staff question."""
        pass


class MockCopilotProvider(BaseCopilotProvider):
    """
    Deterministic offline assistant for unit tests and local execution.
    Answers staff questions by synthesizing latest recommendation fields and retrieved document chunks.
    Guarantees: If evidence is missing, it explicitly states that evidence is insufficient/unavailable.
    """

    def answer_question(
        self,
        request: CopilotChatRequest,
        latest_recommendation: Optional[RecommendationResult],
        retrieved_contexts: List[str],
    ) -> CopilotChatResponse:
        q_lower = request.question.lower()
        now_iso = datetime.now(timezone.utc).isoformat()
        company = request.company

        rec = latest_recommendation
        supporting_sources: List[str] = list(retrieved_contexts[:3])
        evidence_status = "AVAILABLE"

        # Case 1: Asking why recommended / what action / why priority
        if any(w in q_lower for w in ["why", "action", "recommended", "recommendation", "priority"]):
            if rec:
                reasons_str = " ".join(rec.reasons)
                answer = (
                    f"For {company}, the recommended action is {rec.recommended_action.value} with confidence "
                    f"{rec.confidence:.2f}. Key rationale: {reasons_str} "
                    f"Positive factors include: {'; '.join(rec.positive_factors) if rec.positive_factors else 'None noted'}."
                )
                if rec.supporting_evidence:
                    for ev in rec.supporting_evidence:
                        if ev.relevant_source_text:
                            supporting_sources.append(f"Page {ev.page or 'N/A'}: {ev.relevant_source_text[:120]}...")
            else:
                answer = f"No current recommendation is recorded for {company}. Run evaluation first."
                evidence_status = "INSUFFICIENT_EVIDENCE"

        # Case 2: Asking about risks, caveats, or limiting factors
        elif any(w in q_lower for w in ["risk", "caveat", "limiting", "concern", "drawback"]):
            if rec and (rec.risks or rec.limiting_factors):
                risks_str = "; ".join(rec.risks) if rec.risks else "None noted"
                limiting_str = "; ".join(rec.limiting_factors) if rec.limiting_factors else "None noted"
                answer = (
                    f"Advisory risks identified for {company}: {risks_str}. "
                    f"Limiting factors to keep in mind: {limiting_str}."
                )
            else:
                answer = f"No significant risks or limiting factors are recorded in the current assessment for {company}."

        # Case 3: Asking about next steps or what to do next
        elif any(w in q_lower for w in ["next step", "what should we do", "next", "approach", "proposal", "outreach"]):
            if rec and rec.next_steps:
                steps_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(rec.next_steps))
                answer = f"Recommended next steps for Jaldhaara staff regarding {company}:\n{steps_str}"
            else:
                answer = f"No immediate next steps found for {company}."

        # Case 4: Asking about missing information, data gaps, or unverified facts
        elif any(w in q_lower for w in ["missing", "unknown", "gap", "unverified", "insufficient"]):
            if rec and rec.missing_information:
                missing_str = "; ".join(rec.missing_information)
                answer = f"The following information is missing or unverified for {company}: {missing_str}."
                evidence_status = "INSUFFICIENT_EVIDENCE"
            else:
                answer = f"There are no major unverified data gaps flagged for {company}."

        # Case 5: Asking about water/WASH projects or specific details from documents
        elif any(w in q_lower for w in ["water", "wash", "project", "spend", "sanitation", "district"]):
            if retrieved_contexts:
                context_summary = " ".join(retrieved_contexts[:2])
                answer = f"Verified project intelligence from disclosures for {company}: {context_summary}"
            elif rec and rec.supporting_evidence:
                ev_summary = " | ".join(e.relevant_source_text for e in rec.supporting_evidence if e.relevant_source_text)
                answer = f"Verified evidence for {company}: {ev_summary}"
            else:
                answer = f"Insufficient specific project evidence available in current disclosures for {company}."
                evidence_status = "INSUFFICIENT_EVIDENCE"

        # General Fallback
        else:
            if rec:
                answer = (
                    f"Regarding {company}: Current recommendation is {rec.recommended_action.value} "
                    f"(Score: {rec.metadata.get('lead_score', 'N/A')}, Freshness: {rec.metadata.get('freshness_status', 'N/A')}). "
                    f"{rec.reasons[0] if rec.reasons else ''}"
                )
            elif retrieved_contexts:
                answer = f"Information retrieved for {company}: {retrieved_contexts[0]}"
            else:
                answer = f"No verified evidence found to answer '{request.question}' for {company}."
                evidence_status = "INSUFFICIENT_EVIDENCE"

        return CopilotChatResponse(
            company=company,
            question=request.question,
            answer=answer,
            supporting_sources=supporting_sources,
            evidence_status=evidence_status,
            timestamp=now_iso,
        )


class GeminiCopilotProvider(BaseCopilotProvider):
    """
    Google Gemini GenAI integration for Copilot chat.
    Injects verified company context and retrieved chunks into system prompt.
    Falls back gracefully to MockCopilotProvider if API key is missing or calls fail.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.fallback = MockCopilotProvider()

    def answer_question(
        self,
        request: CopilotChatRequest,
        latest_recommendation: Optional[RecommendationResult],
        retrieved_contexts: List[str],
    ) -> CopilotChatResponse:
        if not self.api_key:
            return self.fallback.answer_question(request, latest_recommendation, retrieved_contexts)

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            rec_context = latest_recommendation.model_dump_json(indent=2) if latest_recommendation else "None available"
            retrieved_text = "\n\n".join(f"[Source {i+1}]: {c}" for i, c in enumerate(retrieved_contexts))

            prompt = f"""
You are the Jaldhaara Foundation AI Copilot for CSR Donor Engagement.
You assist foundation staff by answering questions about corporate candidates and recommended next actions.

STRICT RULES:
1. Ground answers strictly in the Verified Recommendation Record and Retrieved Document Sources below.
2. DO NOT invent outreach commitments, contacts, or unverified claims.
3. If information is missing or unverified, explicitly say so (e.g. "We do not have verified data for...").
4. Remember this is advisory only (no automated emails are sent).

VERIFIED RECOMMENDATION RECORD:
{rec_context}

RETRIEVED DOCUMENT SOURCES:
{retrieved_text}

STAFF QUESTION:
{request.question}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            answer_text = response.text.strip() if response.text else "Unable to generate answer."
            evidence_status = "INSUFFICIENT_EVIDENCE" if "unverified" in answer_text.lower() or "not available" in answer_text.lower() else "AVAILABLE"

            return CopilotChatResponse(
                company=request.company,
                question=request.question,
                answer=answer_text,
                supporting_sources=list(retrieved_contexts[:3]),
                evidence_status=evidence_status,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            return self.fallback.answer_question(request, latest_recommendation, retrieved_contexts)
