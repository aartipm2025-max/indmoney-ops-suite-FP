import sys
from pathlib import Path

from loguru import logger

from core.request_context import get_request_id

_LOGS_DIR = Path(__file__).parent.parent / "logs"
_LOGS_DIR.mkdir(exist_ok=True)

_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
    "<yellow>req={extra[request_id]}</yellow> | "
    "{message}"
)


def _request_id_patcher(record: dict) -> None:
    rid = get_request_id()
    record["extra"].setdefault("request_id", rid if rid is not None else "none")


logger.remove()

logger.configure(patcher=_request_id_patcher)

logger.add(
    sys.stderr,
    format=_LOG_FORMAT,
    colorize=True,
    level="INFO",
    enqueue=True,
)

logger.add(
    _LOGS_DIR / "app.log",
    format=_LOG_FORMAT,
    level="DEBUG",
    rotation="5 MB",
    retention=5,
    enqueue=True,
    diagnose=False,
    backtrace=False,
    colorize=False,
)

logger.add(
    _LOGS_DIR / "app.jsonl",
    level="INFO",
    rotation="5 MB",
    retention=5,
    enqueue=True,
    serialize=True,
    diagnose=False,
    backtrace=False,
)

log = logger


def log_with_request(request_id: str):
    """Return a loguru logger bound with an explicit request_id."""
    return logger.bind(request_id=request_id)
