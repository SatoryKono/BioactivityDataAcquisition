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

__all__ = ["GoldMetadataAssembler", "SilverMetadataAssembler"]


class RuntimeMetadataFactory(Protocol):
    """Callable protocol for runtime metadata construction."""

    def __call__(
        self,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> RuntimeMetadata: ...


class PipelineMetadataFactory(Protocol):
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
    lineage_created_at: datetime | None = None
    if isinstance(lineage_raw, str):
        try:
            lineage_created_at = datetime.fromisoformat(lineage_raw)
        except ValueError:
            lineage_created_at = None

    has_composite_fields = any(key.startswith("_composite_") for key in sample)
    has_lineage_fields = "_source_providers" in sample or "_enrichment_status" in sample
    if not has_composite_fields and not has_lineage_fields:
        return None

    return CompositeOutputExt(
        partition_count=partition_count,
        composite_run_id=str(composite_run_id)
        if composite_run_id is not None
        else None,
        source_providers=_parse_composite_list(sample.get("_source_providers")),
        enrichment_status=_parse_composite_status(sample.get("_enrichment_status")),
        lineage_created_at=lineage_created_at,
        schema_validation=CompositeSchemaValidationMetadata(
            enabled=schema_validation_enabled,
            strict=schema_validation_strict,
            status="passed" if schema_validation_enabled else "not_run",
        ),
    )


@dataclass(slots=True, frozen=True)
class SilverMetadataAssembler:
    """Assemble Silver metadata from scenario inputs and shared context."""

    run_context: RunContext
    runtime_metadata_factory: RuntimeMetadataFactory
    pipeline_metadata_factory: PipelineMetadataFactory
    environment_metadata: EnvironmentMetadata

    def assemble(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Build complete Silver metadata payload."""
        if not input_data.records and input_data.total_records is None:
            raise ValueError("Cannot create Silver metadata without records")

        if input_data.source_batch_ids is not None:
            source_batch_ids = input_data.source_batch_ids
        elif input_data.records:
            source_batch_ids = list(
                {
                    record.get("_source_batch_id", "")
                    for record in input_data.records
                    if record.get("_source_batch_id")
                }
            )
        else:
            source_batch_ids = []

        bronze_paths: list[str] = []
        if input_data.bronze_refs:
            bronze_refs = cast("list[BronzeWriteResult]", input_data.bronze_refs)
            bronze_paths = [ref.relative_path for ref in bronze_refs]

        transform_version = (
            input_data.transform_version
            if input_data.transform_version is not None
            else self.run_context.transform_version
        )
        transform_steps = list(
            input_data.transform_steps
            if input_data.transform_steps is not None
            else self.run_context.transform_steps
        )
        lineage = LineageMetadata(
            source_batch_ids=source_batch_ids,
            bronze_paths=bronze_paths,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        operation_map: dict[
            SilverWriteMode, Literal["merge", "overwrite", "append"]
        ] = {
            SilverWriteMode.MERGE: "merge",
            SilverWriteMode.APPEND: "append",
            SilverWriteMode.DELETE: "overwrite",
        }
        rows_inserted = (
            input_data.total_records
            if input_data.total_records is not None
            else len(input_data.records or [])
        )
        mode = cast("SilverWriteMode", input_data.mode)
        delta = DeltaMetrics(
            table_path=input_data.table_path,
            operation=operation_map[mode],
            primary_key=input_data.primary_keys,
            partition_by=input_data.partition_by or [],
            version_after=input_data.version_after,
            rows_inserted=rows_inserted,
        )

        record_count = (
            input_data.total_records
            if input_data.total_records is not None
            else len(input_data.records or [])
        )
        dq_summary = DQSummary(total_records=record_count, valid_records=record_count)
        if input_data.dq_metrics:
            dq_metrics = cast("BatchDQMetrics", input_data.dq_metrics)
            dq_summary = dq_metrics.to_dq_summary()
        if input_data.dq_rule_provenance:
            dq_summary = dq_summary.model_copy(
                update={"rule_provenance": input_data.dq_rule_provenance}
            )

        duration_seconds = (
            (input_data.completed_at - input_data.started_at).total_seconds()
            if input_data.started_at and input_data.completed_at
            else None
        )

        output = BaseOutputMetadata(
            record_count=record_count or 0,
            total_bytes=getattr(input_data, "total_bytes", 0) or 0,
            write_started_at=input_data.started_at,
            write_completed_at=input_data.completed_at,
        )
        output_ext = SilverOutputExt(
            delta_version_before=getattr(input_data, "version_before", None),
            delta_version_after=input_data.version_after,
        )

        return SilverMetadata(
            runtime=self.runtime_metadata_factory(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration_seconds or 0.0,
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
class GoldMetadataAssembler:
    """Assemble Gold metadata from scenario inputs and shared context."""

    run_context: RunContext
    runtime_metadata_factory: RuntimeMetadataFactory
    pipeline_metadata_factory: PipelineMetadataFactory
    environment_metadata: EnvironmentMetadata

    def assemble(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Build complete Gold metadata payload."""
        if not input_data.records and input_data.total_records is None:
            raise ValueError("Cannot create Gold metadata without records")

        source_tables: dict[str, int] = {}
        if input_data.silver_refs:
            source_tables = {
                ref.table_name: ref.delta_version for ref in input_data.silver_refs
            }

        transform_version = (
            input_data.transform_version
            if input_data.transform_version is not None
            else self.run_context.transform_version
        )
        transform_steps = list(
            input_data.transform_steps
            if input_data.transform_steps is not None
            else self.run_context.transform_steps
        )
        lineage = LineageMetadata(
            source_tables=source_tables,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        record_count = (
            input_data.total_records
            if input_data.total_records is not None
            else len(input_data.records or [])
        )
        record_count = record_count or 0
        dq_summary = DQSummary(
            total_records=record_count,
            valid_records=record_count,
        )

        records = input_data.records or []
        partition_count = getattr(input_data, "partition_count", 0)
        composite_ext = _extract_composite_output_ext(
            records=records,
            partition_count=partition_count,
            schema_validation_enabled=getattr(
                input_data, "schema_validation_enabled", False
            ),
            schema_validation_strict=getattr(
                input_data, "schema_validation_strict", None
            ),
        )
        output = BaseOutputMetadata(
            record_count=record_count,
            total_bytes=getattr(input_data, "total_bytes", 0) or 0,
            write_started_at=getattr(input_data, "started_at", None),
            write_completed_at=input_data.completed_at,
            composite_run_id=composite_ext.composite_run_id if composite_ext else None,
        )
        output_ext = composite_ext or GoldOutputExt(partition_count=partition_count)

        scd = None
        if input_data.mode == GoldWriteMode.SCD2 and input_data.scd_config:
            scd = SCDMetadata(
                enabled=True,
                effective_date_column=input_data.scd_config.get(
                    "valid_from_col", "_valid_from"
                ),
                end_date_column=input_data.scd_config.get("valid_to_col", "_valid_to"),
                current_flag_column=input_data.scd_config.get(
                    "current_flag_col", "_is_current"
                ),
            )

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
