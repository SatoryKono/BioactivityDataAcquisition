"""Application context for interfaces layer.

This module provides an immutable container for application-wide dependencies
used across the interfaces layer. It consolidates observability and configuration
dependencies into a single, testable context.

The ApplicationContext enables clean dependency injection in CLI, REST,
and other interface adapters while maintaining immutability for thread safety.

Example:
    >>> # Production usage
    >>> context = ApplicationContext.create_default()
    >>> context.logger.info("Application started")

    >>> # Test usage
    >>> mock_context = ApplicationContext(
    ...     logger=MockLogger(),
    ...     metrics=MockMetrics(),
    ...     config_loader=MockConfigLoader(),
    ... )
    >>> set_application_context(mock_context)
    >>> # ... test ...
    >>> reset_application_context()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
    from bioetl.domain.observability.contracts import (
        LoggingPortABC,
        MetricsPortABC,
    )


@dataclass(frozen=True)
class ApplicationContext:
    """Immutable container for application-wide dependencies.

    This context consolidates all cross-cutting concerns (logging, metrics,
    configuration) into a single dependency that can be easily injected
    or mocked for testing.

    Attributes:
        logger: Structured logging port for application-wide logging.
        metrics: Metrics collection port for observability.
        config_loader: Pipeline configuration loader for accessing configs.

    Example:
        >>> context = ApplicationContext.create_default()
        >>> context.logger.info("Processing started", pipeline="chembl")
        >>> context.metrics.inc_counter("requests", {"endpoint": "/run"})
    """

    logger: LoggingPortABC
    metrics: MetricsPortABC
    config_loader: PipelineConfigLoaderProtocol

    @classmethod
    def create_default(cls) -> ApplicationContext:
        """Create an ApplicationContext with production configuration.

        This factory method creates a fully configured context with:
        - Structured JSON logger (via structlog)
        - Prometheus-backed metrics
        - File-based pipeline config loader

        Returns:
            ApplicationContext configured for production use.

        Raises:
            RuntimeError: If config loader is not available from bootstrap.

        Example:
            >>> context = ApplicationContext.create_default()
            >>> context.logger.info("Ready")
        """
        from bioetl.infrastructure.observability.factories import (
            create_logging_port,
            create_metrics_port,
        )
        from bioetl.interfaces.bootstrap_factory import create_default_bootstrap

        bootstrap = create_default_bootstrap()
        app_context = bootstrap.start()

        if app_context.config_loader is None:
            raise RuntimeError(
                "Config loader not available from bootstrap. "
                "This indicates a configuration error."
            )

        return cls(
            logger=create_logging_port(),
            metrics=create_metrics_port(),
            config_loader=app_context.config_loader,
        )


# Module-level singleton for application context
_application_context: ApplicationContext | None = None


def get_application_context() -> ApplicationContext:
    """Get the current application context.

    Returns the singleton application context, creating a default one
    if none has been set.

    Returns:
        The current ApplicationContext instance.

    Example:
        >>> context = get_application_context()
        >>> context.logger.info("Using shared context")
    """
    global _application_context  # noqa: PLW0603
    if _application_context is None:
        _application_context = ApplicationContext.create_default()
    return _application_context


def set_application_context(context: ApplicationContext) -> None:
    """Set the application context.

    Replaces the current context with the provided one. This is primarily
    useful for testing, where you want to inject mock dependencies.

    Args:
        context: The ApplicationContext to use as the singleton.

    Example:
        >>> mock_context = ApplicationContext(
        ...     logger=MockLogger(),
        ...     metrics=MockMetrics(),
        ...     config_loader=MockConfigLoader(),
        ... )
        >>> set_application_context(mock_context)
    """
    global _application_context  # noqa: PLW0603
    _application_context = context


def reset_application_context() -> None:
    """Reset the application context to None.

    Clears the singleton, causing the next call to get_application_context()
    to create a fresh default context. This is primarily useful for test
    cleanup to ensure test isolation.

    Example:
        >>> # In test teardown
        >>> reset_application_context()
    """
    global _application_context  # noqa: PLW0603
    _application_context = None


__all__ = [
    "ApplicationContext",
    "get_application_context",
    "reset_application_context",
    "set_application_context",
]
