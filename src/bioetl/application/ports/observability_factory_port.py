"""Port for observability component factories.

This module defines abstract interfaces for creating observability
components (loggers, metrics collectors), allowing the application
layer to work with observability without infrastructure dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    MetricsPortABC,
)


class ObservabilityFactoryPortABC(ABC):
    """Abstract factory for observability components.

    This port abstracts the creation of logging and metrics components,
    providing a clean interface for dependency injection.

    Example:
        >>> class StructlogFactory(ObservabilityFactoryPortABC):
        ...     def create_logger(self) -> LoggingPortABC:
        ...         return StructlogAdapter()
        ...     def create_metrics(self) -> MetricsPortABC:
        ...         return PrometheusMetrics()
    """

    @abstractmethod
    def create_logger(self) -> LoggingPortABC:
        """Create structured logger instance.

        Returns:
            Configured LoggingPortABC implementation.
        """
        ...

    @abstractmethod
    def create_metrics(self) -> MetricsPortABC:
        """Create metrics collector instance.

        Returns:
            Configured MetricsPortABC implementation.
        """
        ...


__all__ = ["ObservabilityFactoryPortABC"]
