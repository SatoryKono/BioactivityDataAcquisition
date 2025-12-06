"""Observability ports for the domain layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Self


class LoggingPort(ABC):
    """
    Port describing structured logging operations.

    Default factory: ``bioetl.infrastructure.observability.factories.default_logging_port``.
    Implementations: ``StructuredLoggerImpl``.
    """

    @abstractmethod
    def info(self, msg: str, **ctx: Any) -> None:
        """Log info message with structured context."""

    @abstractmethod
    def error(self, msg: str, **ctx: Any) -> None:
        """Log error message with structured context."""

    @abstractmethod
    def debug(self, msg: str, **ctx: Any) -> None:
        """Log debug message with structured context."""

    @abstractmethod
    def warning(self, msg: str, **ctx: Any) -> None:
        """Log warning message with structured context."""

    @abstractmethod
    def bind(self, **ctx: Any) -> Self:
        """Return logger instance with bound context."""


class TracingPort(ABC):
    """
    Port describing distributed tracing operations.

    Default factory: ``bioetl.infrastructure.observability.factories.default_tracing_port``.
    Implementations: ``TracingAdapterImpl``.
    """

    @abstractmethod
    def start_span(self, name: str) -> Any:
        """Start a tracing span."""

    @abstractmethod
    def end_span(self, span: Any) -> None:
        """Finish a tracing span."""

    @abstractmethod
    def inject_context(self, headers: dict[str, str]) -> None:
        """Inject tracing context into headers."""


__all__ = [
    "LoggingPort",
    "TracingPort",
]
