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
        from bioetl.interfaces.factories.provider_registry import (
            create_provider_registry_factory,
        )

        ctx = self._ensure_context()
        root = ctx.composition_root

        # Use composition_root methods to avoid direct infrastructure imports
        return RunPipelineUseCase(
            config_loader=ctx.config_loader,
            container_factory=root.create_pipeline_container,
            provider_loader_factory=root.create_provider_loader(),
            provider_registry_factory=create_provider_registry_factory(),
            configs_root=root.get_configs_root(),
        )


__all__ = [
    "UseCaseFactory",
]
