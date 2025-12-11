"""Registry of available pipeline implementations and factories."""

from __future__ import annotations

from collections.abc import Callable
from typing import Type

from bioetl.application.contracts import PipelineFactoryABC
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.chembl.factories import ChemblPipelineFactory

PipelineFactory = Callable[..., PipelineBase]

# Registry mapping pipeline names to pipeline classes
PIPELINE_REGISTRY: dict[str, PipelineFactory] = {
    "activity_chembl": ChemblPipelineBase,
    "assay_chembl": ChemblPipelineBase,
    "publication_chembl": ChemblPipelineBase,
    "target_chembl": ChemblPipelineBase,
    "molecule_chembl": ChemblPipelineBase,
}

# Factory registry: maps pipeline names to their factory instances
# This is the preferred way to create pipelines
_FACTORY_REGISTRY: dict[str, PipelineFactoryABC] = {
    "activity_chembl": ChemblPipelineFactory(),
    "assay_chembl": ChemblPipelineFactory(),
    "publication_chembl": ChemblPipelineFactory(),
    "target_chembl": ChemblPipelineFactory(),
    "molecule_chembl": ChemblPipelineFactory(),
}


def get_pipeline_factory(name: str) -> PipelineFactory:
    """Return factory callable for the given pipeline name."""

    try:
        return PIPELINE_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(
            f"Pipeline '{name}' not found. Available: {list(PIPELINE_REGISTRY.keys())}"
        ) from exc


def get_pipeline_class(name: str) -> Type[PipelineBase]:
    """Return pipeline class for the given name when registered as a class."""

    factory = get_pipeline_factory(name)
    if isinstance(factory, type) and issubclass(factory, PipelineBase):
        return factory
    raise ValueError(
        f"Pipeline '{name}' is registered with a non-class factory: {factory}"
    )


def get_factory(name: str) -> PipelineFactoryABC:
    """
    Return the factory instance for creating pipelines of the given type.

    This is the preferred method for obtaining pipeline factories.

    Args:
        name: Pipeline name (e.g., 'activity_chembl').

    Returns:
        Factory instance implementing PipelineFactoryABC.

    Raises:
        ValueError: If no factory is registered for the given name.
    """
    try:
        return _FACTORY_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(
            f"Pipeline factory '{name}' not found. "
            f"Available: {list(_FACTORY_REGISTRY.keys())}"
        ) from exc


def get_registered_pipelines() -> dict[str, PipelineFactory]:
    """Return a copy of the registered pipeline mapping."""

    return dict(PIPELINE_REGISTRY)


def get_registered_factories() -> dict[str, PipelineFactoryABC]:
    """Return a copy of the registered factory mapping."""

    return dict(_FACTORY_REGISTRY)


__all__ = [
    "PIPELINE_REGISTRY",
    "PipelineFactory",
    "get_factory",
    "get_pipeline_class",
    "get_pipeline_factory",
    "get_registered_factories",
    "get_registered_pipelines",
]
