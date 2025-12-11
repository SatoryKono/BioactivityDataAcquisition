"""Unified application context for sharing dependencies across interfaces.

This module provides a single, consolidated application context that replaces
multiple scattered singletons (_default_root, _context, _factory) with a
unified, testable context object.

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


# Module-level singleton
_context: ApplicationContext | None = None


def get_application_context() -> ApplicationContext:
    """Get or create the application context singleton.

    This is the primary entry point for obtaining application dependencies.
    For testing, use set_application_context() to inject a custom context.

    Returns:
        The singleton ApplicationContext instance.
    """
    global _context
    if _context is None:
        _context = ApplicationContext.create_default()
    return _context


def set_application_context(context: ApplicationContext) -> None:
    """Set custom application context (for testing).

    Args:
        context: Custom ApplicationContext to use as the singleton.
    """
    global _context
    _context = context


def reset_application_context() -> None:
    """Reset application context to force re-initialization.

    This is primarily used in tests to ensure a clean state between tests.
    """
    global _context
    _context = None


__all__ = [
    "ApplicationContext",
    "get_application_context",
    "set_application_context",
    "reset_application_context",
]
