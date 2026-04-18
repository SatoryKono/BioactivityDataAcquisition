"""Record-processor assembly helpers for pipeline_builder facade."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    RecordProcessor,
    RecordProcessorConfig,
)
from bioetl.composition.factories.services._record_processor_policy_support import (
    extract_gold_schema_policy_by_version,
    extract_hash_policy,
    extract_hash_policy_by_version,
)
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pandera as pdr
    import pyarrow as pa

    from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import GoldValidatorPort, TracingPort
    from bioetl.domain.types import GoldSchemaType


def build_record_processor_config_and_validator(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    bronze_output_path: str | None,
    silver_output_path: str | None,
    gold_output_path: str | None,
    flat_structure: bool,
    gold_validator_factory: Callable[..., GoldValidatorPort] = PanderaGoldValidator,
) -> tuple[RecordProcessorConfig, GoldValidatorPort]:
    """Build RecordProcessorConfig plus Gold validator from pipeline state."""
    include_fields, exclude_fields = extract_hash_policy(pipeline)
    hash_policy_by_version = extract_hash_policy_by_version(
        pipeline,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    gold_schema_policy_by_version = extract_gold_schema_policy_by_version(
        pipeline,
        gold_schema=gold_schema,
    )
    active_gold_schema = (
        gold_schema_policy_by_version.active_schema
        if gold_schema_policy_by_version is not None
        else gold_schema
    )
    processor_config = RecordProcessorConfig(
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=cast("DQConfig | None", pipeline.config.dq),
        table_config=pipeline.config.table,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
        column_groups=pipeline.config.column_groups,
        scd_config=pipeline.config.scd_config,
        content_hash_include_fields=include_fields,
        content_hash_exclude_fields=exclude_fields,
        content_hash_policy_by_version=hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )
    gold_validator = gold_validator_factory(
        cast("pdr.DataFrameSchema | None", active_gold_schema),
        strict=strict_gold_validation,
    )
    return processor_config, gold_validator


def create_record_processor_from_pipeline(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    callbacks: PipelineCallbacksContext,
    create_record_processor_fn: Callable[..., RecordProcessor],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
) -> RecordProcessor:
    """Project pipeline fields into the injected record-processor factory."""
    include_fields, exclude_fields = extract_hash_policy(pipeline)
    hash_policy_by_version = extract_hash_policy_by_version(
        pipeline,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    gold_schema_policy_by_version = extract_gold_schema_policy_by_version(
        pipeline,
        gold_schema=gold_schema,
    )
    return create_record_processor_fn(
        services=pipeline.services,
        context=pipeline.context,
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=pipeline.config.dq,
        primary_keys=pipeline.config.table.primary_keys,
        silver_table=pipeline.config.effective_silver_table,
        gold_table=pipeline.config.effective_gold_table,
        silver_write_mode=pipeline.config.table.silver_write_mode,
        gold_write_mode=pipeline.config.table.gold_write_mode,
        on_schema_mismatch=pipeline.config.table.on_schema_mismatch,
        transform_callback=callbacks.transform,
        gold_filter_callback=callbacks.gold_filter,
        gold_transform_callback=callbacks.gold_transform,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
        column_groups=tuple(pipeline.config.column_groups),
        scd_config=pipeline.config.scd_config,
        content_hash_include_fields=include_fields,
        content_hash_exclude_fields=exclude_fields,
        content_hash_policy_by_version=hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )
