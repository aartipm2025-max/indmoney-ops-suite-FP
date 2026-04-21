"""Phase 1 schema contract tests — positive + negative for every class."""
from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from schemas import (
    ActionIdea,
    AdvisorBriefingCard,
    ApprovalDecision,
    Booking,
    BookingCode,
    Bullet,
    CalendarHold,
    Citation,
    DocType,
    EmailDraft,
    EvalCase,
    EvalKind,
    EvalReport,
    EvalResult,
    EvalVerdict,
    JudgeCalibration,
    JudgeScore,
    OpStatus,
    OpType,
    PendingOp,
    Pulse,
    QueryRoute,
    RAGAnswer,
    RAGQuery,
    RejectReason,
    Theme,
    ThemeCategory,
    TrendDelta,
    TrendDirection,
    TurnContext,
    VoiceCallContext,
    VoiceState,
    utcnow,
)

# ---------------------------------------------------------------------------
# Shared fixtures / factories
# ---------------------------------------------------------------------------

UTC = dt.UTC
NOW = dt.datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
LATER = dt.datetime(2026, 4, 20, 13, 0, 0, tzinfo=UTC)


def make_citation(doc_id: str = "axis_elss", chunk_index: int = 0) -> Citation:
    return Citation(
        doc_id=doc_id,
        chunk_index=chunk_index,
        score=0.85,
        doc_type=DocType.FACTSHEET,
        section="exit_load",
    )


def make_bullet(doc_id: str = "axis_elss") -> Bullet:
    return Bullet(
        text=f"The fund has low exit load. [source:{doc_id}]",
        sources=[make_citation(doc_id)],
    )


def make_rag_answer(n_bullets: int = 6) -> dict[str, Any]:
    retrieved = [make_citation("axis_elss")]
    bullets = [make_bullet("axis_elss") for _ in range(n_bullets)]
    return dict(
        query="What is the exit load?",
        route=QueryRoute.FACT_ONLY,
        bullets=bullets,
        retrieved_chunks=retrieved,
        generated_at=NOW,
        model_name="llama3-70b",
        request_id="req-001",
    )


def make_trend_delta(this: int = 10, prev: int = 5) -> TrendDelta:
    delta = this - prev
    if delta > 0:
        direction = TrendDirection.UP
    elif delta < 0:
        direction = TrendDirection.DOWN
    else:
        direction = TrendDirection.FLAT
    return TrendDelta(
        theme=ThemeCategory.LOGIN,
        this_week_count=this,
        prev_week_count=prev,
        abs_delta=delta,
        pct_delta=100.0 * delta / prev if prev else 0.0,
        p_value=0.05,
        direction=direction,
        is_significant=True,
    )


def make_theme() -> Theme:
    return Theme(
        category=ThemeCategory.LOGIN,
        label="Cannot login after OTP",
        count=10,
        example_review_ids=["r1"],
        trend=make_trend_delta(),
    )


def make_action() -> ActionIdea:
    return ActionIdea(
        headline="Fix OTP login flow now",
        rationale="Login failures are the top complaint and drive churn among new users.",
        linked_themes=[ThemeCategory.LOGIN],
        effort="medium",
    )


def make_pulse(n_actions: int = 3) -> dict[str, Any]:
    return dict(
        week_start=dt.datetime(2026, 4, 14, 0, 0, 0, tzinfo=UTC),
        week_end=dt.datetime(2026, 4, 20, 23, 59, 59, tzinfo=UTC),
        summary=(
            "This week saw elevated login complaints following the OTP revamp rollout. "
            "Nominee update failures also spiked after a backend schema migration. "
            "Exit load queries remain steady, suggesting investor education "
            "content is working well."
        ),
        themes=[make_theme(), make_theme(), make_theme()],
        actions=[make_action() for _ in range(n_actions)],
        total_reviews_analyzed=200,
        generated_at=NOW,
        request_id="req-pulse-001",
    )


def make_booking_code(raw: str = "IND-NOM-20260420-001") -> BookingCode:
    return BookingCode.parse(raw)


def make_booking() -> Booking:
    return Booking(
        code=make_booking_code(),
        session_id="sess-001",
        theme=ThemeCategory.NOMINEE,
        captured_intent="Update nominee details",
        slots_json={"customer_name": "[REDACTED]"},
        created_at=NOW,
        request_id="req-001",
    )


def make_advisor_card() -> AdvisorBriefingCard:
    return AdvisorBriefingCard(
        top_themes=[make_theme(), make_theme(), make_theme()],
        sentiment_shift="declining",
        pain_points=["Login fails after OTP", "Nominee update broken"],
        talking_points=["Fix OTP flow", "Escalate nominee bug", "Offer callback"],
        booking_code=make_booking_code(),
    )


def make_calendar_hold() -> CalendarHold:
    return CalendarHold(
        summary="Advisor callback IND-NOM-20260420-001",
        description="Booked via INDmoney Ops Suite [IND-NOM-20260420-001]",
        start_utc=NOW,
        end_utc=LATER,
        attendees=["advisor@indmoney.com", "investor@example.com"],
        booking_code=make_booking_code(),
        idempotency_id="abc123def456gh",
    )


def make_pending_op(status: OpStatus = OpStatus.PENDING) -> dict[str, Any]:
    base: dict[str, Any] = dict(
        id="op-uuid-001",
        op_type=OpType.CALENDAR_HOLD,
        status=status,
        payload_json={"key": "val"},
        idempotency_key="idem-key-001",
        created_at=NOW,
        retry_count=0,
        last_error="",
        external_ids={},
        reject_reason=None,
        reject_reason_text="",
        request_id="req-001",
    )
    if status == OpStatus.APPROVED:
        base["approved_at"] = NOW
    if status == OpStatus.EXECUTED:
        base["approved_at"] = NOW
        base["executed_at"] = LATER
    if status == OpStatus.REJECTED:
        base["reject_reason"] = RejectReason.DUPLICATE
    if status == OpStatus.FAILED:
        base["last_error"] = "Connection timeout"
    return base


def make_eval_result() -> EvalResult:
    return EvalResult(
        case_id="case-001",
        kind=EvalKind.RAG,
        verdict=EvalVerdict.PASS,
        scores=[
            JudgeScore(
                dimension="faithfulness",
                score=4.5,
                reasoning="All claims traced to sources",
                judge_model="llama3-70b",
            )
        ],
        deterministic_checks={"six_bullets": True},
        raw_output="The exit load is 1% for redemption within 1 year. [source:axis_elss]",
        ran_at=NOW,
        latency_ms=1200,
        request_id="req-001",
    )


def make_calibration() -> JudgeCalibration:
    return JudgeCalibration(
        iteration=1,
        sample_size=10,
        exact_match_agreement=0.7,
        within_1_agreement=0.9,
        threshold_met=True,
        mismatches=[],
        calibrated_at=NOW,
    )


# ===========================================================================
# base.py
# ===========================================================================

class TestOpsSuiteBaseModel:
    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            RAGQuery(query="hi", request_id="r1", top_k=5, rerank_k=3, unknown_field="x")

    def test_str_strip_whitespace(self) -> None:
        q = RAGQuery(query="  hello  ", request_id="  r1  ", top_k=5, rerank_k=3)
        assert q.query == "hello"
        assert q.request_id == "r1"

    def test_validate_assignment_active(self) -> None:
        q = RAGQuery(query="hello", request_id="r1", top_k=5, rerank_k=3)
        with pytest.raises(ValidationError):
            q.top_k = 0  # ge=1 violated


class TestUtcDateTime:
    def test_naive_datetime_rejected(self) -> None:
        naive = dt.datetime(2026, 4, 20, 12, 0, 0)  # no tzinfo
        with pytest.raises(ValidationError, match="timezone-aware"):
            Pulse(**{**make_pulse(), "week_start": naive})

    def test_non_utc_datetime_rejected(self) -> None:
        tz_plus5 = dt.timezone(dt.timedelta(hours=5))
        non_utc = dt.datetime(2026, 4, 20, 12, 0, 0, tzinfo=tz_plus5)
        with pytest.raises(ValidationError, match="UTC"):
            Pulse(**{**make_pulse(), "week_start": non_utc})

    def test_utcnow_is_aware(self) -> None:
        result = utcnow()
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


# ===========================================================================
# rag.py
# ===========================================================================

class TestRAGQuery:
    def test_positive_round_trip(self) -> None:
        q = RAGQuery(query="What is exit load?", request_id="req-1", top_k=10, rerank_k=5)
        data = q.model_dump()
        q2 = RAGQuery(**data)
        assert q == q2

    def test_rerank_gt_topk_fails(self) -> None:
        with pytest.raises(ValidationError, match="rerank_k"):
            RAGQuery(query="x", request_id="r1", top_k=5, rerank_k=10)

    def test_topk_out_of_range_fails(self) -> None:
        with pytest.raises(ValidationError):
            RAGQuery(query="x", request_id="r1", top_k=0, rerank_k=1)

    def test_empty_query_fails(self) -> None:
        with pytest.raises(ValidationError):
            RAGQuery(query="", request_id="r1")


class TestCitation:
    def test_positive_round_trip(self) -> None:
        c = make_citation()
        c2 = Citation(**c.model_dump())
        assert c == c2

    def test_invalid_doc_id_fails(self) -> None:
        with pytest.raises(ValidationError):
            Citation(doc_id="ab", chunk_index=0, score=0.5, doc_type=DocType.FEE, section="fees")

    def test_score_out_of_range_fails(self) -> None:
        with pytest.raises(ValidationError):
            Citation(doc_id="abc", chunk_index=0, score=1.5, doc_type=DocType.FEE, section="fees")


class TestBullet:
    def test_positive_round_trip(self) -> None:
        b = make_bullet()
        b2 = Bullet(**b.model_dump())
        assert b == b2

    def test_no_source_tag_fails(self) -> None:
        with pytest.raises(ValidationError, match="source"):
            Bullet(text="The fund has a low exit load of 1 percent.", sources=[make_citation()])

    def test_empty_sources_fails(self) -> None:
        with pytest.raises(ValidationError):
            Bullet(text="Text [source:axis_elss]", sources=[])


class TestRAGAnswer:
    def test_positive_round_trip(self) -> None:
        a = RAGAnswer(**make_rag_answer())
        a2 = RAGAnswer(**a.model_dump())
        assert a == a2

    def test_five_bullets_fails(self) -> None:
        with pytest.raises(ValidationError):
            RAGAnswer(**make_rag_answer(n_bullets=5))

    def test_seven_bullets_fails(self) -> None:
        with pytest.raises(ValidationError):
            RAGAnswer(**make_rag_answer(n_bullets=7))

    def test_bullet_citing_missing_doc_fails(self) -> None:
        data = make_rag_answer()
        # bullet cites "sbi_bluechip" but retrieved_chunks only has "axis_elss"
        data["bullets"] = [make_bullet("axis_elss")] * 5 + [make_bullet("sbi_bluechip")]
        with pytest.raises(ValidationError, match="sbi_bluechip"):
            RAGAnswer(**data)


# ===========================================================================
# pulse.py
# ===========================================================================

class TestTrendDelta:
    def test_positive_round_trip(self) -> None:
        td = make_trend_delta()
        td2 = TrendDelta(**td.model_dump())
        assert td == td2

    def test_wrong_abs_delta_fails(self) -> None:
        with pytest.raises(ValidationError, match="abs_delta"):
            TrendDelta(
                theme=ThemeCategory.LOGIN,
                this_week_count=10,
                prev_week_count=5,
                abs_delta=99,  # wrong
                pct_delta=100.0,
                p_value=0.05,
                direction=TrendDirection.UP,
                is_significant=True,
            )

    def test_wrong_direction_fails(self) -> None:
        with pytest.raises(ValidationError, match="direction"):
            TrendDelta(
                theme=ThemeCategory.LOGIN,
                this_week_count=10,
                prev_week_count=5,
                abs_delta=5,
                pct_delta=100.0,
                p_value=0.05,
                direction=TrendDirection.DOWN,  # wrong — should be UP
                is_significant=True,
            )


class TestTheme:
    def test_positive_round_trip(self) -> None:
        t = make_theme()
        t2 = Theme(**t.model_dump())
        assert t == t2

    def test_zero_count_fails(self) -> None:
        data = make_theme().model_dump()
        data["count"] = 0
        with pytest.raises(ValidationError):
            Theme(**data)


class TestActionIdea:
    def test_positive_round_trip(self) -> None:
        a = make_action()
        a2 = ActionIdea(**a.model_dump())
        assert a == a2

    def test_invalid_effort_fails(self) -> None:
        with pytest.raises(ValidationError):
            ActionIdea(
                headline="Fix the login flow now",
                rationale="Login failures are driving churn among new users.",
                linked_themes=[ThemeCategory.LOGIN],
                effort="extreme",  # type: ignore[arg-type]
            )


class TestPulse:
    def test_positive_round_trip(self) -> None:
        p = Pulse(**make_pulse())
        p2 = Pulse(**p.model_dump())
        assert p == p2

    def test_summary_over_250_words_fails(self) -> None:
        long_summary = " ".join(["word"] * 251)
        with pytest.raises(ValidationError, match="250"):
            Pulse(**{**make_pulse(), "summary": long_summary})

    def test_two_actions_fails(self) -> None:
        with pytest.raises(ValidationError):
            Pulse(**make_pulse(n_actions=2))

    def test_four_actions_fails(self) -> None:
        with pytest.raises(ValidationError):
            Pulse(**make_pulse(n_actions=4))

    def test_week_end_before_start_fails(self) -> None:
        data = make_pulse()
        data["week_end"] = dt.datetime(2026, 4, 13, 0, 0, 0, tzinfo=UTC)  # before week_start
        with pytest.raises(ValidationError, match="week_end"):
            Pulse(**data)

    def test_range_over_14_days_fails(self) -> None:
        data = make_pulse()
        data["week_end"] = dt.datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)  # 17 days after
        with pytest.raises(ValidationError, match="14 days"):
            Pulse(**data)


# ===========================================================================
# booking.py
# ===========================================================================

class TestBookingCode:
    def test_parse_factory(self) -> None:
        bc = BookingCode.parse("IND-NOM-20260420-001")
        assert bc.theme_code == "NOM"
        assert bc.date == "20260420"
        assert bc.sequence == 1

    def test_positive_round_trip(self) -> None:
        bc = make_booking_code()
        bc2 = BookingCode(**bc.model_dump())
        assert bc == bc2

    def test_malformed_raw_fails(self) -> None:
        with pytest.raises(ValidationError):
            BookingCode(raw="IND-NOM-2026-001", theme_code="NOM", date="2026", sequence=1)

    def test_mismatched_components_fails(self) -> None:
        with pytest.raises(ValidationError, match="disagrees"):
            BookingCode(
                raw="IND-NOM-20260420-001",
                theme_code="EXIT",  # wrong
                date="20260420",
                sequence=1,
            )

    def test_parse_invalid_raw_fails(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            BookingCode.parse("INVALID-CODE")


class TestTurnContext:
    def test_positive_round_trip(self) -> None:
        tc = TurnContext(
            session_id="sess-1",
            state=VoiceState.GREETING,
            top_theme=ThemeCategory.NOMINEE,
            request_id="req-1",
            updated_at=NOW,
        )
        tc2 = TurnContext(**tc.model_dump())
        assert tc == tc2

    def test_negative_turn_count_fails(self) -> None:
        with pytest.raises(ValidationError):
            TurnContext(
                session_id="sess-1",
                state=VoiceState.GREETING,
                top_theme=ThemeCategory.NOMINEE,
                request_id="req-1",
                turn_count=-1,
                updated_at=NOW,
            )


class TestBooking:
    def test_positive_round_trip(self) -> None:
        b = make_booking()
        b2 = Booking(**b.model_dump())
        assert b == b2

    def test_empty_captured_intent_fails(self) -> None:
        data = make_booking().model_dump()
        data["captured_intent"] = ""
        with pytest.raises(ValidationError):
            Booking(**data)


class TestVoiceCallContext:
    def test_positive_round_trip(self) -> None:
        vcc = VoiceCallContext(
            booking=make_booking(),
            pulse_snapshot_id="snap-001",
            transcript=[{"role": "agent", "text": "Hello"}, {"role": "user", "text": "Hi"}],
        )
        vcc2 = VoiceCallContext(**vcc.model_dump())
        assert vcc == vcc2

    def test_empty_transcript_allowed(self) -> None:
        # transcript: list[dict] with no min constraint — empty list is valid
        vcc = VoiceCallContext(
            booking=make_booking(),
            pulse_snapshot_id="snap-001",
            transcript=[],
        )
        assert vcc.transcript == []


# ===========================================================================
# hitl.py
# ===========================================================================

class TestAdvisorBriefingCard:
    def test_positive_round_trip(self) -> None:
        card = make_advisor_card()
        card2 = AdvisorBriefingCard(**card.model_dump())
        assert card == card2

    def test_too_few_top_themes_fails(self) -> None:
        with pytest.raises(ValidationError):
            AdvisorBriefingCard(
                top_themes=[make_theme(), make_theme()],  # need exactly 3
                sentiment_shift="declining",
                pain_points=["p1", "p2"],
                talking_points=["t1", "t2", "t3"],
                booking_code=make_booking_code(),
            )


class TestCalendarHold:
    def test_positive_round_trip(self) -> None:
        ch = make_calendar_hold()
        ch2 = CalendarHold(**ch.model_dump())
        assert ch == ch2

    def test_end_before_start_fails(self) -> None:
        data = make_calendar_hold().model_dump()
        data["end_utc"] = NOW  # same as start_utc
        with pytest.raises(ValidationError, match="end_utc"):
            CalendarHold(**data)

    def test_invalid_email_in_attendees_fails(self) -> None:
        with pytest.raises(ValidationError, match="email"):
            CalendarHold(
                summary="Hold",
                description="Meeting [IND-NOM-20260420-001]",
                start_utc=NOW,
                end_utc=LATER,
                attendees=["not-an-email"],
                booking_code=make_booking_code(),
                idempotency_id="abc123def456gh",
            )

    def test_duration_too_short_fails(self) -> None:
        start = dt.datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
        end = dt.datetime(2026, 4, 20, 12, 10, 0, tzinfo=UTC)  # 10 min
        with pytest.raises(ValidationError, match="15 minutes"):
            CalendarHold(
                summary="Hold",
                description="Meeting",
                start_utc=start,
                end_utc=end,
                attendees=["a@b.com"],
                booking_code=make_booking_code(),
                idempotency_id="abc123def456gh",
            )

    def test_duration_too_long_fails(self) -> None:
        start = dt.datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
        end = dt.datetime(2026, 4, 20, 14, 30, 0, tzinfo=UTC)  # 150 min
        with pytest.raises(ValidationError, match="120 minutes"):
            CalendarHold(
                summary="Hold",
                description="Meeting",
                start_utc=start,
                end_utc=end,
                attendees=["a@b.com"],
                booking_code=make_booking_code(),
                idempotency_id="abc123def456gh",
            )


class TestEmailDraft:
    def _make(self) -> EmailDraft:
        return EmailDraft(
            to=["advisor@indmoney.com"],
            subject="Callback scheduled [IND-NOM-20260420-001]",
            body_html="<p>Your callback is confirmed.</p>",
            body_plain="Your callback is confirmed.",
            briefing_card=make_advisor_card(),
            booking_code=make_booking_code(),
        )

    def test_positive_round_trip(self) -> None:
        ed = self._make()
        ed2 = EmailDraft(**ed.model_dump())
        assert ed == ed2

    def test_subject_without_booking_code_marker_fails(self) -> None:
        with pytest.raises(ValidationError, match="subject"):
            EmailDraft(
                to=["advisor@indmoney.com"],
                subject="Callback scheduled",  # no booking code marker
                body_html="<p>Done</p>",
                body_plain="Done",
                briefing_card=make_advisor_card(),
                booking_code=make_booking_code(),
            )

    def test_invalid_to_email_fails(self) -> None:
        with pytest.raises(ValidationError, match="email"):
            EmailDraft(
                to=["not-an-email"],
                subject="Subject [IND-NOM-20260420-001]",
                body_html="<p>Done</p>",
                body_plain="Done",
                briefing_card=make_advisor_card(),
                booking_code=make_booking_code(),
            )


class TestPendingOp:
    @pytest.mark.parametrize("status", [
        OpStatus.PENDING,
        OpStatus.APPROVED,
        OpStatus.EXECUTED,
        OpStatus.FAILED,
        OpStatus.REJECTED,
    ])
    def test_positive_each_valid_status(self, status: OpStatus) -> None:
        op = PendingOp(**make_pending_op(status))
        assert op.status == status

    def test_rejected_without_reason_fails(self) -> None:
        data = make_pending_op(OpStatus.REJECTED)
        data["reject_reason"] = None
        with pytest.raises(ValidationError, match="reject_reason"):
            PendingOp(**data)

    def test_executed_without_executed_at_fails(self) -> None:
        data = make_pending_op(OpStatus.EXECUTED)
        data["executed_at"] = None
        with pytest.raises(ValidationError, match="executed_at"):
            PendingOp(**data)

    def test_approved_without_approved_at_fails(self) -> None:
        data = make_pending_op(OpStatus.APPROVED)
        data["approved_at"] = None
        with pytest.raises(ValidationError, match="approved_at"):
            PendingOp(**data)

    def test_failed_without_error_fails(self) -> None:
        data = make_pending_op(OpStatus.FAILED)
        data["last_error"] = ""
        with pytest.raises(ValidationError, match="last_error"):
            PendingOp(**data)


class TestApprovalDecision:
    def test_positive_approve(self) -> None:
        ad = ApprovalDecision(
            op_id="op-001",
            decision="approve",
            decided_by="advisor-1",
            decided_at=NOW,
        )
        ad2 = ApprovalDecision(**ad.model_dump())
        assert ad == ad2

    def test_positive_reject_with_reason(self) -> None:
        ad = ApprovalDecision(
            op_id="op-001",
            decision="reject",
            reject_reason=RejectReason.DUPLICATE,
            decided_by="advisor-1",
            decided_at=NOW,
        )
        assert ad.reject_reason == RejectReason.DUPLICATE

    def test_reject_without_reason_fails(self) -> None:
        with pytest.raises(ValidationError, match="reject_reason"):
            ApprovalDecision(
                op_id="op-001",
                decision="reject",
                decided_by="advisor-1",
                decided_at=NOW,
            )


# ===========================================================================
# eval.py
# ===========================================================================

class TestEvalCase:
    def test_positive_round_trip(self) -> None:
        ec = EvalCase(
            id="case-001",
            kind=EvalKind.RAG,
            prompt="What is the exit load for Axis ELSS?",
            expected_refusal=False,
            expected_sources=["axis_elss"],
            expected_answer_covers=["1% within 1 year"],
            category="exit_load",
        )
        ec2 = EvalCase(**ec.model_dump())
        assert ec == ec2

    def test_empty_id_fails(self) -> None:
        with pytest.raises(ValidationError):
            EvalCase(id="", kind=EvalKind.RAG, prompt="Test prompt")


class TestJudgeScore:
    def test_positive_round_trip(self) -> None:
        js = JudgeScore(
            dimension="faithfulness",
            score=4.0,
            reasoning="All claims verified",
            judge_model="llama3-70b",
        )
        js2 = JudgeScore(**js.model_dump())
        assert js == js2

    def test_score_out_of_range_fails(self) -> None:
        with pytest.raises(ValidationError):
            JudgeScore(dimension="faithfulness", score=6.0, reasoning="x", judge_model="m")

    def test_invalid_dimension_fails(self) -> None:
        with pytest.raises(ValidationError):
            JudgeScore(dimension="accuracy", score=3.0, reasoning="x", judge_model="m")  # type: ignore[arg-type]


class TestEvalResult:
    def test_positive_round_trip(self) -> None:
        er = make_eval_result()
        er2 = EvalResult(**er.model_dump())
        assert er == er2

    def test_negative_latency_fails(self) -> None:
        data = make_eval_result().model_dump()
        data["latency_ms"] = -1
        with pytest.raises(ValidationError):
            EvalResult(**data)


class TestJudgeCalibration:
    def test_positive_round_trip(self) -> None:
        jc = make_calibration()
        jc2 = JudgeCalibration(**jc.model_dump())
        assert jc == jc2

    def test_iteration_out_of_range_fails(self) -> None:
        with pytest.raises(ValidationError):
            JudgeCalibration(
                iteration=11,  # max 10
                sample_size=10,
                exact_match_agreement=0.7,
                within_1_agreement=0.9,
                threshold_met=True,
                calibrated_at=NOW,
            )

    def test_sample_size_too_small_fails(self) -> None:
        with pytest.raises(ValidationError):
            JudgeCalibration(
                iteration=1,
                sample_size=4,  # min 5
                exact_match_agreement=0.7,
                within_1_agreement=0.9,
                threshold_met=True,
                calibrated_at=NOW,
            )


class TestEvalReport:
    def test_positive_round_trip(self) -> None:
        er = EvalReport(
            run_id="run-001",
            started_at=NOW,
            completed_at=LATER,
            results=[make_eval_result()],
            calibration=make_calibration(),
            overall_pass=True,
            summary_stats={"rag_faithfulness_avg": 4.2},
        )
        er2 = EvalReport(**er.model_dump())
        assert er == er2

    def test_empty_results_fails(self) -> None:
        with pytest.raises(ValidationError):
            EvalReport(
                run_id="run-001",
                started_at=NOW,
                completed_at=LATER,
                results=[],
                calibration=make_calibration(),
                overall_pass=True,
                summary_stats={},
            )
