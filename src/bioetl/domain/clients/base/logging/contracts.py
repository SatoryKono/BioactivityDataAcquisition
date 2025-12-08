"""
Logging contracts for the application.

Defines ABCs for logging, progress reporting, and tracing.

DEPRECATED: This module is deprecated. Use bioetl.domain.observability.contracts
instead. This module provides backward compatibility aliases.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterator
import warnings

# Import the canonical contracts from observability
from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    TracingPortABC,
)

# Issue deprecation warning for the entire module
warnings.warn(
    "bioetl.domain.clients.base.logging.contracts is deprecated. "
    "Use bioetl.domain.observability.contracts instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Provide backward compatibility aliases
LoggerAdapterABC = LoggingPortABC
TracerABC = TracingPortABC


class ProgressReporterABC(ABC):
    """
    Интерфейс отчетности о прогрессе.

    Реализация выбирается инфраструктурой и связывается с контейнером.
    """

    @abstractmethod
    def start(self, total: int, description: str = "") -> None:
        """Начинает отслеживание прогресса."""

    @abstractmethod
    def apply_update(self, n: int = 1) -> None:
        """Обновляет прогресс на n единиц."""

    @abstractmethod
    def stop_reporting(self) -> None:
        """Завершает отслеживание."""

    @contextmanager
    def create_bar(self, total: int, desc: str = "") -> Iterator[Any]:
        """
        Context manager for progress bar.
        Default implementation delegates to start/stop.
        """
        self.start(total, description=desc)
        try:
            yield self
        finally:
            self.stop_reporting()


__all__ = [
    "LoggerAdapterABC",
    "ProgressReporterABC",
    "TracerABC",
]
