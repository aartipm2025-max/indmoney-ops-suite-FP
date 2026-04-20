class OpsSuiteError(Exception):
    """Base exception for all INDmoney Ops Suite errors."""


class ConfigError(OpsSuiteError):
    """Raised when configuration is invalid or missing."""


class LLMError(OpsSuiteError):
    """Raised for general LLM call failures."""


class LLMRefusalError(LLMError):
    """Raised when the LLM refuses to answer due to safety or policy."""


class LLMCircuitBreakerError(LLMError):
    """Raised when the circuit breaker is open after repeated LLM failures."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM call exceeds the allowed timeout."""


class RetrievalError(OpsSuiteError):
    """Raised when retrieval from vector or BM25 index fails."""


class CitationError(OpsSuiteError):
    """Raised when citation extraction or verification fails."""


class SchemaValidationError(OpsSuiteError):
    """Raised when a Pydantic schema validation fails unexpectedly."""


class PulseGenerationError(OpsSuiteError):
    """Raised when weekly pulse generation fails."""


class TrendDetectionError(OpsSuiteError):
    """Raised when review trend detection fails."""


class VoiceAgentError(OpsSuiteError):
    """Raised when the voice agent pipeline encounters an error."""


class BookingError(OpsSuiteError):
    """Raised when calendar booking fails."""


class HITLApprovalError(OpsSuiteError):
    """Raised when the HITL approval flow encounters an error."""


class GoogleAPIError(OpsSuiteError):
    """Raised when a Google API call (Calendar, Gmail, Drive) fails."""


class OAuthError(OpsSuiteError):
    """Raised when OAuth authentication or token refresh fails."""


class EvalError(OpsSuiteError):
    """Raised when the eval harness encounters an error."""


class JudgeCalibrationError(EvalError):
    """Raised when judge calibration fails to meet the agreement threshold."""


class SafetyViolationError(OpsSuiteError):
    """Raised when a request violates safety guardrails."""


class PIIDetectedError(SafetyViolationError):
    """Raised when PII is detected in input or output."""
