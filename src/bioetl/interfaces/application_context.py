from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
    from bioetl.domain.observability import LoggingPortABC, MetricsPortABC


@dataclass(frozen=True)
class ApplicationContext:
    """Immutable container for application-wide dependencies.

    Replaces scattered singletons with a single, testable context object.
    """

    logger: LoggingPortABC
    metrics: MetricsPortABC
    config_loader: PipelineConfigLoaderProtocol

    @classmethod
    def create_default(cls) -> ApplicationContext:
        """Create context with production dependencies."""
        from bioetl.infrastructure.observability.factories import (
            create_logging_port,
            create_metrics_port,
        )
        from bioetl.interfaces.bootstrap_factory import create_default_bootstrap

        bootstrap = create_default_bootstrap()
        context = bootstrap.start()

        if context.config_loader is None:
            raise RuntimeError("Config loader not available from bootstrap")

        return cls(
            logger=create_logging_port(),
            metrics=create_metrics_port(),
            config_loader=context.config_loader,
        )


_context: ApplicationContext | None = None


def get_application_context() -> ApplicationContext:
    """Get or create the application context singleton."""
    global _context
    if _context is None:
        _context = ApplicationContext.create_default()
    return _context


def set_application_context(context: ApplicationContext) -> None:
    """Set custom application context (for testing)."""
    global _context
    _context = context


def reset_application_context() -> None:
    """Reset application context (for testing)."""
    global _context
    _context = None


__all__ = [
    "ApplicationContext",
    "get_application_context",
    "set_application_context",
    "reset_application_context",
]
