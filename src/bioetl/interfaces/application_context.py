"""Unified application context for sharing dependencies across interfaces.

This module provides a single, consolidated application context that replaces
multiple scattered singletons (_default_root, _context, _factory) with a
unified, testable context object.

The actual context storage is delegated to context_manager.py which uses
contextvars.ContextVar for thread-safe and async-safe context management.

Usage:
    # Get the default context
    ctx = get_application_context()

    # Access dependencies
    logger = ctx.logger
    use_case = ctx.use_case_factory.create_run_pipeline_use_case()
    registry = ctx.composition_root.get_provider_registry()

    # For testing - inject custom context
    test_ctx = ApplicationContext(
        logger=mock_logger,
        metrics=mock_metrics,
        config_loader=mock_loader,
        composition_root=mock_root,
    )
    set_application_context(test_ctx)

    # For scoped context (recommended for testing):
    from bioetl.interfaces.context_manager import application_context
    with application_context(test_ctx):
        # code uses test_ctx
    # original context restored
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
    from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
    from bioetl.interfaces.composition_root import CompositionRoot
    from bioetl.interfaces.use_case_factory import UseCaseFactory


@dataclass(frozen=True)
class ApplicationContext:
    """Unified container for application-wide dependencies.

    This is the single source of truth for application-wide dependencies,
    replacing multiple scattered singletons:
    - composition_root._default_root
    - application_context._context
    - use_case_factory._factory

    All dependencies are immutable and can be easily replaced for testing.

    Attributes:
        logger: Logging port for structured logging
        metrics: Metrics port for observability
        config_loader: Pipeline configuration loader
        composition_root: Dependency injection root for creating containers

    Example:
        >>> ctx = get_application_context()
        >>> use_case = ctx.use_case_factory.create_run_pipeline_use_case()
        >>> result = use_case.execute(pipeline_id="chembl.activity")
    """

    logger: LoggingPortABC
    metrics: MetricsPortABC
    config_loader: PipelineConfigLoaderProtocol
    composition_root: CompositionRoot

    @property
    def use_case_factory(self) -> "UseCaseFactory":
        """Get or create a use case factory for this context.

        The factory is created lazily and uses this context's composition_root.
        """
        from bioetl.interfaces.use_case_factory import UseCaseFactory

        return UseCaseFactory(self)

    @classmethod
    def create_default(cls) -> ApplicationContext:
        """Create context with production dependencies.

        This method bootstraps the application with production-ready
        infrastructure components.

        Returns:
            ApplicationContext with all production dependencies configured.
        """
        from bioetl.infrastructure.observability.factories import (
            create_logging_port,
            create_metrics_port,
        )
        from bioetl.interfaces.bootstrap_factory import create_default_bootstrap
        from bioetl.interfaces.composition_root import CompositionRoot

        bootstrap = create_default_bootstrap()
        bootstrap_context = bootstrap.start()

        if bootstrap_context.config_loader is None:
            raise RuntimeError("Config loader not available from bootstrap")

        return cls(
            logger=create_logging_port(),
            metrics=create_metrics_port(),
            config_loader=bootstrap_context.config_loader,
            composition_root=CompositionRoot(),
        )


# =============================================================================
# Context access functions - delegate to context_manager for thread-safety
# =============================================================================


def get_application_context() -> ApplicationContext:
    """Get or create the application context for the current thread/task.

    This is the primary entry point for obtaining application dependencies.
    The context is stored using contextvars.ContextVar for thread-safety.

    For testing, use set_application_context() to inject a custom context,
    or preferably use the application_context() context manager from
    context_manager.py for automatic cleanup.

    Returns:
        The ApplicationContext instance for the current thread/task.

    Example:
        >>> ctx = get_application_context()
        >>> logger = ctx.logger
    """
    from bioetl.interfaces.context_manager import get_current_context

    return get_current_context()


def set_application_context(context: ApplicationContext) -> None:
    """Set custom application context for the current thread/task.

    This is primarily used for testing. For scoped context that
    automatically restores the previous context, prefer using
    the application_context() context manager from context_manager.py.

    Args:
        context: Custom ApplicationContext to use.

    Example:
        >>> set_application_context(test_ctx)
        >>> # Now get_application_context() returns test_ctx
    """
    from bioetl.interfaces.context_manager import set_current_context

    set_current_context(context)


def reset_application_context() -> None:
    """Reset application context to force re-initialization.

    This is primarily used in tests to ensure a clean state between tests.
    After calling this, the next call to get_application_context() will
    create a new default context.
    """
    from bioetl.interfaces.context_manager import reset_current_context

    reset_current_context()


__all__ = [
    "ApplicationContext",
    "get_application_context",
    "set_application_context",
    "reset_application_context",
]
