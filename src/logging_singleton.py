"""A simple singleton pattern for application loggers.

Provides `get_logger(name)` which returns a configured logger instance and
`configure_logging(level)` to update the default logger level at runtime.

This keeps logger configuration centralized and avoids duplicate handlers on
re-imports.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

_loggers: Dict[str, logging.Logger] = {}


def _env_log_level() -> int:
    lvl = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, lvl, logging.INFO)


def get_logger(name: str = "int20h") -> logging.Logger:
    """Return a singleton Logger for the given name.

    The logger is configured only once and subsequent calls return the same
    instance. Configuration reads LOG_LEVEL from env if present.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    # Use the application's logging handlers/formatters (e.g., uvicorn's defaults).
    # Only set the logger level here and avoid adding handlers or custom formatters
    # so the ASGI server can control formatting and destinations.
    level = _env_log_level()
    logger.setLevel(level)
    # Keep propagate=True (default) so the application's configured handlers are used.

    _loggers[name] = logger
    return logger


def configure_logging(level: Optional[str] = None) -> None:
    """Reconfigure all known loggers to a new level.

    level may be a string (e.g. "DEBUG") or None to use env var / default.
    """
    lvl = (
        _env_log_level()
        if level is None
        else getattr(logging, level.upper(), logging.INFO)
    )
    for lg in _loggers.values():
        lg.setLevel(lvl)
        for h in lg.handlers:
            h.setLevel(lvl)


__all__ = ["get_logger", "configure_logging"]
