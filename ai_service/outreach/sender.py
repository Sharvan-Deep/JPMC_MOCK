"""
Email Sending Boundary & Abstraction for Task 13: Outreach Drafting Assistant.

Strict Human-in-the-Loop Rules:
- An email can ONLY be sent if its status is APPROVED.
- Unapproved or Draft emails MUST be blocked from transmission.
- Uses MockEmailSender for offline testing and safe default execution.
- Never invents credentials or exposes secrets.
"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
from ai_service.schemas.outreach import OutreachApprovalStatus, OutreachDraft


class EmailSendResult(BaseModel):
    """Result of an email transmission attempt."""

    success: bool
    status: str
    message: str
    error: Optional[str] = None


class BaseEmailSender(ABC):
    """Abstract interface for sending corporate CSR outreach emails."""

    @abstractmethod
    def send_email(
        self,
        draft: OutreachDraft,
        recipient_email: str,
        sender_email: Optional[str] = None,
    ) -> EmailSendResult:
        """Transmits the approved draft to the specified recipient."""
        pass


class MockEmailSender(BaseEmailSender):
    """
    Safe Mock Email Sender for local development and unit tests.
    Strictly verifies approval boundary, records delivery payload, and simulates delivery.
    """

    def __init__(self, simulate_failure: bool = False):
        self.simulate_failure = simulate_failure
        self.sent_messages = []

    def send_email(
        self,
        draft: OutreachDraft,
        recipient_email: str,
        sender_email: Optional[str] = None,
    ) -> EmailSendResult:
        # Strict boundary enforcement
        if draft.approval_status != OutreachApprovalStatus.APPROVED:
            return EmailSendResult(
                success=False,
                status="FAILED",
                message="Cannot send unapproved draft. Explicit human approval is strictly required.",
                error="UNAPPROVED_DRAFT",
            )

        if not recipient_email or "@" not in recipient_email:
            return EmailSendResult(
                success=False,
                status="FAILED",
                message="Invalid or missing recipient email address.",
                error="INVALID_RECIPIENT",
            )

        if self.simulate_failure:
            return EmailSendResult(
                success=False,
                status="FAILED",
                message="Simulated SMTP / transmission failure.",
                error="TRANSMISSION_ERROR",
            )

        effective_sender = sender_email or "partnerships@jaldhaara.org"
        message_record = {
            "draft_id": draft.draft_id,
            "company": draft.company,
            "to": recipient_email,
            "from": effective_sender,
            "subject": draft.subject,
            "body": draft.body,
            "draft_version": draft.draft_version,
        }
        self.sent_messages.append(message_record)

        return EmailSendResult(
            success=True,
            status="SENT",
            message=f"Email successfully delivered to {recipient_email} (mock delivery).",
        )
