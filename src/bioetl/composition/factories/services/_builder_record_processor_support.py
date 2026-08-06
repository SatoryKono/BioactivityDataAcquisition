"""Injected helper for ServicesBuilder record-processor assembly."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from bioetl.application.core.wiring.runtime import RecordProcessor
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier

if TYPE_CHECKING:
    import pandera as pdr
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import (
        BatchProcessingComponents,
        ContentHashPolicyByVersion,
        GoldFilterCallback,
        GoldTransformCallback,
        PipelineService,
        RecordProcessorConfig,
        TransformCallback,
    )
    from bioetl.application.services.export_lineage.debug_export_service import DebugExportConfig
    from bioetl.domain.composite import ColumnGroupConfig, DataSchemaConfig
    from bioetl.domain.config import DQConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
    from bioetl.domain.ports import (
        GoldValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import (
        GoldSchemaPolicyByVersion,
        GoldSchemaType,
        ScdConfig,
    )


@dataclass(frozen=True, slots=True)
class _RecordProcessorBuildRequest:
    create_batch_processing_components_fn: Callable[..., BatchProcessingComponents]
    services: PipelineService
    context: PipelineContext
    pipeline_name: str
    provider: str
    entity_type: str
    silver_schema: pa.Schema | None
    gold_schema: GoldSchemaType
    dq_config: DQConfig | None
    data_schema: DataSchemaConfig | None
    primary_keys: tuple[str, ...] | list[str]
    silver_table: str
    gold_table: str | None
    silver_write_mode: SilverWriteMode
    gold_write_mode: GoldWriteMode
    on_schema_mismatch: Literal["error", "evolve", "ignore"]
    transform_callback: TransformCallback
    gold_filter_callback: GoldFilterCallback
    gold_transform_callback: GoldTransformCallback
    tracer: TracingPort | None
    strict_gold_validation: bool
    lock_validator: Callable[[], Awaitable[bool]] | None
    column_groups: tuple[ColumnGroupConfig, ...]
    scd_config: ScdConfig | None
    content_hash_policy_authoritative: bool
    content_hash_include_fields: frozenset[str]
    content_hash_exclude_fields: frozenset[str]
    content_hash_policy_by_version: ContentHashPolicyByVersion | None
    gold_schema_policy_by_version: GoldSchemaPolicyByVersion | None
    record_processor_config_cls: type[RecordProcessorConfig]
    table_config_cls: type[TableConfig]
    gold_validator_factory: Callable[..., GoldValidatorPort]
    record_processor_cls: type[RecordProcessor]
    debug_export_config: DebugExportConfig | None = None


def create_record_processor_impl(
    *,
    request: _RecordProcessorBuildRequest,
) -> RecordProcessor:
    """Build a RecordProcessor using constructors injected from the public module."""
    effective_tracer = request.tracer or request.services.tracing
    active_gold_schema = (
        request.gold_schema_policy_by_version.active_schema
        if request.gold_schema_policy_by_version is not None
        else request.gold_schema
    )
    processor_config = request.record_processor_config_cls(
        pipeline_name=request.pipeline_name,
        provider=request.provider,
        entity_type=request.entity_type,
        silver_schema=request.silver_schema,
        gold_schema=request.gold_schema,
        dq_config=request.dq_config,
        data_schema=request.data_schema,
        table_config=request.table_config_cls(
            primary_keys=tuple(request.primary_keys),
            silver_table=request.silver_table,
            gold_table=request.gold_table,
            silver_write_mode=request.silver_write_mode,
            gold_write_mode=request.gold_write_mode,
            on_schema_mismatch=request.on_schema_mismatch,
        ),
        column_groups=request.column_groups,
        scd_config=request.scd_config,
        content_hash_policy_authoritative=request.content_hash_policy_authoritative,
        content_hash_include_fields=request.content_hash_include_fields,
        content_hash_exclude_fields=request.content_hash_exclude_fields,
        content_hash_policy_by_version=request.content_hash_policy_by_version,
        gold_schema_policy_by_version=request.gold_schema_policy_by_version,
        debug_export_config=request.debug_export_config,
    )
    components = request.create_batch_processing_components_fn(
        services=request.services,
        context=request.context,
        config=processor_config,
        error_classifier=ErrorClassifier(),
        transform_callback=request.transform_callback,
        gold_filter_callback=request.gold_filter_callback,
        gold_transform_callback=request.gold_transform_callback,
        gold_validator=request.gold_validator_factory(
            cast("pdr.DataFrameSchema | None", active_gold_schema),
            strict=request.strict_gold_validation,
            dq_config=request.dq_config,
        ),
        tracer=effective_tracer,
        lock_validator=request.lock_validator,
    )
    return request.record_processor_cls(
        context=request.context,
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        config=processor_config,
        tracer=effective_tracer,
    )
