"""Factory for creating application use cases.

Eliminates duplication between CLI and REST interfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.use_cases import RunPipelineUseCase

__all__ = ["UseCaseFactory", "get_use_case_factory", "reset_use_case_factory"]


class UseCaseFactory:
    """Factory for creating application use cases."""

    def __init__(self) -> None:
        """Initialize the factory with lazy context."""
        self._context = None

    def _ensure_context(self):
        """Ensure application context is initialized.

        Returns:
            The application context instance.
        """
        if self._context is None:
            from bioetl.interfaces.application_context import get_application_context

            self._context = get_application_context()
        return self._context

    def create_run_pipeline_use_case(self) -> RunPipelineUseCase:
        """Create a RunPipelineUseCase instance.

        Returns:
            Configured RunPipelineUseCase instance.
        """
        ctx = self._ensure_context()

        from bioetl.application.use_cases import RunPipelineUseCase
        from bioetl.infrastructure.config.provider_registry import create_provider_loader
        from bioetl.infrastructure.config.sources import get_configs_root
        from bioetl.interfaces.composition_root import build_default_container

        return RunPipelineUseCase(
            config_loader=ctx.config_loader,
            container_factory=build_default_container,
            provider_loader_factory=create_provider_loader,
            configs_root=get_configs_root(None),
        )


_factory: UseCaseFactory | None = None


def get_use_case_factory() -> UseCaseFactory:
    """Get the singleton UseCaseFactory instance.

    Returns:
        The UseCaseFactory singleton instance.
    """
    global _factory  # noqa: PLW0603
    if _factory is None:
        _factory = UseCaseFactory()
    return _factory


def reset_use_case_factory() -> None:
    """Reset the UseCaseFactory singleton.

    Useful for testing to ensure a fresh factory instance.
    """
    global _factory  # noqa: PLW0603
    _factory = None
