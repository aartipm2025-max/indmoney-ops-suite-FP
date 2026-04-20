import threading
from datetime import datetime
from pathlib import Path
from typing import Literal

from core.request_context import get_request_id

_LOGS_DIR = Path(__file__).parent.parent / "logs"
_LOGS_DIR.mkdir(exist_ok=True)
_ERROR_LOG = _LOGS_DIR / "system_errors.log"

_MAX_SIZE_BYTES = 5 * 1024 * 1024
_MAX_ROTATIONS = 5
_SEPARATOR = "─" * 61
_lock = threading.Lock()


def _rotate_if_needed() -> None:
    if not _ERROR_LOG.exists() or _ERROR_LOG.stat().st_size < _MAX_SIZE_BYTES:
        return
    for i in range(_MAX_ROTATIONS - 1, 0, -1):
        src = _ERROR_LOG.parent / f"{_ERROR_LOG.name}.{i}"
        dst = _ERROR_LOG.parent / f"{_ERROR_LOG.name}.{i + 1}"
        if src.exists():
            src.rename(dst)
    _ERROR_LOG.rename(_ERROR_LOG.parent / f"{_ERROR_LOG.name}.1")


def _indent(value: str) -> str:
    """Indent continuation lines for multi-line values."""
    lines = str(value).splitlines()
    if len(lines) <= 1:
        return value
    return lines[0] + "\n" + "\n".join("  " + ln for ln in lines[1:])


def log_structured_error(
    phase: str,
    module: str,
    error_type: Literal["Validation", "Runtime", "Integration", "Safety"],
    description: str,
    input_val: str,
    expected: str,
    actual: str,
    fix: str,
    status: Literal["Resolved", "Pending", "Documented"] = "Pending",
    request_id: str | None = None,
) -> None:
    rid = request_id if request_id is not None else (get_request_id() or "none")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = (
        f"{_SEPARATOR}\n"
        f"[TIMESTAMP]    {timestamp}\n"
        f"[REQUEST_ID]   {rid}\n"
        f"[PHASE]        {_indent(phase)}\n"
        f"[MODULE]       {_indent(module)}\n"
        f"[ERROR_TYPE]   {_indent(error_type)}\n"
        f"[DESCRIPTION]  {_indent(description)}\n"
        f"[INPUT]        {_indent(input_val)}\n"
        f"[EXPECTED]     {_indent(expected)}\n"
        f"[ACTUAL]       {_indent(actual)}\n"
        f"[FIX]          {_indent(fix)}\n"
        f"[STATUS]       {status}\n"
        f"{_SEPARATOR}\n"
    )

    with _lock:
        _rotate_if_needed()
        with _ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(entry)


def log_from_exception(
    phase: str,
    module: str,
    exc: BaseException,
    input_val: str = "",
    fix: str = "Under investigation",
    status: Literal["Resolved", "Pending", "Documented"] = "Pending",
    request_id: str | None = None,
) -> None:
    error_type: Literal["Validation", "Runtime", "Integration", "Safety"] = "Runtime"
    log_structured_error(
        phase=phase,
        module=module,
        error_type=error_type,
        description=type(exc).__name__,
        input_val=input_val,
        expected="No exception",
        actual=str(exc),
        fix=fix,
        status=status,
        request_id=request_id,
    )
