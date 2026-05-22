"""Shared runtime-registration seam for composition entrypoints."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry

__all__ = ["ensure_runtime_registrations"]


def ensure_runtime_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure providers and pipelines are registered for shared entrypoints."""
    ensure_providers_loaded()
    if registry is None or not registry.list_pipelines():
        register_all_pipelines(registry=registry)
