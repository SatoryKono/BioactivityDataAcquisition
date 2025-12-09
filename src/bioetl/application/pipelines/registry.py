"""Registry of available pipeline implementations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Type

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase

PipelineFactory = Callable[..., PipelineBase]

_PIPELINE_REGISTRY: dict[str, PipelineFactory] = {
    "activity_chembl": ChemblPipelineBase,
    "assay_chembl": ChemblPipelineBase,
    "publication_chembl": ChemblPipelineBase,
    "target_chembl": ChemblPipelineBase,
    "molecule_chembl": ChemblPipelineBase,
}


def get_pipeline_factory(name: str) -> PipelineFactory:
    """Return factory callable for the given pipeline name."""

    try:
        return _PIPELINE_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(
            f"Pipeline '{name}' not found. Available: {list(_PIPELINE_REGISTRY.keys())}"
        ) from exc


def get_pipeline_class(name: str) -> Type[PipelineBase]:
    """Return pipeline class for the given name when registered as a class."""

    factory = get_pipeline_factory(name)
    if isinstance(factory, type) and issubclass(factory, PipelineBase):
        return factory
    raise ValueError(
        f"Pipeline '{name}' is registered with a non-class factory: {factory}"
    )


def get_registered_pipelines() -> dict[str, PipelineFactory]:
    """Return a copy of the registered pipeline mapping."""

    return dict(_PIPELINE_REGISTRY)
