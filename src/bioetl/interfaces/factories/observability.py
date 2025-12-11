from __future__ import annotations

from abc import ABC, abstractmethod

from bioetl.domain.observability import LoggingPortABC, MetricsPortABC


class ObservabilityFactoryABC(ABC):
    """Abstract factory for observability components."""

    @abstractmethod
    def create_logger(self) -> LoggingPortABC:
        """Create logging port instance."""

    @abstractmethod
    def create_metrics(self) -> MetricsPortABC:
        """Create metrics port instance."""


class DefaultObservabilityFactory(ObservabilityFactoryABC):
    """Default factory using infrastructure implementations."""

    def __init__(self) -> None:
        self._logger: LoggingPortABC | None = None
        self._metrics: MetricsPortABC | None = None

    def create_logger(self) -> LoggingPortABC:
        if self._logger is None:
            from bioetl.infrastructure.observability.factories import (
                create_logging_port,
            )

            self._logger = create_logging_port()
        return self._logger

    def create_metrics(self) -> MetricsPortABC:
        if self._metrics is None:
            from bioetl.infrastructure.observability.factories import (
                create_metrics_port,
            )

            self._metrics = create_metrics_port()
        return self._metrics


def create_observability_factory() -> ObservabilityFactoryABC:
    """Factory function for default observability factory."""
    return DefaultObservabilityFactory()


__all__ = [
    "ObservabilityFactoryABC",
    "DefaultObservabilityFactory",
    "create_observability_factory",
]
