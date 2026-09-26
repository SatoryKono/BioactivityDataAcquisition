"""Generic Pipeline Implementation.

Provides a universal pipeline class that can be used for any provider/entity
combination. Replaces provider-specific empty pipeline subclasses.

All pipelines are now configured via YAML and DI, eliminating the need for
separate class files per entity type.

Usage:
    # Via factory (recommended)
    factory = GenericPipelineFactory(
        pipeline_name="chembl_activity",
        pipeline_class=GenericPipeline,  # Use directly
        provider="chembl",
        ...
    )

    # Direct instantiation (for testing)
    pipeline = GenericPipeline.create(
        run_id=run_id,
        runtime=runtime,
        services=services,
        config=config,
        transformer=transformer,
    )
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class GenericPipeline(BasePipeline):
    """Universal pipeline for all provider/entity combinations.

    This class provides a concrete implementation of BasePipeline that works
    with any data source. All entity-specific logic is encapsulated in:

    - **Configuration**: YAML configs in `configs/entities/{provider}/{entity}.yaml`
    - **Transformation**: Transformer classes injected via DI
    - **Schemas**: Silver/Gold schemas for validation

    GenericPipeline eliminates the need for empty pipeline subclasses like
    ChEMBLActivityPipeline, PubChemCompoundPipeline, etc.

    Benefits:
    - DRY: No code duplication across pipeline classes
    - Extensibility: Add new pipelines via YAML config only
    - Consistency: All pipelines use identical orchestration logic
    - Testability: Single class to test, well-understood behavior

    Transformer Injection:
        Transformer is injected via DI from GenericPipelineFactory.
        If no transformer is provided, transform_bronze_to_silver() raises
        NotImplementedError (per BasePipeline contract).

    Example YAML Config:
        ```yaml
        pipeline_name: chembl_activity
        provider: chembl
        entity_type: activity
        primary_keys: ["activity_id"]
        silver_table: "chembl_activity"
        ```
    """

    # Inherits all behavior from BasePipeline:
    # - transform_bronze_to_silver() delegates to injected transformer
    # - Properties: config, runtime, services, run_id, context, logger, etc.
    # - Lifecycle: shutdown_signal


__all__ = ["GenericPipeline"]
