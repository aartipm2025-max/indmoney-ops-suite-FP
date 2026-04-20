import json
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOGS_DIR = ROOT / "logs"


# ---------------------------------------------------------------------------
# 1. Settings loads correctly
# ---------------------------------------------------------------------------
def test_settings_loads() -> None:
    from config import settings

    assert settings.app_name, "app_name must be non-empty"
    assert settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    assert settings.groq_model_primary, "groq_model_primary must be set"
    assert settings.groq_model_fast, "groq_model_fast must be set"


# ---------------------------------------------------------------------------
# 2. Required directories exist
# ---------------------------------------------------------------------------
def test_directories_exist() -> None:
    required = [
        ROOT / "core",
        ROOT / "schemas",
        ROOT / "pillars" / "pillar_a_knowledge",
        ROOT / "pillars" / "pillar_b_voice",
        ROOT / "pillars" / "pillar_c_hitl",
        ROOT / "evals",
        ROOT / "ui" / "tabs",
        ROOT / "scripts",
        ROOT / "data" / "factsheets",
        ROOT / "data" / "fees",
        ROOT / "data" / "reviews",
        ROOT / "data" / "manifests",
        ROOT / "logs",
        ROOT / ".secrets",
        ROOT / "docs",
        ROOT / "tests",
    ]
    for d in required:
        assert d.exists() and d.is_dir(), f"Missing directory: {d}"


# ---------------------------------------------------------------------------
# 3. Logger writes to app.log
# ---------------------------------------------------------------------------
def test_logger_writes_app_log() -> None:
    from core.logger import log

    marker = "test_logger_writes_app_log_MARKER"
    log.info(marker)
    time.sleep(0.3)  # allow loguru enqueue flush

    log_file = LOGS_DIR / "app.log"
    assert log_file.exists(), "logs/app.log does not exist"
    content = log_file.read_text(encoding="utf-8")
    assert marker in content, "Marker not found in app.log"


# ---------------------------------------------------------------------------
# 4. JSONL sink writes valid JSON lines
# ---------------------------------------------------------------------------
def test_jsonl_sink_writes() -> None:
    from core.logger import log

    marker = "test_jsonl_sink_writes_MARKER"
    log.info(marker)
    time.sleep(0.3)

    jsonl_file = LOGS_DIR / "app.jsonl"
    assert jsonl_file.exists(), "logs/app.jsonl does not exist"

    valid_lines = 0
    for line in jsonl_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            valid_lines += 1
        except json.JSONDecodeError:
            pass

    assert valid_lines >= 1, "No valid JSON lines found in app.jsonl"


# ---------------------------------------------------------------------------
# 5. Structured error writes correct 11-line format
# ---------------------------------------------------------------------------
def test_structured_error_writes() -> None:
    from core.error_logger import log_structured_error

    log_structured_error(
        phase="0 — Foundation",
        module="tests/test_p0_foundation.py",
        error_type="Validation",
        description="Test error entry",
        input_val="sample_input",
        expected="no error",
        actual="test error",
        fix="this is a test",
        status="Documented",
    )

    error_log = LOGS_DIR / "system_errors.log"
    assert error_log.exists(), "logs/system_errors.log does not exist"
    content = error_log.read_text(encoding="utf-8")

    required_labels = [
        "[TIMESTAMP]",
        "[REQUEST_ID]",
        "[PHASE]",
        "[MODULE]",
        "[ERROR_TYPE]",
        "[DESCRIPTION]",
        "[INPUT]",
        "[EXPECTED]",
        "[ACTUAL]",
        "[FIX]",
        "[STATUS]",
    ]
    for label in required_labels:
        assert label in content, f"Missing label {label} in system_errors.log"

    separator = "─" * 61
    assert separator in content, "Missing separator line in system_errors.log"


# ---------------------------------------------------------------------------
# 6. Exception hierarchy
# ---------------------------------------------------------------------------
def test_exception_hierarchy() -> None:
    from core.exceptions import (
        BookingError,
        CitationError,
        ConfigError,
        EvalError,
        GoogleAPIError,
        HITLApprovalError,
        JudgeCalibrationError,
        LLMCircuitBreakerError,
        LLMError,
        LLMRefusalError,
        LLMTimeoutError,
        OAuthError,
        OpsSuiteError,
        PIIDetectedError,
        PulseGenerationError,
        RetrievalError,
        SafetyViolationError,
        SchemaValidationError,
        TrendDetectionError,
        VoiceAgentError,
    )

    subclasses = [
        ConfigError,
        LLMError,
        LLMRefusalError,
        LLMCircuitBreakerError,
        LLMTimeoutError,
        RetrievalError,
        CitationError,
        SchemaValidationError,
        PulseGenerationError,
        TrendDetectionError,
        VoiceAgentError,
        BookingError,
        HITLApprovalError,
        GoogleAPIError,
        OAuthError,
        EvalError,
        JudgeCalibrationError,
        SafetyViolationError,
        PIIDetectedError,
    ]
    for cls in subclasses:
        assert issubclass(cls, OpsSuiteError), f"{cls.__name__} is not a subclass of OpsSuiteError"


# ---------------------------------------------------------------------------
# 7. Request context propagation into error log
# ---------------------------------------------------------------------------
def test_request_context_propagation() -> None:
    from core.error_logger import log_structured_error
    from core.request_context import request_scope

    test_rid = "abc123def456"
    with request_scope(test_rid):
        log_structured_error(
            phase="0 — Foundation",
            module="tests/test_p0_foundation.py",
            error_type="Runtime",
            description="Request context propagation test",
            input_val="none",
            expected="request_id propagated",
            actual="checking",
            fix="N/A — this is a test",
            status="Documented",
        )

    error_log = LOGS_DIR / "system_errors.log"
    content = error_log.read_text(encoding="utf-8")
    assert test_rid in content, (
        f"request_id '{test_rid}' not found in system_errors.log"
    )
