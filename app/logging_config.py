"""Logging configuration for the backend."""
import logging
import sys
from typing import Any

from app.config import settings


def setup_logging() -> None:
    """Configure application logging."""
    level = logging.DEBUG if settings.debug else logging.INFO
    format_str = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    # Reduce noise from third-party libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module/component."""
    return logging.getLogger(name)
