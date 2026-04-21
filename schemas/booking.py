from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from schemas.base import NonEmptyStr, OpsSuiteBaseModel, ShortStr, UtcDateTime, utcnow
from schemas.pulse import ThemeCategory


class VoiceState(StrEnum):
    GREETING = "greeting"
    INTENT_CAPTURE = "intent_capture"
    SLOT_FILLING = "slot_filling"
    CONFIRMATION = "confirmation"
    BOOKED = "booked"
    FAILED = "failed"


_BOOKING_CODE_RE = re.compile(r"^IND-([A-Z]{3,10})-(\d{8})-(\d{3})$")


class BookingCode(OpsSuiteBaseModel):
    raw: Annotated[str, Field(pattern=r"^IND-[A-Z]{3,10}-\d{8}-\d{3}$")]
    theme_code: Annotated[str, Field(pattern=r"^[A-Z]{3,10}$")]
    date: Annotated[str, Field(pattern=r"^\d{8}$")]
    sequence: Annotated[int, Field(ge=1, le=999)]

    @model_validator(mode="after")
    def raw_matches_components(self) -> BookingCode:
        m = _BOOKING_CODE_RE.match(self.raw)
        if not m:
            raise ValueError(
                f"raw='{self.raw}' does not match expected "
                "format IND-<THEME>-<YYYYMMDD>-<seq>."
            )
        parsed_theme, parsed_date, parsed_seq_str = m.group(1), m.group(2), m.group(3)
        parsed_seq = int(parsed_seq_str)
        errors: list[str] = []
        if parsed_theme != self.theme_code:
            errors.append(
                f"theme_code='{self.theme_code}' disagrees with raw parsed '{parsed_theme}'"
            )
        if parsed_date != self.date:
            errors.append(
                f"date='{self.date}' disagrees with raw parsed '{parsed_date}'"
            )
        if parsed_seq != self.sequence:
            errors.append(
                f"sequence={self.sequence} disagrees with raw parsed {parsed_seq}"
            )
        if errors:
            raise ValueError(
                "BookingCode components do not match raw string: "
                + "; ".join(errors)
                + ". Ensure raw, theme_code, date, and sequence are consistent."
            )
        return self

    @classmethod
    def parse(cls, raw: str) -> BookingCode:
        m = _BOOKING_CODE_RE.match(raw)
        if not m:
            raise ValueError(
                f"Cannot parse '{raw}' as BookingCode. "
                "Expected format: IND-<THEME>-<YYYYMMDD>-<seq> e.g. 'IND-NOM-20260420-001'."
            )
        return cls(
            raw=raw,
            theme_code=m.group(1),
            date=m.group(2),
            sequence=int(m.group(3)),
        )


class TurnContext(OpsSuiteBaseModel):
    session_id: ShortStr
    state: VoiceState
    top_theme: ThemeCategory
    captured_intent: Annotated[str, Field(default="", max_length=500)] = ""
    slots: dict[str, str] = Field(default_factory=dict)
    turn_count: Annotated[int, Field(ge=0, default=0)] = 0
    updated_at: UtcDateTime = Field(default_factory=utcnow)
    request_id: ShortStr


class Booking(OpsSuiteBaseModel):
    code: BookingCode
    session_id: ShortStr
    theme: ThemeCategory
    captured_intent: NonEmptyStr
    slots_json: dict[str, str]
    created_at: UtcDateTime = Field(default_factory=utcnow)
    request_id: ShortStr


class VoiceCallContext(OpsSuiteBaseModel):
    booking: Booking
    pulse_snapshot_id: ShortStr
    transcript: list[dict[str, str]]
