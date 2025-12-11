"""Registry of available pipeline implementations and factories."""

from __future__ import annotations

from typing import Type

from bioetl.application.contracts import PipelineFactoryABC
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.factories import ChemblPipelineFactory

# Factory registry: maps pipeline names to their factory instances
_FACTORY_REGISTRY: dict[str, PipelineFactoryABC] = {
    "activity_chembl": ChemblPipelineFactory(),
    "assay_chembl": ChemblPipelineFactory(),
    "publication_chembl": ChemblPipelineFactory(),
    "target_chembl": ChemblPipelineFactory(),
    "molecule_chembl": ChemblPipelineFactory(),
}


def list_pipelines() -> list[str]:
    """Return sorted list of available pipeline identifiers."""

    return sorted(_FACTORY_REGISTRY.keys())


def get_pipeline_factory(name: str) -> PipelineFactoryABC:
    """Return the factory instance for the given pipeline name."""

    try:
        return _FACTORY_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(
            f"Pipeline factory '{name}' not found. "
            f"Available: {list(_FACTORY_REGISTRY.keys())}"
        ) from exc


def get_factory(name: str) -> PipelineFactoryABC:
    """Backward-compatible alias for :func:`get_pipeline_factory`."""

    return get_pipeline_factory(name)


def get_pipeline_class(name: str) -> Type[PipelineBase]:
    """Return pipeline class exposed by the registered factory."""

    factory = get_pipeline_factory(name)
    pipeline_cls = getattr(factory, "pipeline_cls", None)
    if isinstance(pipeline_cls, type) and issubclass(pipeline_cls, PipelineBase):
        return pipeline_cls
    raise ValueError(
        f"Pipeline '{name}' is registered without accessible pipeline class"
    )


def get_registered_factories() -> dict[str, PipelineFactoryABC]:
    """Return a copy of the registered factory mapping."""

    return dict(_FACTORY_REGISTRY)


__all__ = [
    "get_factory",
    "get_pipeline_class",
    "get_pipeline_factory",
    "get_registered_factories",
    "list_pipelines",
]
