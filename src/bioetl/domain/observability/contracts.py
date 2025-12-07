"""Observability ports for the domain layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Self


class LoggingPortABC(ABC):
    """
    Port describing structured logging operations.

    Реализации предоставляются инфраструктурой и должны связываться через DI.
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
    def apply_bind(self, **ctx: Any) -> Self:
        """Return logger instance with bound context."""


class TracingPortABC(ABC):
    """
    Port describing distributed tracing operations.

    Инфраструктура должна предоставить адаптер трассировки и связать его через DI.
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


class PipelineMetricsPortABC(ABC):
    """Port for recording pipeline stage metrics."""

    @abstractmethod
    def update_stage_duration(
        self,
        *,
        pipeline: str,
        provider: str,
        entity: str,
        stage: str,
        outcome: str,
        duration_sec: float,
    ) -> None:
        """Record duration metric for a stage."""

    @abstractmethod
    def update_stage_total(
        self,
        *,
        pipeline: str,
        provider: str,
        entity: str,
        stage: str,
        outcome: str,
    ) -> None:
        """Increment counter for a stage outcome."""


__all__ = [
    "LoggingPortABC",
    "TracingPortABC",
    "PipelineMetricsPortABC",
]
