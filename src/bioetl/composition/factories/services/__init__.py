"""Services factory subpackage (DI for PipelineRunner)."""

from __future__ import annotations

from importlib import import_module

from bioetl.composition.factories.pipeline.creation_support import (
    _BuildPipelineServicesFn as _BuildPipelineServicesFn,
)

_PIPELINE_CREATION_EXPORTS = frozenset(
    {
        "_BuildPipelineServicesFn",
        "_PipelineCreationInputs",
        "_ServiceBundleDeps",
        "_create_pipeline_with_services_impl",
    }
)

_FACTORY_EXPORTS = frozenset(
    {
        "BaseServicesFactory",
        "ServicesBuilder",
        "create_data_normalization_service",
    }
)

_SUBMODULE_EXPORTS = frozenset({"factory", "bundle"})

_OBSERVABILITY_EXPORTS = frozenset(
    {
        "_create_cached_bronze_data_source",
        "_create_data_source",
        "create_shared_metrics",
    }
)


def __getattr__(name: str) -> object:
    """Expose service factory helpers lazily to avoid package import cycles."""
    if name in _SUBMODULE_EXPORTS:
        return import_module(f"bioetl.composition.factories.services.{name}")
    if name in _PIPELINE_CREATION_EXPORTS:
        return getattr(
            import_module("bioetl.composition.factories.pipeline.creation_support"),
            name,
        )
    if name in _FACTORY_EXPORTS:
        from bioetl.composition.factories.services import factory as _factory

        return getattr(_factory, name)
    if name in _OBSERVABILITY_EXPORTS:
        from bioetl.composition.factories.services import (
            observability_api as _observability_api,
        )

        return getattr(_observability_api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseServicesFactory",
    "ServicesBuilder",
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_ServiceBundleDeps",
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "_create_pipeline_with_services_impl",
    "bundle",
    "create_data_normalization_service",
    "create_shared_metrics",
    "factory",
]
