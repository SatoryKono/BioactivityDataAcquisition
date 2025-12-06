from typing import Type

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.pipeline import ChemblEntityPipeline

# Registry mapping pipeline names to their implementation classes
PIPELINE_REGISTRY: dict[str, Type[PipelineBase]] = {
    "activity_chembl": ChemblEntityPipeline,
    "assay_chembl": ChemblEntityPipeline,
    "document_chembl": ChemblEntityPipeline,
    "target_chembl": ChemblEntityPipeline,
    "testitem_chembl": ChemblEntityPipeline,
    "molecule_chembl": ChemblEntityPipeline,  # Alias for testitem
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
