"""Unified observability service for application layer.

This module provides a centralized service for managing observability
concerns including logging and metrics. It abstracts the creation and
lifecycle of observability components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.application.ports.observability_factory_port import (
        ObservabilityFactoryPortABC,
    )
    from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC


@dataclass
class ObservabilityContext:
    """Concrete observability context implementation.

    Provides scoped access to logging and metrics with automatic
    context binding for structured logging.

    Attributes:
        _logger: Underlying logger instance.
        _metrics: Underlying metrics instance.
        _bound_context: Context values to bind to log messages.

    Example:
        >>> context = observability_service.create_context(
        ...     pipeline_id="chembl.activity",
        ...     run_id="run-123",
        ... )
        >>> context.logger.info("Processing started")
        # Logs: {"pipeline_id": "chembl.activity", "run_id": "run-123",
        #        "message": "Processing started"}
    """

    _logger: "LoggingPortABC"
    _metrics: "MetricsPortABC"
    _bound_context: dict[str, Any] = field(default_factory=dict)

    @property
    def logger(self) -> "LoggingPortABC":
        """Get logger with bound context."""
        if self._bound_context:
            return self._logger.apply_bind(**self._bound_context)
        return self._logger

    @property
    def metrics(self) -> "MetricsPortABC":
        """Get metrics instance."""
        return self._metrics

    def with_context(self, **kwargs: Any) -> "ObservabilityContext":
        """Create new context with additional bindings.

        Args:
            **kwargs: Additional context values to bind.

        Returns:
            New ObservabilityContext with merged context.
        """
        new_context = {**self._bound_context, **kwargs}
        return ObservabilityContext(
            _logger=self._logger,
            _metrics=self._metrics,
            _bound_context=new_context,
        )

    def with_stage(self, stage_name: str) -> "ObservabilityContext":
        """Create context bound to specific stage.

        Convenience method for creating stage-specific context.

        Args:
            stage_name: Name of the pipeline stage.

        Returns:
            New context with stage binding.
        """
        return self.with_context(stage=stage_name)


class ObservabilityService:
    """Service for creating and managing observability contexts.

    Centralizes the creation of observability components and provides
    factory methods for creating scoped contexts.

    Example:
        >>> service = ObservabilityService(factory)
        >>> context = service.create_pipeline_context(
        ...     pipeline_id="chembl.activity",
        ...     run_id="run-123",
        ... )
        >>> context.logger.info("Pipeline started")
    """

    def __init__(self, factory: "ObservabilityFactoryPortABC") -> None:
        """Initialize service with factory.

        Args:
            factory: Factory for creating observability components.
        """
        self._factory = factory
        self._logger: "LoggingPortABC | None" = None
        self._metrics: "MetricsPortABC | None" = None

    def _get_logger(self) -> "LoggingPortABC":
        """Get or create logger instance (cached)."""
        if self._logger is None:
            self._logger = self._factory.create_logger()
        return self._logger

    def _get_metrics(self) -> "MetricsPortABC":
        """Get or create metrics instance (cached)."""
        if self._metrics is None:
            self._metrics = self._factory.create_metrics()
        return self._metrics

    def create_context(self, **initial_context: Any) -> ObservabilityContext:
        """Create new observability context with optional initial bindings.

        Args:
            **initial_context: Initial context values to bind.

        Returns:
            New ObservabilityContext instance.
        """
        return ObservabilityContext(
            _logger=self._get_logger(),
            _metrics=self._get_metrics(),
            _bound_context=initial_context,
        )

    def create_pipeline_context(
        self,
        pipeline_id: str,
        run_id: str,
        **extra: Any,
    ) -> ObservabilityContext:
        """Create context specifically for pipeline execution.

        Convenience method that creates a context with standard
        pipeline execution bindings.

        Args:
            pipeline_id: Pipeline identifier (e.g., "chembl.activity").
            run_id: Unique run identifier.
            **extra: Additional context values.

        Returns:
            ObservabilityContext configured for pipeline execution.
        """
        return self.create_context(
            pipeline_id=pipeline_id,
            run_id=run_id,
            **extra,
        )

    def create_stage_context(
        self,
        pipeline_context: ObservabilityContext,
        stage_name: str,
    ) -> ObservabilityContext:
        """Create context for specific pipeline stage.

        Args:
            pipeline_context: Parent pipeline context.
            stage_name: Name of the stage.

        Returns:
            ObservabilityContext bound to the stage.
        """
        return pipeline_context.with_stage(stage_name)


__all__ = [
    "ObservabilityContext",
    "ObservabilityService",
]
