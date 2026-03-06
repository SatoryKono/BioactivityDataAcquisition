"""Assembly helpers for Silver/Gold metadata sidecar models.

Extracts scenario-specific metadata assembly from MetadataCoordinator so
coordinator methods stay orchestration-focused.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol, cast

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    CompositeOutputExt,
    CompositeSchemaValidationMetadata,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    GoldMetadata,
    GoldOutputExt,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    SCDMetadata,
    SilverMetadata,
    SilverOutputExt,
)
from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput
from bioetl.domain.services.schema_metadata_extractor import extract_schema_metadata
from bioetl.domain.value_objects.run_context import RunContext

if TYPE_CHECKING:
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics


class RuntimeMetadataProtocol(Protocol):
    """Callable protocol for runtime metadata construction."""

    def __call__(
        self,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> RuntimeMetadata: ...


class PipelineMetadataProtocol(Protocol):
    """Callable protocol for pipeline metadata construction."""

    def __call__(self) -> PipelineMetadata: ...


def _parse_composite_list(value: object) -> list[str]:
    """Parse composite list metadata stored as list or stringified list."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def _parse_composite_status(value: object) -> dict[str, str]:
    """Parse enrichment status stored as dict or stringified dict."""
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    return {}


def _extract_composite_output_ext(
    records: list[dict[str, object]],
    partition_count: int,
    *,
    schema_validation_enabled: bool = False,
    schema_validation_strict: bool | None = None,
) -> CompositeOutputExt | None:
    """Extract composite output metadata from merged Gold records."""
    if not records:
        return None

    sample = records[0]
    composite_run_id = sample.get("_composite_run_id")
    lineage_raw = sample.get("_lineage_created_at")
    lineage_created_at = _parse_lineage_created_at(lineage_raw)

    has_composite_fields = any(key.startswith("_composite_") for key in sample)
    has_lineage_fields = "_source_providers" in sample or "_enrichment_status" in sample
    if not has_composite_fields and not has_lineage_fields:
        return None

    return CompositeOutputExt(
        partition_count=partition_count,
        composite_run_id=(
            str(composite_run_id) if composite_run_id is not None else None
        ),
        source_providers=_parse_composite_list(sample.get("_source_providers")),
        enrichment_status=_parse_composite_status(sample.get("_enrichment_status")),
        lineage_created_at=lineage_created_at,
        schema_validation=CompositeSchemaValidationMetadata(
            enabled=schema_validation_enabled,
            strict=schema_validation_strict,
            status="passed" if schema_validation_enabled else "not_run",
        ),
    )


def _parse_lineage_created_at(value: object) -> datetime | None:
    """Parse lineage timestamp from raw metadata payload."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _resolve_source_batch_ids(input_data: SilverMetadataInput) -> list[str]:
    """Resolve source batch IDs from explicit input or embedded records."""
    if input_data.source_batch_ids is not None:
        return input_data.source_batch_ids

    records = input_data.records or []
    ids = {
        str(record["_source_batch_id"])
        for record in records
        if record.get("_source_batch_id")
    }
    return list(ids)


def _resolve_bronze_paths(input_data: SilverMetadataInput) -> list[str]:
    """Extract Bronze relative paths when lineage refs are provided."""
    if input_data.bronze_refs is None:
        return []
    bronze_refs = cast("list[BronzeWriteResult]", input_data.bronze_refs)
    return [ref.relative_path for ref in bronze_refs]


def _resolve_transform_metadata(
    *,
    run_context: RunContext,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | None,
) -> tuple[str, list[str]]:
    """Resolve transform metadata using input override or run context defaults."""
    resolved_version = transform_version or run_context.transform_version
    resolved_steps = list(transform_steps or run_context.transform_steps)
    return resolved_version, resolved_steps


def _resolve_record_count(
    *,
    records: list[dict[str, object]] | None,
    total_records: int | None,
) -> int:
    """Resolve final record count from aggregate total or batch records."""
    if total_records is not None:
        return total_records
    return len(records or [])


def _build_silver_delta(
    input_data: SilverMetadataInput, rows_inserted: int
) -> DeltaMetrics:
    """Build Silver Delta metrics payload."""
    operation_map: dict[SilverWriteMode, Literal["merge", "overwrite", "append"]] = {
        SilverWriteMode.MERGE: "merge",
        SilverWriteMode.APPEND: "append",
        SilverWriteMode.DELETE: "overwrite",
    }
    mode = cast("SilverWriteMode", input_data.mode)
    return DeltaMetrics(
        table_path=input_data.table_path,
        operation=operation_map[mode],
        primary_key=input_data.primary_keys,
        partition_by=input_data.partition_by or [],
        version_after=input_data.version_after,
        rows_inserted=rows_inserted,
    )


def _build_silver_dq_summary(
    input_data: SilverMetadataInput, record_count: int
) -> DQSummary:
    """Build DQ summary using optional batch metrics and provenance."""
    dq_summary = DQSummary(total_records=record_count, valid_records=record_count)
    if input_data.dq_metrics is not None:
        dq_metrics = cast("BatchDQMetrics", input_data.dq_metrics)
        dq_summary = dq_metrics.to_dq_summary()
    if input_data.dq_rule_provenance:
        dq_summary = dq_summary.model_copy(
            update={"rule_provenance": input_data.dq_rule_provenance}
        )
    return dq_summary


def _build_runtime_duration(
    started_at: datetime | None,
    completed_at: datetime | None,
) -> float:
    """Compute operation duration in seconds."""
    if started_at is None or completed_at is None:
        return 0.0
    return (completed_at - started_at).total_seconds()


def _build_silver_lineage(
    *,
    source_batch_ids: list[str],
    bronze_paths: list[str],
    transform_version: str,
    transform_steps: list[str],
) -> LineageMetadata:
    """Build lineage metadata for Silver writes."""
    return LineageMetadata(
        source_batch_ids=source_batch_ids,
        bronze_paths=bronze_paths,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )


def _build_gold_lineage(
    *,
    source_tables: dict[str, int],
    transform_version: str,
    transform_steps: list[str],
) -> LineageMetadata:
    """Build lineage metadata for Gold writes."""
    return LineageMetadata(
        source_tables=source_tables,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )


def _resolve_gold_source_tables(input_data: GoldMetadataInput) -> dict[str, int]:
    """Resolve Gold lineage source tables from Silver refs."""
    if not input_data.silver_refs:
        return {}
    return {ref.table_name: ref.delta_version for ref in input_data.silver_refs}


def _build_gold_scd(input_data: GoldMetadataInput) -> SCDMetadata | None:
    """Build SCD2 metadata when SCD mode and config are available."""
    if input_data.mode != GoldWriteMode.SCD2 or not input_data.scd_config:
        return None
    return SCDMetadata(
        enabled=True,
        effective_date_column=input_data.scd_config.get(
            "valid_from_col", "_valid_from"
        ),
        end_date_column=input_data.scd_config.get("valid_to_col", "_valid_to"),
        current_flag_column=input_data.scd_config.get(
            "current_flag_col", "_is_current"
        ),
    )


def _build_gold_output(
    *,
    input_data: GoldMetadataInput,
    record_count: int,
    composite_ext: CompositeOutputExt | None,
) -> BaseOutputMetadata:
    """Build Gold base output metadata."""
    composite_run_id = composite_ext.composite_run_id if composite_ext else None
    return BaseOutputMetadata(
        record_count=record_count,
        total_bytes=input_data.total_bytes,
        write_started_at=input_data.started_at,
        write_completed_at=input_data.completed_at,
        composite_run_id=composite_run_id,
    )


@dataclass(slots=True, frozen=True)
class SilverMetadataService:
    """Assemble Silver metadata from scenario inputs and shared context."""

    run_context: RunContext
    runtime_metadata_factory: RuntimeMetadataProtocol
    pipeline_metadata_factory: PipelineMetadataProtocol
    environment_metadata: EnvironmentMetadata

    def assemble(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Build complete Silver metadata payload."""
        if not input_data.records and input_data.total_records is None:
            raise ValueError("Cannot create Silver metadata without records")

        source_batch_ids = _resolve_source_batch_ids(input_data)
        bronze_paths = _resolve_bronze_paths(input_data)
        transform_version, transform_steps = _resolve_transform_metadata(
            run_context=self.run_context,
            transform_version=input_data.transform_version,
            transform_steps=input_data.transform_steps,
        )
        lineage = _build_silver_lineage(
            source_batch_ids=source_batch_ids,
            bronze_paths=bronze_paths,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        record_count = _resolve_record_count(
            records=input_data.records,
            total_records=input_data.total_records,
        )
        delta = _build_silver_delta(input_data=input_data, rows_inserted=record_count)
        dq_summary = _build_silver_dq_summary(
            input_data=input_data, record_count=record_count
        )
        duration_seconds = _build_runtime_duration(
            input_data.started_at, input_data.completed_at
        )

        output = BaseOutputMetadata(
            record_count=record_count,
            total_bytes=input_data.total_bytes,
            write_started_at=input_data.started_at,
            write_completed_at=input_data.completed_at,
        )
        output_ext = SilverOutputExt(
            delta_version_before=input_data.version_before,
            delta_version_after=input_data.version_after,
        )

        return SilverMetadata(
            runtime=self.runtime_metadata_factory(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration_seconds,
            ),
            pipeline=self.pipeline_metadata_factory(),
            lineage=lineage,
            delta=delta,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            environment=self.environment_metadata,
            dq_report_path=input_data.dq_report_path,
            governance=input_data.governance,
        )


@dataclass(slots=True, frozen=True)
class GoldMetadataService:
    """Assemble Gold metadata from scenario inputs and shared context."""

    run_context: RunContext
    runtime_metadata_factory: RuntimeMetadataProtocol
    pipeline_metadata_factory: PipelineMetadataProtocol
    environment_metadata: EnvironmentMetadata

    def assemble(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Build complete Gold metadata payload."""
        if not input_data.records and input_data.total_records is None:
            raise ValueError("Cannot create Gold metadata without records")

        source_tables = _resolve_gold_source_tables(input_data)
        transform_version, transform_steps = _resolve_transform_metadata(
            run_context=self.run_context,
            transform_version=input_data.transform_version,
            transform_steps=input_data.transform_steps,
        )
        lineage = _build_gold_lineage(
            source_tables=source_tables,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        record_count = _resolve_record_count(
            records=input_data.records,
            total_records=input_data.total_records,
        )
        dq_summary = DQSummary(total_records=record_count, valid_records=record_count)

        records = input_data.records or []
        composite_ext = _extract_composite_output_ext(
            records=records,
            partition_count=input_data.partition_count,
            schema_validation_enabled=input_data.schema_validation_enabled,
            schema_validation_strict=input_data.schema_validation_strict,
        )
        output = _build_gold_output(
            input_data=input_data,
            record_count=record_count,
            composite_ext=composite_ext,
        )
        output_ext = composite_ext or GoldOutputExt(
            partition_count=input_data.partition_count
        )
        scd = _build_gold_scd(input_data)

        schema_info = extract_schema_metadata(input_data.gold_schema)
        return GoldMetadata(
            runtime=self.runtime_metadata_factory(
                completed_at=input_data.completed_at,
                duration_seconds=0.0,
            ),
            pipeline=self.pipeline_metadata_factory(),
            lineage=lineage,
            schema=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            scd=scd,
            environment=self.environment_metadata,
            dq_report_path=input_data.dq_report_path,
            governance=input_data.governance,
        )


# Backward-compatible aliases for pre-refactor import paths.
SilverMetadataAssembler = SilverMetadataService
GoldMetadataAssembler = GoldMetadataService
RuntimeMetadataFactory = RuntimeMetadataProtocol
PipelineMetadataFactory = PipelineMetadataProtocol

__all__ = [
    "GoldMetadataAssembler",
    "GoldMetadataService",
    "PipelineMetadataFactory",
    "PipelineMetadataProtocol",
    "RuntimeMetadataFactory",
    "RuntimeMetadataProtocol",
    "SilverMetadataAssembler",
    "SilverMetadataService",
]
