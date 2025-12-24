"""No-op logger implementation for fallback logging.

This class implements the LoggerPort protocol but performs no actions.
It is used as a safe fallback when no logger is explicitly provided to components.
"""

from __future__ import annotations

from typing import Any, Self

from bioetl.domain.ports import LoggerPort


class NoOpLogger(LoggerPort):
    """No-op implementation of LoggerPort."""

    def bind(self, **kwargs: Any) -> Self:
        """Bind returns self as no context is stored."""
        return self

    def info(self, msg: str, **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def error(self, msg: str, **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def exception(self, msg: str, **kwargs: Any) -> None:
        """Do nothing."""
        pass
