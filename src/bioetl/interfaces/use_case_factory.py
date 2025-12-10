"""Factory for creating application use cases.

This module provides a centralized factory for instantiating use cases
with all their dependencies. It eliminates code duplication between
CLI and REST interfaces by consolidating use case creation logic.

The UseCaseFactory uses ApplicationContext for shared dependencies and
wires together infrastructure components (container factory, provider loader,
config sources) in a single location.

Example:
    >>> # Get the singleton factory
    >>> factory = get_use_case_factory()
    >>> use_case = factory.create_run_pipeline_use_case()
    >>> response = use_case.execute(request)

    >>> # For testing, inject custom context
    >>> from bioetl.interfaces.application_context import set_application_context
    >>> set_application_context(mock_context)
    >>> factory = get_use_case_factory()  # Uses mock context
    >>> reset_use_case_factory()  # Clean up after test
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.config.provider_registry import create_provider_loader
from bioetl.infrastructure.config.sources import get_configs_root
from bioetl.interfaces.application_context import (
    ApplicationContext,
    get_application_context,
)
from bioetl.interfaces.composition_root import build_default_container

if TYPE_CHECKING:
    from bioetl.application.use_cases import RunPipelineUseCase


class UseCaseFactory:
    """Factory for creating use cases with injected dependencies.

    This factory centralizes the creation of use cases, ensuring consistent
    dependency injection across all interfaces (CLI, REST, etc.). It uses
    ApplicationContext for shared dependencies and wires together infrastructure
    components.

    Attributes:
        _context: The application context providing shared dependencies.

    Example:
        >>> context = ApplicationContext.create_default()
        >>> factory = UseCaseFactory(context)
        >>> use_case = factory.create_run_pipeline_use_case()
        >>> response = use_case.execute(request)
    """

    def __init__(self, context: ApplicationContext) -> None:
        """Initialize the factory with an application context.

        Args:
            context: Application context providing shared dependencies
                like config_loader, logger, and metrics.
        """
        self._context = context

    def create_run_pipeline_use_case(self) -> RunPipelineUseCase:
        """Create a RunPipelineUseCase with all required dependencies.

        Creates a fully configured use case for running ETL pipelines.
        All dependencies are resolved from the application context and
        infrastructure defaults.

        Returns:
            A configured RunPipelineUseCase ready for execution.

        Example:
            >>> factory = get_use_case_factory()
            >>> use_case = factory.create_run_pipeline_use_case()
            >>> request = RunPipelineRequest(pipeline_name="activity_chembl")
            >>> response = use_case.execute(request)
        """
        from bioetl.application.use_cases import RunPipelineUseCase

        return RunPipelineUseCase(
            config_loader=self._context.config_loader,
            container_factory=build_default_container,
            provider_loader_factory=create_provider_loader,
            configs_root=get_configs_root(None),
        )


# Module-level singleton for use case factory
_use_case_factory: UseCaseFactory | None = None


def get_use_case_factory() -> UseCaseFactory:
    """Get the singleton use case factory instance.

    Returns the current singleton factory, creating one with the default
    application context if none exists. This ensures consistent use case
    creation across the application.

    Returns:
        The singleton UseCaseFactory instance.

    Example:
        >>> factory = get_use_case_factory()
        >>> use_case = factory.create_run_pipeline_use_case()
    """
    global _use_case_factory  # noqa: PLW0603
    if _use_case_factory is None:
        _use_case_factory = UseCaseFactory(get_application_context())
    return _use_case_factory


def reset_use_case_factory() -> None:
    """Reset the use case factory singleton to None.

    Clears the singleton, causing the next call to get_use_case_factory()
    to create a fresh factory with the current application context.
    This is primarily useful for test cleanup to ensure test isolation.

    Example:
        >>> # In test teardown
        >>> reset_use_case_factory()
        >>> reset_application_context()
    """
    global _use_case_factory  # noqa: PLW0603
    _use_case_factory = None


__all__ = [
    "UseCaseFactory",
    "get_use_case_factory",
    "reset_use_case_factory",
]
