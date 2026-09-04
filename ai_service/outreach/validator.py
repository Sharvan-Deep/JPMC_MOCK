"""
Claim Validation Engine for Task 13: Outreach Drafting Assistant.

Identifies factual claims in outreach emails:
- Numerical figures (e.g. ₹12.5 Cr, 45 villages, 12 RO plants)
- Geographic locations (e.g. Gujarat, Maharashtra)
- Project-specific and beneficiary claims

Checks whether each claim has supporting evidence in verified project data or citations.
Flags unsupported claims and issues warnings.
"""

import re
from typing import List, Set
from ai_service.schemas.outreach import ClaimValidationResult, CompanyOutreachContext, OutreachDraft
from ai_service.schemas.verification import CSREvidenceReference


class ClaimValidator:
    """Validates factual statements made in outreach drafts against evidence."""

    @classmethod
    def validate(cls, draft: OutreachDraft, context: CompanyOutreachContext) -> ClaimValidationResult:
        verified_claims: List[str] = []
        unsupported_claims: List[str] = []
        warnings: List[str] = []

        # Combine all verifiable text from context and evidence
        knowledge_corpus = " ".join([
            context.company,
            " ".join(context.geography),
            " ".join(context.commitments),
            " ".join(str(p.get("project_name", "")) + " " + str(p.get("location", "")) for p in context.projects),
            " ".join(e.relevant_source_text or "" for e in draft.evidence_used),
            " ".join(e.relevant_source_text or "" for e in context.evidence),
        ]).lower()

        text_to_check = f"{draft.subject} {draft.body}".lower()

        # 1. Geographic claims check
        common_indian_states = [
            "gujarat", "maharashtra", "rajasthan", "karnataka", "telangana",
            "andhra pradesh", "tamil nadu", "uttar pradesh", "bihar", "odisha",
            "madhya pradesh", "west bengal", "punjab", "haryana", "kerala"
        ]
        for state in common_indian_states:
            if state in text_to_check:
                if state in knowledge_corpus:
                    verified_claims.append(f"Geographic focus in {state.capitalize()} is corroborated by disclosures.")
                else:
                    unsupported_claims.append(f"Mentions geographic focus in {state.capitalize()}, which is not corroborated in verified disclosures.")

        # 2. Financial / Numerical spending claims
        # Look for patterns like ₹X Cr, Rs. X, X crore, X lakh
        spend_patterns = re.findall(r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)\s*(?:cr|crore|lakh)?", text_to_check)
        for amount in spend_patterns:
            if amount in knowledge_corpus:
                verified_claims.append(f"Financial figure '{amount}' matches verified CSR financial disclosures.")
            else:
                unsupported_claims.append(f"Financial figure '{amount}' does not appear in verified CSR disclosures.")

        # 3. Specific programmatic claims (e.g. RO plant, drinking water, sanitation)
        programmatic_keywords = ["ro plant", "drinking water", "sanitation", "toilet", "water kiosk", "purification"]
        for kw in programmatic_keywords:
            if kw in text_to_check:
                if kw in knowledge_corpus:
                    verified_claims.append(f"WASH initiative '{kw}' corroborated by verified project records.")
                else:
                    warnings.append(f"Mentions '{kw}', which has limited direct evidence in retrieved records.")

        # 4. Beneficiary / Absenteeism / School attendance statistic claims
        if any(w in text_to_check for w in ["absenteeism", "drop-out", "dropout rate"]):
            if "absenteeism" in knowledge_corpus or "dropout" in knowledge_corpus:
                verified_claims.append("School absenteeism / health statistic is backed by cited research.")
            else:
                unsupported_claims.append("Claim regarding school absenteeism / dropout rates is not verified in company disclosures.")

        # 5. Check if draft has unsupported_claims recorded from chat instructions
        for claim in draft.unsupported_claims:
            if claim not in unsupported_claims:
                unsupported_claims.append(claim)

        # 6. Advisory warnings
        if not draft.evidence_used:
            warnings.append("Draft does not currently link explicit traceable evidence references.")

        is_valid = len(unsupported_claims) == 0

        return ClaimValidationResult(
            verified_claims=verified_claims,
            unsupported_claims=unsupported_claims,
            warnings=warnings,
            is_valid_for_approval=is_valid,
        )
