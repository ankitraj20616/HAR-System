"""Small JSON logging setup used by every backend process."""

import json
import logging
from datetime import UTC, datetime

VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service.strip()
        if not self.service:
            raise ValueError("service name cannot be empty")

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "service": getattr(record, "service", self.service),
            "event": getattr(record, "event", "log"),
            "message": record.getMessage(),
        }
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(service: str, level: str | None = None) -> logging.Logger:
    """Configure process logging and return the service logger.

    Repeated calls replace only handlers installed by this helper, avoiding
    duplicate lines during application reloads.
    """

    if not service.strip():
        raise ValueError("service name cannot be empty")
    normalized_level = (level or "INFO").strip().upper()
    if normalized_level not in VALID_LOG_LEVELS:
        raise ValueError(f"invalid log level: {level!r}")
    numeric_level = getattr(logging, normalized_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"invalid log level: {level!r}")

    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_har_handler", False):
            root.removeHandler(handler)
            handler.close()
    handler = logging.StreamHandler()
    handler._har_handler = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter(service.strip()))
    root.addHandler(handler)
    root.setLevel(numeric_level)
    logger = logging.getLogger(service.strip())
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name)
