"""Factory for creating observability components.

Provides abstract factory interface and default implementation for
observability-layer components: loggers and metrics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from bioetl.domain.observability import LoggingPortABC, MetricsPortABC


class ObservabilityFactoryABC(ABC):
    """Abstract factory for observability components."""

    @abstractmethod
    def create_logger(self) -> LoggingPortABC:
        """Create a logger instance."""

    @abstractmethod
    def create_metrics(self) -> MetricsPortABC:
        """Create a metrics instance."""


class DefaultObservabilityFactory(ObservabilityFactoryABC):
    """Default implementation of observability factory.

    Uses infrastructure factories to create structured logger and Prometheus metrics.
    """

    def __init__(self) -> None:
        """Initialize factory with lazy-loaded components."""
        self._logger: LoggingPortABC | None = None
        self._metrics: MetricsPortABC | None = None

    def create_logger(self) -> LoggingPortABC:
        """Create or return cached logger instance."""
        if self._logger is None:
            from bioetl.infrastructure.observability.factories import (
                create_logging_port,
            )

            self._logger = create_logging_port()
        return self._logger

    def create_metrics(self) -> MetricsPortABC:
        """Create or return cached metrics instance."""
        if self._metrics is None:
            from bioetl.infrastructure.observability.factories import (
                create_metrics_port,
            )

            self._metrics = create_metrics_port()
        return self._metrics


def create_observability_factory() -> ObservabilityFactoryABC:
    """Create the default observability factory.

    Returns:
        Default observability factory instance.
    """
    return DefaultObservabilityFactory()


__all__ = [
    "ObservabilityFactoryABC",
    "DefaultObservabilityFactory",
    "create_observability_factory",
]
