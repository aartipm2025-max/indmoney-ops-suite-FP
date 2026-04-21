from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, conlist, field_validator, model_validator

from schemas.base import NonEmptyStr, OpsSuiteBaseModel, ShortStr, UtcDateTime, utcnow
from schemas.booking import BookingCode
from schemas.pulse import Theme

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OpStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"


class OpType(StrEnum):
    CALENDAR_HOLD = "calendar_hold"
    EMAIL_DRAFT = "email_draft"


class RejectReason(StrEnum):
    INCORRECT_THEME = "incorrect_theme"
    WRONG_CONTACT = "wrong_contact"
    DUPLICATE = "duplicate"
    LOW_CONFIDENCE = "low_confidence"
    OTHER = "other"


class AdvisorBriefingCard(OpsSuiteBaseModel):
    top_themes: conlist(Theme, min_length=3, max_length=3)  # type: ignore[valid-type]
    sentiment_shift: Literal["improving", "declining", "stable"]
    pain_points: conlist(ShortStr, min_length=2, max_length=2)  # type: ignore[valid-type]
    talking_points: conlist(ShortStr, min_length=3, max_length=3)  # type: ignore[valid-type]
    booking_code: BookingCode


class CalendarHold(OpsSuiteBaseModel):
    summary: ShortStr
    description: NonEmptyStr
    start_utc: UtcDateTime
    end_utc: UtcDateTime
    attendees: conlist(str, min_length=1, max_length=5)  # type: ignore[valid-type]
    booking_code: BookingCode
    idempotency_id: Annotated[str, Field(pattern=r"^[a-v0-9]{12,26}$")]

    @model_validator(mode="after")
    def end_after_start(self) -> CalendarHold:
        if self.end_utc <= self.start_utc:
            raise ValueError(
                f"end_utc ({self.end_utc.isoformat()}) must be after "
                f"start_utc ({self.start_utc.isoformat()}). Set end_utc > start_utc."
            )
        duration_minutes = (self.end_utc - self.start_utc).total_seconds() / 60
        if duration_minutes < 15:
            raise ValueError(
                f"Calendar hold duration is {duration_minutes:.0f} minutes "
                "but must be >= 15 minutes."
            )
        if duration_minutes > 120:
            raise ValueError(
                f"Calendar hold duration is {duration_minutes:.0f} minutes "
                "but must be <= 120 minutes."
            )
        return self

    @field_validator("attendees")
    @classmethod
    def valid_emails(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if not _EMAIL_RE.match(e)]
        if invalid:
            raise ValueError(
                f"Invalid email address(es) in attendees: {invalid}. "
                "Each attendee must be a valid email like user@domain.com."
            )
        return v


class EmailDraft(OpsSuiteBaseModel):
    to: conlist(str, min_length=1, max_length=5)  # type: ignore[valid-type]
    subject: Annotated[str, Field(pattern=r".*\[IND-[A-Z]{3,10}-\d{8}-\d{3}\].*")]
    body_html: NonEmptyStr
    body_plain: NonEmptyStr
    briefing_card: AdvisorBriefingCard
    booking_code: BookingCode

    @field_validator("to")
    @classmethod
    def valid_emails(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if not _EMAIL_RE.match(e)]
        if invalid:
            raise ValueError(
                f"Invalid email address(es) in 'to': {invalid}. "
                "Each recipient must be a valid email like user@domain.com."
            )
        return v


class PendingOp(OpsSuiteBaseModel):
    id: ShortStr
    op_type: OpType
    status: OpStatus
    payload_json: dict  # type: ignore[type-arg]
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128)]
    created_at: UtcDateTime = Field(default_factory=utcnow)
    approved_at: UtcDateTime | None = None
    executed_at: UtcDateTime | None = None
    retry_count: Annotated[int, Field(ge=0, default=0)] = 0
    last_error: str = ""
    external_ids: dict[str, str] = Field(default_factory=dict)
    reject_reason: RejectReason | None = None
    reject_reason_text: Annotated[str, Field(default="", max_length=500)] = ""
    request_id: ShortStr

    @model_validator(mode="after")
    def status_invariants(self) -> PendingOp:
        errors: list[str] = []
        if self.status == OpStatus.REJECTED and self.reject_reason is None:
            errors.append(
                "status='rejected' requires reject_reason to be set. "
                "Provide a RejectReason value."
            )
        if self.status == OpStatus.EXECUTED and self.executed_at is None:
            errors.append(
                "status='executed' requires executed_at to be set. "
                "Provide the execution timestamp."
            )
        if self.status == OpStatus.APPROVED and self.approved_at is None:
            errors.append(
                "status='approved' requires approved_at to be set. "
                "Provide the approval timestamp."
            )
        if self.status == OpStatus.FAILED and not self.last_error:
            errors.append(
                "status='failed' requires last_error to be non-empty. "
                "Provide the error message that caused the failure."
            )
        if errors:
            raise ValueError(" | ".join(errors))
        return self


class ApprovalDecision(OpsSuiteBaseModel):
    op_id: ShortStr
    decision: Literal["approve", "reject"]
    reject_reason: RejectReason | None = None
    reject_reason_text: str = ""
    decided_by: ShortStr
    decided_at: UtcDateTime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def reject_needs_reason(self) -> ApprovalDecision:
        if self.decision == "reject" and self.reject_reason is None:
            raise ValueError(
                "decision='reject' requires reject_reason to be set. "
                "Provide a RejectReason value (e.g. RejectReason.DUPLICATE)."
            )
        return self
