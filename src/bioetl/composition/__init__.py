"""Composition Root for BioETL dependency injection.

This package contains the Composition Root - the single place where
all dependencies are composed and wired together according to the
Ports & Adapters architecture (RULES.md).

Components:
    bootstrap: Pipeline bootstrapping and factory functions.
    registry: Pipeline registry for dynamic pipeline discovery.
    builders: Builder classes for constructing pipelines.
    types: Type definitions for composition layer.
    observability: Observability setup (tracing, metrics, logging).
    entrypoints: CLI and API entrypoints.

The composition layer is the only layer allowed to import from
infrastructure and wire concrete implementations to domain ports.

See Also:
    docs/02-architecture/decisions/ADR-005-composition-layer-separation.md
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.registry import (
        PipelineDefinition,
        PipelineRegistry,
        create_registry,
    )
    from bioetl.composition.registry_default import get_default_registry

_LAZY_MODULE_EXPORTS: dict[str, str] = {
    "bootstrap": "bioetl.composition.bootstrap",
    "composite_api": "bioetl.composition.composite_api",
    "control_plane_api": "bioetl.composition.control_plane_api",
    "entrypoints": "bioetl.composition.entrypoints",
    "execution_api": "bioetl.composition.execution_api",
    "health_api": "bioetl.composition.health_api",
    "maintenance_api": "bioetl.composition.maintenance_api",
    "observability_api": "bioetl.composition.observability_api",
    "registry_api": "bioetl.composition.registry_api",
    "resources_api": "bioetl.composition.resources_api",
    "resource_management_api": "bioetl.composition.resource_management_api",
    "services_api": "bioetl.composition.services_api",
    "types": "bioetl.composition.types",
}
_LAZY_ATTR_EXPORTS: dict[str, tuple[str, str]] = {
    "PipelineDefinition": ("bioetl.composition.registry", "PipelineDefinition"),
    "PipelineRegistry": ("bioetl.composition.registry", "PipelineRegistry"),
    "create_registry": ("bioetl.composition.registry", "create_registry"),
    "get_default_registry": (
        "bioetl.composition.registry_default",
        "get_default_registry",
    ),
}

__all__ = [
    "PipelineDefinition",
    "PipelineRegistry",
    "bootstrap",
    "composite_api",
    "control_plane_api",
    "create_registry",
    "entrypoints",
    "execution_api",
    "get_default_registry",
    "health_api",
    "maintenance_api",
    "observability_api",
    "registry_api",
    "resource_management_api",
    "resources_api",
    "services_api",
    "types",
]


def __getattr__(name: str) -> object:
    """Lazily expose composition modules and registry helpers."""
    module_name = _LAZY_MODULE_EXPORTS.get(name)
    if module_name is not None:
        module: ModuleType = import_module(module_name)
        globals()[name] = module
        return module

    attr_target = _LAZY_ATTR_EXPORTS.get(name)
    if attr_target is not None:
        target_module_name, attr_name = attr_target
        value = getattr(import_module(target_module_name), attr_name)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Return stable composition exports for help() and shell introspection."""
    return sorted(set(globals()) | set(__all__))
