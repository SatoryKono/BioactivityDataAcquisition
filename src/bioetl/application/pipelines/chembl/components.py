"""ChEMBL pipeline components container.

This module provides dataclasses for grouping ChEMBL pipeline dependencies,
reducing the number of constructor parameters and improving code organization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
    from bioetl.domain.observability import LoggingPortABC
    from bioetl.domain.pipelines.contracts import (
        ErrorPolicyABC,
        LoaderABC,
        PipelineHookABC,
    )
    from bioetl.domain.ports.entity_models import EntityModelRegistryABC
    from bioetl.domain.ports.extraction import ExtractionServiceABC
    from bioetl.domain.record_source import RecordSourceABC
    from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel
    from bioetl.domain.transform.contracts import (
        HashServiceABC,
        IndexGeneratorABC,
        NormalizationServiceABC,
        TimestampProviderABC,
    )
    from bioetl.domain.transform.transformers import TransformerABC
    from bioetl.domain.validation.service import ValidationService


@dataclass(frozen=True)
class ChemblCoreServices:
    """Core services required for ChEMBL pipeline operation.

    Groups the essential services that every ChEMBL pipeline needs.
    """

    extraction_service: "ExtractionServiceABC"
    """Service for extracting data from ChEMBL API."""

    validation_service: "ValidationService"
    """Service for schema validation."""

    normalization_service: "NormalizationServiceABC"
    """Service for data normalization."""

    entity_model_registry: "EntityModelRegistryABC"
    """Registry for entity model mappings."""


@dataclass(frozen=True)
class ChemblTransformServices:
    """Services for data transformation in ChEMBL pipeline.

    Groups hash, index, and timestamp services used during
    the transform stage.
    """

    hash_service: "HashServiceABC"
    """Service for computing record hashes."""

    index_generator: "IndexGeneratorABC"
    """Service for generating record indices."""

    timestamp_provider: "TimestampProviderABC"
    """Service for providing timestamps."""


@dataclass(frozen=True)
class ChemblPipelineComponents:
    """Complete set of components for ChEMBL pipeline.

    This dataclass groups all dependencies needed to construct a ChEMBL
    pipeline, reducing constructor parameters from 16+ to a single
    components object plus config.

    Example:
        >>> components = ChemblPipelineComponents(
        ...     core=ChemblCoreServices(...),
        ...     transform=ChemblTransformServices(...),
        ...     loader=my_loader,
        ...     logger=my_logger,
        ... )
        >>> pipeline = ChemblPipelineBase(config, components)
    """

    core: ChemblCoreServices
    """Core services (extraction, validation, normalization)."""

    transform: ChemblTransformServices
    """Transform services (hash, index, timestamp)."""

    loader: "LoaderABC"
    """Loader for writing output data."""

    logger: "LoggingPortABC"
    """Logger for pipeline operations."""

    # Optional components with defaults handled by pipeline
    schema_contract: "PipelineSchemaModel | None" = None
    """Optional schema contract override."""

    metadata_builder: "RunMetadataBuilderProtocol | None" = None
    """Optional metadata builder override."""

    hooks: "list[PipelineHookABC] | None" = None
    """Optional pipeline hooks."""

    error_policy: "ErrorPolicyABC | None" = None
    """Optional error handling policy."""

    post_transformer: "TransformerABC | None" = None
    """Optional post-transformation handler."""

    record_source: "RecordSourceABC | None" = None
    """Optional record source override."""


def create_chembl_components(
    *,
    extraction_service: "ExtractionServiceABC",
    validation_service: "ValidationService",
    normalization_service: "NormalizationServiceABC",
    entity_model_registry: "EntityModelRegistryABC",
    hash_service: "HashServiceABC",
    index_generator: "IndexGeneratorABC",
    timestamp_provider: "TimestampProviderABC",
    loader: "LoaderABC",
    logger: "LoggingPortABC",
    schema_contract: "PipelineSchemaModel | None" = None,
    metadata_builder: "RunMetadataBuilderProtocol | None" = None,
    hooks: "list[PipelineHookABC] | None" = None,
    error_policy: "ErrorPolicyABC | None" = None,
    post_transformer: "TransformerABC | None" = None,
    record_source: "RecordSourceABC | None" = None,
) -> ChemblPipelineComponents:
    """Factory function for creating ChemblPipelineComponents.

    This provides a flat parameter interface for cases where the
    grouped dataclass structure is not convenient.

    Args:
        extraction_service: ChEMBL extraction service.
        validation_service: Schema validation service.
        normalization_service: Data normalization service.
        entity_model_registry: Entity model registry.
        hash_service: Hash computation service.
        index_generator: Index generation service.
        timestamp_provider: Timestamp provider.
        loader: Output data loader.
        logger: Pipeline logger.
        schema_contract: Optional schema contract.
        metadata_builder: Optional metadata builder.
        hooks: Optional pipeline hooks.
        error_policy: Optional error policy.
        post_transformer: Optional post-transformer.
        record_source: Optional record source.

    Returns:
        ChemblPipelineComponents instance.
    """
    return ChemblPipelineComponents(
        core=ChemblCoreServices(
            extraction_service=extraction_service,
            validation_service=validation_service,
            normalization_service=normalization_service,
            entity_model_registry=entity_model_registry,
        ),
        transform=ChemblTransformServices(
            hash_service=hash_service,
            index_generator=index_generator,
            timestamp_provider=timestamp_provider,
        ),
        loader=loader,
        logger=logger,
        schema_contract=schema_contract,
        metadata_builder=metadata_builder,
        hooks=hooks,
        error_policy=error_policy,
        post_transformer=post_transformer,
        record_source=record_source,
    )


__all__ = [
    "ChemblCoreServices",
    "ChemblPipelineComponents",
    "ChemblTransformServices",
    "create_chembl_components",
]
