"""
Factory for ChEMBL pipeline creation.

This module provides the single entry point for creating ChEMBL pipelines,
ensuring consistent configuration and dependency injection.
"""

from __future__ import annotations

from bioetl.application.contracts import PipelineContainerABC, PipelineFactoryABC
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblPipelineFactory(PipelineFactoryABC):
    """
    Factory for creating ChEMBL entity pipelines.

    This factory centralizes all ChEMBL pipeline creation logic, ensuring
    dependencies are properly resolved from the container and the pipeline
    is fully configured before returning.
    """

    def create(
        self,
        container: PipelineContainerABC,
        *,
        limit: int | None = None,
    ) -> PipelineBase:
        """
        Create a fully configured ChEMBL pipeline.

        Args:
            container: Dependency injection container providing services.
            limit: Optional record limit for extraction.

        Returns:
            Configured ChemblPipelineBase ready to run.
        """
        logger = container.get_logger()
        extraction_service = container.get_extraction_service()
        record_source = container.get_record_source(
            extraction_service=extraction_service,
            limit=limit,
            logger=logger,
        )

        pipeline: PipelineBase = ChemblPipelineBase(
            config=container.config,
            logger=logger,
            validation_service=container.get_validation_service(),
            loader=container.get_loader(),
            extraction_service=extraction_service,
            hash_service=container.get_hash_service(),
            index_generator=container.get_index_generator(),
            timestamp_provider=container.get_timestamp_provider(),
            entity_model_registry=container.get_entity_model_registry(),
            schema_contract=container.get_schema_contract(),
            metadata_builder=container.get_metadata_builder(),
            normalization_service=container.get_normalization_service(),
            hooks=container.get_hooks(),
            error_policy=container.get_error_policy(),
            record_source=record_source,
        )

        # Set post-transformer with version provider from the pipeline
        pipeline.set_post_transformer(
            container.get_post_transformer(version_provider=pipeline.get_version)
        )

        # Register hooks and error policy for runtime notifications
        pipeline.register_hooks(container.get_hooks())
        pipeline.set_error_policy(container.get_error_policy())

        return pipeline


__all__ = ["ChemblPipelineFactory"]
