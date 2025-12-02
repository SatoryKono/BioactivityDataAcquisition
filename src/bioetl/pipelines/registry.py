from typing import Type

from bioetl.core.pipeline_base import PipelineBase
from bioetl.pipelines.chembl.activity.run import ChemblActivityPipeline
from bioetl.pipelines.chembl.assay.run import ChemblAssayPipeline
from bioetl.pipelines.chembl.document.run import ChemblDocumentPipeline
from bioetl.pipelines.chembl.target.run import ChemblTargetPipeline
from bioetl.pipelines.chembl.testitem.run import ChemblTestitemPipeline

# Registry mapping pipeline names to their implementation classes
PIPELINE_REGISTRY: dict[str, Type[PipelineBase]] = {
    "activity_chembl": ChemblActivityPipeline,
    "assay_chembl": ChemblAssayPipeline,
    "document_chembl": ChemblDocumentPipeline,
    "target_chembl": ChemblTargetPipeline,
    "testitem_chembl": ChemblTestitemPipeline,
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
        raise ValueError(f"Pipeline '{name}' not found. Available: {list(PIPELINE_REGISTRY.keys())}")
    return PIPELINE_REGISTRY[name]

