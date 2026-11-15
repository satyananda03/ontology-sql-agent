import inspect
import logging
import re
import time
import warnings
from collections.abc import Callable
from functools import wraps
from typing import Any


# Halaman Settings di UI mem-polling status ingest dan kompilasi tiap 5 detik.
_STATUS_POLL = re.compile(r"GET \S*/status .*\b200\b")


def _not_status_poll(record: logging.LogRecord) -> bool:
    """Buang log polling status yang sukses; yang gagal tetap tampil."""
    return not _STATUS_POLL.search(record.getMessage())


def setup_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )
    for name in ("uvicorn.access", "httpx"):
        logging.getLogger(name).addFilter(_not_status_poll)
    # "N changes detected" dari reloader di mode --reload.
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    warnings.filterwarnings(
        "ignore",
        message=r"Pydantic serializer warnings",
        category=UserWarning,
        module=r"pydantic\.main",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


logger = get_logger(__name__)


def timed(name: str, step: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Log how long *step* takes, so latency can be attributed per step."""
    if inspect.iscoroutinefunction(step):

        @wraps(step)
        async def arun(state: Any) -> Any:
            started = time.perf_counter()
            try:
                return await step(state)
            finally:
                logger.info(f"[TIMING] {name} {time.perf_counter() - started:.2f}s")

        return arun

    @wraps(step)
    def run(state: Any) -> Any:
        started = time.perf_counter()
        try:
            return step(state)
        finally:
            logger.info(f"[TIMING] {name} {time.perf_counter() - started:.2f}s")

    return run
