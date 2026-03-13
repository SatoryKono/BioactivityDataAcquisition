"""Registry helpers for CLI entrypoints.

These helpers preserve the historical ``get_default_registry`` surface for CLI
code paths while avoiding ambient global registry state. Each call returns a
fresh, explicitly populated ``PipelineRegistry`` instance.
"""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry import PipelineRegistry, create_registry

__all__ = [
    "build_cli_registry",
    "create_registry",
    "get_default_registry",
    "register_all_pipelines",
]


def _build_registered_registry(
    *,
    create_registry_fn: Callable[[], PipelineRegistry],
    register_all_pipelines_fn: Callable[..., None],
) -> PipelineRegistry:
    """Build and populate a fresh registry using explicit collaborators."""
    registry = create_registry_fn()
    register_all_pipelines_fn(registry=registry)
    return registry


def build_cli_registry() -> PipelineRegistry:
    """Build a fresh explicit registry for one CLI invocation."""
    return _build_registered_registry(
        create_registry_fn=create_registry,
        register_all_pipelines_fn=register_all_pipelines,
    )


def get_default_registry() -> PipelineRegistry:
    """Compatibility alias returning an explicit CLI registry instance."""
    return build_cli_registry()
