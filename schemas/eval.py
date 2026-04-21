from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, conlist

from schemas.base import DocId, NonEmptyStr, OpsSuiteBaseModel, ShortStr, UtcDateTime, utcnow


class EvalKind(StrEnum):
    RAG = "rag"
    ADVERSARIAL = "adversarial"
    UX = "ux"


class EvalVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class EvalCase(OpsSuiteBaseModel):
    id: ShortStr
    kind: EvalKind
    prompt: NonEmptyStr
    expected_refusal: bool = False
    expected_sources: list[DocId] = Field(default_factory=list)
    expected_answer_covers: list[str] = Field(default_factory=list)
    category: ShortStr = ""


class JudgeScore(OpsSuiteBaseModel):
    dimension: Literal["faithfulness", "relevance", "refusal_correctness"]
    score: Annotated[float, Field(ge=0.0, le=5.0)]
    reasoning: NonEmptyStr
    judge_model: ShortStr


class EvalResult(OpsSuiteBaseModel):
    case_id: ShortStr
    kind: EvalKind
    verdict: EvalVerdict
    scores: list[JudgeScore] = Field(default_factory=list)
    deterministic_checks: dict[str, bool] = Field(default_factory=dict)
    raw_output: NonEmptyStr
    ran_at: UtcDateTime = Field(default_factory=utcnow)
    latency_ms: Annotated[int, Field(ge=0)]
    request_id: ShortStr


class JudgeCalibration(OpsSuiteBaseModel):
    iteration: Annotated[int, Field(ge=1, le=10)]
    sample_size: Annotated[int, Field(ge=5)]
    exact_match_agreement: Annotated[float, Field(ge=0.0, le=1.0)]
    within_1_agreement: Annotated[float, Field(ge=0.0, le=1.0)]
    threshold_met: bool
    mismatches: list[dict] = Field(default_factory=list)  # type: ignore[type-arg]
    calibrated_at: UtcDateTime = Field(default_factory=utcnow)


class EvalReport(OpsSuiteBaseModel):
    run_id: ShortStr
    started_at: UtcDateTime
    completed_at: UtcDateTime
    results: conlist(EvalResult, min_length=1)  # type: ignore[valid-type]
    calibration: JudgeCalibration
    overall_pass: bool
    summary_stats: dict[str, float]
