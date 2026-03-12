"""Registry helpers for CLI entrypoints.

These helpers preserve the historical ``get_default_registry`` surface for CLI
code paths while avoiding ambient global registry state. Each call returns a
fresh, explicitly populated ``PipelineRegistry`` instance.
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry import PipelineRegistry, create_registry

__all__ = ["build_cli_registry", "get_default_registry"]


def build_cli_registry() -> PipelineRegistry:
    """Build a fresh explicit registry for one CLI invocation."""
    registry = create_registry()
    register_all_pipelines(registry=registry)
    return registry


def get_default_registry() -> PipelineRegistry:
    """Compatibility alias returning an explicit CLI registry instance."""
    return build_cli_registry()
