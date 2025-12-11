from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.use_cases import RunPipelineUseCase


class UseCaseFactory:
    """Factory for creating application use cases.

    Centralizes use case creation to eliminate duplication between CLI and REST.
    """

    def __init__(self) -> None:
        self._context = None

    def _ensure_context(self):
        if self._context is None:
            from bioetl.interfaces.application_context import get_application_context
            self._context = get_application_context()
        return self._context

    def create_run_pipeline_use_case(self) -> RunPipelineUseCase:
        """Create RunPipelineUseCase with all dependencies."""
        from bioetl.application.use_cases import RunPipelineUseCase
        from bioetl.infrastructure.config.provider_registry import (
            create_provider_loader,
        )
        from bioetl.infrastructure.config.sources import get_configs_root
        from bioetl.interfaces.composition_root import build_default_container

        ctx = self._ensure_context()

        return RunPipelineUseCase(
            config_loader=ctx.config_loader,
            container_factory=build_default_container,
            provider_loader_factory=create_provider_loader,
            configs_root=get_configs_root(None),
        )


_factory: UseCaseFactory | None = None


def get_use_case_factory() -> UseCaseFactory:
    """Get or create the use case factory singleton."""
    global _factory
    if _factory is None:
        _factory = UseCaseFactory()
    return _factory


def reset_use_case_factory() -> None:
    """Reset use case factory (for testing)."""
    global _factory
    _factory = None


__all__ = [
    "UseCaseFactory",
    "get_use_case_factory",
    "reset_use_case_factory",
]
