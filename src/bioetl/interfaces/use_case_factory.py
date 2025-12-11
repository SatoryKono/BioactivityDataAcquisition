"""Factory helpers for constructing application-layer use cases.

This module provides UseCaseFactory for creating application use cases
with proper dependency injection. It integrates with ApplicationContext
as the single source of dependencies.

Usage:
    # Via ApplicationContext (recommended)
    ctx = get_application_context()
    use_case = ctx.use_case_factory.create_run_pipeline_use_case()

    # Direct instantiation (for testing)
    factory = UseCaseFactory(mock_context)
    use_case = factory.create_run_pipeline_use_case()

    # Legacy singleton (deprecated, delegates to ApplicationContext)
    factory = get_use_case_factory()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.use_cases import RunPipelineUseCase
    from bioetl.interfaces.application_context import ApplicationContext


class UseCaseFactory:
    """Factory for creating application use cases.

    Centralizes use case creation to eliminate duplication between CLI and REST.
    Receives dependencies from ApplicationContext for proper DI.

    Args:
        context: ApplicationContext providing all necessary dependencies.
            If None, will lazily get from get_application_context().

    Example:
        >>> ctx = get_application_context()
        >>> factory = UseCaseFactory(ctx)
        >>> use_case = factory.create_run_pipeline_use_case()
    """

    def __init__(self, context: "ApplicationContext | None" = None) -> None:
        self._context = context

    def _ensure_context(self) -> "ApplicationContext":
        """Ensure context is available, lazily creating if needed."""
        if self._context is None:
            from bioetl.interfaces.application_context import get_application_context

            self._context = get_application_context()
        return self._context

    def create_run_pipeline_use_case(self) -> "RunPipelineUseCase":
        """Create RunPipelineUseCase with all dependencies.

        Returns:
            Configured RunPipelineUseCase ready for execution.
        """
        from bioetl.application.use_cases import RunPipelineUseCase
        from bioetl.infrastructure.config.provider_registry import (
            create_provider_loader,
        )
        from bioetl.infrastructure.config.sources import get_configs_root

        ctx = self._ensure_context()

        # Use composition_root from context for container factory
        container_factory = ctx.composition_root.create_pipeline_container

        return RunPipelineUseCase(
            config_loader=ctx.config_loader,
            container_factory=container_factory,
            provider_loader_factory=create_provider_loader,
            configs_root=get_configs_root(None),
        )


def get_use_case_factory() -> UseCaseFactory:
    """Get use case factory from ApplicationContext singleton.

    This function delegates to ApplicationContext to ensure single source
    of truth for application dependencies.

    Returns:
        UseCaseFactory configured with current ApplicationContext.
    """
    from bioetl.interfaces.application_context import get_application_context

    return get_application_context().use_case_factory


def reset_use_case_factory() -> None:
    """Reset use case factory (for testing).

    Since UseCaseFactory is now created from ApplicationContext,
    this function resets the ApplicationContext instead.
    """
    from bioetl.interfaces.application_context import reset_application_context

    reset_application_context()


__all__ = [
    "UseCaseFactory",
    "get_use_case_factory",
    "reset_use_case_factory",
]
