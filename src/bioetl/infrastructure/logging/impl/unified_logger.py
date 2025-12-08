"""Structlog-based unified logger implementation."""

from __future__ import annotations

from typing import Any, Self

import structlog
from structlog.stdlib import BoundLogger

from bioetl.interfaces.observability.contracts import LoggingPortABC


class UnifiedLoggerImpl(LoggingPortABC):
    """Реализация структурированного логгера на базе structlog."""

    def __init__(self, logger: BoundLogger | None = None) -> None:
        self._logger = logger or structlog.get_logger()

    def info(self, msg: str, **ctx: Any) -> None:
        """Log info message with structured context."""
        self._logger.info(msg, **ctx)

    def error(self, msg: str, **ctx: Any) -> None:
        """Log error message with structured context."""
        self._logger.error(msg, **ctx)

    def debug(self, msg: str, **ctx: Any) -> None:
        """Log debug message with structured context."""
        self._logger.debug(msg, **ctx)

    def warning(self, msg: str, **ctx: Any) -> None:
        """Log warning message with structured context."""
        self._logger.warning(msg, **ctx)

    def apply_bind(self, **ctx: Any) -> Self:
        """Return a logger bound with additional context."""
        return self.__class__(self._logger.bind(**ctx))


__all__ = ["UnifiedLoggerImpl"]
