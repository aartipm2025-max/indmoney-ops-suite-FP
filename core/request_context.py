import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def get_request_id() -> str | None:
    return _request_id_var.get()


@contextmanager
def request_scope(request_id: str | None = None) -> Generator[str, None, None]:
    rid = request_id or new_request_id()
    token = _request_id_var.set(rid)
    try:
        yield rid
    finally:
        _request_id_var.reset(token)


def bind_request_id() -> dict[str, str]:
    """Return a dict suitable for loguru .bind() with the current request_id."""
    rid = get_request_id()
    return {"request_id": rid if rid is not None else "none"}
