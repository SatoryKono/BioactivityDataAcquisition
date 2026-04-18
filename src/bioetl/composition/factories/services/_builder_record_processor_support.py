"""Injected helper for ServicesBuilder record-processor assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.runtime import RecordProcessor
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pandera as pdr
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import (
        ContentHashPolicyByVersion,
        GoldFilterCallback,
        GoldTransformCallback,
        PipelineService,
        RecordProcessorConfig,
        TransformCallback,
    )
    from bioetl.application.core.wiring.runtime import BasePipeline
    from bioetl.composition.factories.services.builder import ServicesBuilder
    from bioetl.domain.composite.config import ColumnGroupConfig
    from bioetl.domain.config import DQConfig, MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        GoldValidatorPort,
        MemoryMonitorPort,
        TracingPort,
    )
    from bioetl.domain.types import (
        GoldSchemaPolicyByVersion,
        GoldSchemaType,
        ScdConfig,
    )


def create_record_processor_impl(
    *,
    services_builder: type[ServicesBuilder],
    services: PipelineService,
    context: PipelineContext,
    pipeline_name: str,
    provider: str,
    entity_type: str,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    dq_config: DQConfig | None,
    primary_keys: tuple[str, ...] | list[str],
    silver_table: str,
    gold_table: str | None,
    silver_write_mode: str,
    gold_write_mode: str,
    on_schema_mismatch: str,
    transform_callback: TransformCallback,
    gold_filter_callback: GoldFilterCallback,
    gold_transform_callback: GoldTransformCallback,
    tracer: TracingPort | None,
    strict_gold_validation: bool,
    lock_validator,
    column_groups: tuple[ColumnGroupConfig, ...],
    scd_config: ScdConfig | None,
    content_hash_include_fields: frozenset[str],
    content_hash_exclude_fields: frozenset[str],
    content_hash_policy_by_version: ContentHashPolicyByVersion | None,
    gold_schema_policy_by_version: GoldSchemaPolicyByVersion | None,
    record_processor_config_cls: type[RecordProcessorConfig],
    table_config_cls: type[TableConfig],
    gold_validator_factory: type[GoldValidatorPort] | type[PanderaGoldValidator],
    record_processor_cls: type[RecordProcessor],
) -> RecordProcessor:
    """Build a RecordProcessor using constructors injected from the public module."""
    effective_tracer = tracer or services.tracing
    active_gold_schema = (
        gold_schema_policy_by_version.active_schema
        if gold_schema_policy_by_version is not None
        else gold_schema
    )
    processor_config = record_processor_config_cls(
        pipeline_name=pipeline_name,
        provider=provider,
        entity_type=entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=dq_config,
        table_config=table_config_cls(
            primary_keys=tuple(primary_keys),
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,
        ),
        column_groups=column_groups,
        scd_config=scd_config,
        content_hash_include_fields=content_hash_include_fields,
        content_hash_exclude_fields=content_hash_exclude_fields,
        content_hash_policy_by_version=content_hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )
    components = services_builder.create_batch_processing_components(
        services=services,
        context=context,
        config=processor_config,
        error_classifier=ErrorClassifier(),
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=gold_validator_factory(
            cast("pdr.DataFrameSchema | None", active_gold_schema),
            strict=strict_gold_validation,
        ),
        tracer=effective_tracer,
        lock_validator=lock_validator,
    )
    return record_processor_cls(
        context=context,
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        config=processor_config,
        tracer=effective_tracer,
    )
