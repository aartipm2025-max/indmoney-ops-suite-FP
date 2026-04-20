import time
from typing import Literal

import groq
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from core.error_logger import log_from_exception
from core.exceptions import LLMCircuitBreakerError
from core.request_context import get_request_id


class LLMClient:
    _failure_count: int = 0
    _failure_window_start: float = 0.0
    _circuit_open_until: float = 0.0

    def __init__(self) -> None:
        from config import settings

        self._settings = settings
        self._client = groq.Groq(api_key=settings.groq_api_key)
        self._model_map: dict[str, str] = {
            "primary": settings.groq_model_primary,
            "fast": settings.groq_model_fast,
        }

    def _check_circuit(self) -> None:
        now = time.monotonic()
        if now < LLMClient._circuit_open_until:
            raise LLMCircuitBreakerError(
                f"Circuit open for {LLMClient._circuit_open_until - now:.1f}s more"
            )

    def _record_failure(self) -> None:
        now = time.monotonic()
        threshold = self._settings.llm_circuit_breaker_threshold
        window = self._settings.llm_circuit_breaker_window_s

        if now - LLMClient._failure_window_start > window:
            LLMClient._failure_count = 0
            LLMClient._failure_window_start = now

        LLMClient._failure_count += 1
        if LLMClient._failure_count >= threshold:
            LLMClient._circuit_open_until = now + 30.0
            LLMClient._failure_count = 0

    def _reset_failures(self) -> None:
        LLMClient._failure_count = 0
        LLMClient._circuit_open_until = 0.0

    def chat(
        self,
        messages: list[dict],
        model: Literal["primary", "fast"] = "primary",
        temperature: float = 0.2,
        max_tokens: int = 1024,
        response_format: dict | None = None,
        timeout: float = 30.0,
    ) -> str:
        self._check_circuit()

        model_name = self._model_map[model]
        preview = str(messages)[:80]

        @retry(
            stop=stop_after_attempt(self._settings.llm_max_retries),
            wait=wait_exponential_jitter(initial=2, max=10),
            retry=retry_if_exception_type(
                (groq.APIError, groq.APIConnectionError, groq.RateLimitError)
            ),
            reraise=True,
        )
        def _call() -> str:
            rid = get_request_id()
            extra_headers = {"X-Request-Id": rid} if rid else {}
            try:
                kwargs: dict = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout": timeout,
                    "extra_headers": extra_headers,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format

                response = self._client.chat.completions.create(**kwargs)
                self._reset_failures()
                return response.choices[0].message.content or ""
            except groq.AuthenticationError:
                raise
            except (groq.APIError, groq.APIConnectionError, groq.RateLimitError) as exc:
                self._record_failure()
                log_from_exception(
                    phase="0 — Foundation",
                    module="core/llm_client.py",
                    exc=exc,
                    input_val=f"model={model_name} preview={preview}",
                )
                raise

        return _call()
