"""
Logging contracts for the application.

Defines ABCs for logging, progress reporting, and tracing.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterator, Self


class LoggerAdapterABC(ABC):
    """
    Интерфейс структурированного логгера.

    Default factory: ``bioetl.infrastructure.logging.factories.default_logger``.
    Implementations: ``UnifiedLoggerImpl``.
    """

    @abstractmethod
    def info(self, msg: str, **ctx: Any) -> None:
        """Log info message."""

    @abstractmethod
    def error(self, msg: str, **ctx: Any) -> None:
        """Log error message."""

    @abstractmethod
    def debug(self, msg: str, **ctx: Any) -> None:
        """Log debug message."""

    @abstractmethod
    def warning(self, msg: str, **ctx: Any) -> None:
        """Log warning message."""

    @abstractmethod
    def bind(self, **ctx: Any) -> Self:
        """Возвращает логгер с привязанным контекстом."""


class ProgressReporterABC(ABC):
    """
    Интерфейс отчетности о прогрессе.

    Default factory:
    ``bioetl.infrastructure.logging.factories.default_progress_reporter``.
    Implementations: ``TqdmProgressReporterImpl``.
    """

    @abstractmethod
    def start(self, total: int, description: str = "") -> None:
        """Начинает отслеживание прогресса."""

    @abstractmethod
    def update(self, n: int = 1) -> None:
        """Обновляет прогресс на n единиц."""

    @abstractmethod
    def finish(self) -> None:
        """Завершает отслеживание."""

    @contextmanager
    def create_bar(self, total: int, desc: str = "") -> Iterator[Any]:
        """
        Context manager for progress bar.
        Default implementation delegates to start/finish.
        """
        self.start(total, description=desc)
        try:
            yield self
        finally:
            self.finish()


class TracerABC(ABC):
    """
    Интерфейс распределенной трассировки.

    Implementations expected to be provided by infrastructure tracing backends.
    """

    @abstractmethod
    def start_span(self, name: str) -> Any:
        """Начинает спан."""

    @abstractmethod
    def end_span(self, span: Any) -> None:
        """Завершает спан."""

    @abstractmethod
    def inject_context(self, headers: dict[str, str]) -> None:
        """Внедряет контекст трассировки в заголовки."""


__all__ = [
    "LoggerAdapterABC",
    "ProgressReporterABC",
    "TracerABC",
]
