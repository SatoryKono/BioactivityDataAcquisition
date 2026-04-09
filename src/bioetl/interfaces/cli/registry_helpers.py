"""Registry helpers for CLI entrypoints.

These helpers provide the canonical explicit-registry path for CLI code paths
without ambient global registry state. Each call returns a fresh, explicitly
populated ``PipelineRegistry`` instance.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "build_cli_registry",
    "create_registry",
    "register_all_pipelines",
]


def create_registry() -> PipelineRegistry:
    """Create a fresh registry via the public composition facade."""
    from bioetl.composition.registry_api import create_registry as _impl

    return _impl()


def register_all_pipelines(*, registry: PipelineRegistry | None = None) -> None:
    """Register pipelines via the public composition facade."""
    from bioetl.composition.registry_api import register_all_pipelines as _impl

    _impl(registry=registry)


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
