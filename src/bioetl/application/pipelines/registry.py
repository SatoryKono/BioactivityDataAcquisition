"""Registry of available pipeline implementations."""

from typing import Type

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase

# Registry mapping pipeline names to their implementation classes
PIPELINE_REGISTRY: dict[str, Type[PipelineBase]] = {
    "activity_chembl": ChemblPipelineBase,
    "assay_chembl": ChemblPipelineBase,
    "publication_chembl": ChemblPipelineBase,
    "target_chembl": ChemblPipelineBase,
    "molecule_chembl": ChemblPipelineBase,
}


def get_pipeline_class(name: str) -> Type[PipelineBase]:
    """
    Returns the pipeline class for the given name.

    Args:
        name: Pipeline name (e.g. 'activity_chembl')

    Raises:
        ValueError: If pipeline is not found.
    """
    if name not in PIPELINE_REGISTRY:
        raise ValueError(
            f"Pipeline '{name}' not found. Available: {list(PIPELINE_REGISTRY.keys())}"
        )
    return PIPELINE_REGISTRY[name]
