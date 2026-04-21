from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, conlist, field_validator, model_validator

from schemas.base import OpsSuiteBaseModel, ShortStr, UtcDateTime, utcnow


class ThemeCategory(StrEnum):
    LOGIN = "login"
    NOMINEE = "nominee"
    EXIT_LOAD = "exit_load"
    WITHDRAWAL = "withdrawal"
    SUPPORT = "support"
    OTHER = "other"


class TrendDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class TrendDelta(OpsSuiteBaseModel):
    theme: ThemeCategory
    this_week_count: Annotated[int, Field(ge=0)]
    prev_week_count: Annotated[int, Field(ge=0)]
    abs_delta: int
    pct_delta: float
    p_value: Annotated[float, Field(ge=0.0, le=1.0)]
    direction: TrendDirection
    is_significant: bool

    @model_validator(mode="after")
    def validate_derived_fields(self) -> TrendDelta:
        expected_abs = self.this_week_count - self.prev_week_count
        if self.abs_delta != expected_abs:
            raise ValueError(
                f"abs_delta={self.abs_delta} does not match "
                f"this_week_count - prev_week_count = {expected_abs}. "
                "Set abs_delta = this_week_count - prev_week_count."
            )
        if expected_abs > 0:
            derived_direction = TrendDirection.UP
        elif expected_abs < 0:
            derived_direction = TrendDirection.DOWN
        else:
            derived_direction = TrendDirection.FLAT

        if derived_direction != self.direction:
            raise ValueError(
                f"direction='{self.direction.value}' disagrees with computed direction "
                f"'{derived_direction.value}' (abs_delta={expected_abs}). "
                "Set direction to match the sign of abs_delta."
            )
        return self


class Theme(OpsSuiteBaseModel):
    category: ThemeCategory
    label: ShortStr
    count: Annotated[int, Field(ge=1)]
    example_review_ids: conlist(str, min_length=1, max_length=5)  # type: ignore[valid-type]
    trend: TrendDelta


class ActionIdea(OpsSuiteBaseModel):
    headline: Annotated[str, Field(min_length=10, max_length=150)]
    rationale: Annotated[str, Field(min_length=20, max_length=400)]
    linked_themes: conlist(ThemeCategory, min_length=1, max_length=3)  # type: ignore[valid-type]
    effort: Literal["low", "medium", "high"]


class Pulse(OpsSuiteBaseModel):
    week_start: UtcDateTime
    week_end: UtcDateTime
    summary: Annotated[str, Field(min_length=50, max_length=2000)]
    themes: conlist(Theme, min_length=3, max_length=8)  # type: ignore[valid-type]
    actions: conlist(ActionIdea, min_length=3, max_length=3)  # type: ignore[valid-type]
    total_reviews_analyzed: Annotated[int, Field(ge=1)]
    generated_at: UtcDateTime = Field(default_factory=utcnow)
    request_id: ShortStr

    @field_validator("summary")
    @classmethod
    def word_count_under_250(cls, v: str) -> str:
        count = len(v.split())
        if count > 250:
            raise ValueError(
                f"summary has {count} words but must be <= 250 words. "
                "Trim the summary to 250 words or fewer."
            )
        return v

    @model_validator(mode="after")
    def week_range_valid(self) -> Pulse:
        if self.week_end <= self.week_start:
            raise ValueError(
                "week_end must be after week_start. "
                f"Got week_start={self.week_start.isoformat()}, "
                f"week_end={self.week_end.isoformat()}."
            )
        delta = self.week_end - self.week_start
        if delta > timedelta(days=14):
            raise ValueError(
                f"week range is {delta.days} days but must be <= 14 days. "
                "Reduce the range between week_start and week_end."
            )
        return self
