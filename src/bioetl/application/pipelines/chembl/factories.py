"""
Factories for ChEMBL pipelines.
"""

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel


def create_chembl_pipeline(container: PipelineContainerABC) -> ChemblPipelineBase:
    """
    Creates a ChEMBL entity pipeline using dependencies from container.

    Args:
        container: Dependency injection container.

    Returns:
        Configured ChemblPipelineBase.
    """
    extraction_service = container.get_extraction_service()
    logger = container.get_logger()

    record_source = container.get_record_source(
        extraction_service,
        logger=logger,
        model_cls=ActivityRawModel,
    )

    return ChemblPipelineBase(
        config=container.config,
        logger=logger,
        validation_service=container.get_validation_service(),
        loader=container.get_loader(),
        extraction_service=extraction_service,
        hash_service=container.get_hash_service(),
        metadata_builder=container.get_metadata_builder(),
        record_source=record_source,
        normalization_service=container.get_normalization_service(),
        hooks=container.get_hooks(),
        error_policy=container.get_error_policy(),
    )
