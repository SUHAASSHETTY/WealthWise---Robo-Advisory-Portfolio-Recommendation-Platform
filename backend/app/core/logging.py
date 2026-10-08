"""Structured JSON logging with request correlation IDs (NFR-06) and an allow-list of extra keys (NFR-03).

Only keys in ALLOWED_LOG_KEYS are emitted from `extra={...}`; anything else (names, emails, amounts, …)
is silently dropped, so a careless log call cannot leak PII or financial positions.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

ALLOWED_LOG_KEYS: frozenset[str] = frozenset(
    {
        "method",
        "path_template",
        "status_code",
        "duration_ms",
        "customer_id",
        "advisor_id",
        "user_id",
        "role",
        "entity_id",
        "entity_type",
        "action",
        "version_no",
        "count",
        "line_count",
        "outcome",
        "error_code",
    }
)
_HANDLER_NAME = "wealthwise-json"


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None) -> object:
    return _correlation_id.set(value)


def reset_correlation_id(token: object) -> None:
    _correlation_id.reset(token)  # type: ignore[arg-type]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        for key in sorted(ALLOWED_LOG_KEYS):
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        return json.dumps(payload, default=str)


class _CurrentStdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Writes to whatever sys.stdout is at emit time (survives stdout redirection, reloaders, test capture)."""

    @property
    def stream(self) -> object:
        return sys.stdout

    @stream.setter
    def stream(self, _value: object) -> None:
        pass


def configure_logging(level: str) -> None:
    """(Re)install a single JSON handler on the root logger bound to the current stdout."""
    root = logging.getLogger()
    for existing in [h for h in root.handlers if h.get_name() == _HANDLER_NAME]:
        root.removeHandler(existing)
    handler = _CurrentStdoutHandler()
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
