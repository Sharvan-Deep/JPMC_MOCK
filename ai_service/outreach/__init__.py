"""
Outreach module for Task 13: Outreach Drafting Assistant.
"""

from ai_service.outreach.providers import (
    BaseOutreachDraftProvider,
    GeminiOutreachDraftProvider,
    MockOutreachDraftProvider,
)
from ai_service.outreach.repository import OutreachRepository
from ai_service.outreach.sender import BaseEmailSender, EmailSendResult, MockEmailSender
from ai_service.outreach.service import CSROutreachAssistantService
from ai_service.outreach.validator import ClaimValidator

__all__ = [
    "BaseOutreachDraftProvider",
    "MockOutreachDraftProvider",
    "GeminiOutreachDraftProvider",
    "OutreachRepository",
    "BaseEmailSender",
    "MockEmailSender",
    "EmailSendResult",
    "ClaimValidator",
    "CSROutreachAssistantService",
]
