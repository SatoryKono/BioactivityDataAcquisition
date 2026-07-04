"""Shared runtime-registration seam for composition entrypoints."""

from __future__ import annotations

from enum import StrEnum

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry

__all__ = ["RuntimeRegistrationScope", "ensure_runtime_registrations"]


class RuntimeRegistrationScope(StrEnum):
    """Runtime registration scopes exposed by composition entrypoints."""

    PROVIDERS = "providers"
    PIPELINES = "pipelines"


def ensure_runtime_registrations(
    registry: PipelineRegistry | None = None,
    *,
    scope: RuntimeRegistrationScope | str = RuntimeRegistrationScope.PIPELINES,
) -> None:
    """Ensure the requested runtime registration scope for shared entrypoints."""
    resolved_scope = RuntimeRegistrationScope(scope)
    ensure_providers_loaded()
    if resolved_scope is RuntimeRegistrationScope.PROVIDERS:
        return
    if registry is None or not registry.list_pipelines():
        register_all_pipelines(registry=registry)
