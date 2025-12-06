"""
Factories for ChEMBL pipelines.
"""

from bioetl.application.container import PipelineContainer
from bioetl.application.pipelines.chembl.pipeline import ChemblEntityPipeline


def create_chembl_pipeline(container: PipelineContainer) -> ChemblEntityPipeline:
    """
    Creates a ChEMBL entity pipeline using dependencies from container.

    Args:
        container: Dependency injection container.

    Returns:
        Configured ChemblEntityPipeline.
    """
    return ChemblEntityPipeline(
        config=container.config,
        logger=container.get_logger(),
        validation_service=container.get_validation_service(),
        output_writer=container.get_output_writer(),
        extraction_service=container.get_extraction_service(),
        hash_service=container.get_hash_service(),
        record_source=None,  # Pipeline resolves source based on config
        normalization_service=container.get_normalization_service(),
        hooks=container.get_hooks(),
        error_policy=container.get_error_policy(),
    )
