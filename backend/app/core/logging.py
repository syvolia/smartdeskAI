"""Structured logging configuration built on structlog.

Development renders colored console output; production renders JSON so log
aggregators can parse fields reliably.
"""

import logging

import structlog
from structlog.stdlib import BoundLogger

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog and the standard library logging bridge."""

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    # Align noisy third-party loggers with our configured level.
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = "smartdesk") -> BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)