"""Helper functions and protocols for metadata assembly services."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol, cast

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    CompositeOutputExt,
    DeltaMetrics,
    DQSummary,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    SCDMetadata,
)
from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput
from bioetl.domain.services.composite_metadata_helpers import (
    extract_composite_output_ext,
    parse_composite_list,
    parse_composite_status,
    parse_lineage_created_at,
    summarize_composite_cv_dq,
)
from bioetl.domain.value_objects.run_context import RunContext

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.types.dq_contracts import DQRuleProvenance
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
    return parse_composite_list(value)


def _parse_composite_status(value: object) -> dict[str, str]:
    """Parse enrichment status stored as dict or stringified dict."""
    return parse_composite_status(value)


def _parse_lineage_created_at(value: object) -> datetime | None:
    """Parse lineage timestamp from raw metadata payload."""
    return parse_lineage_created_at(value)


def _extract_composite_output_ext(
    records: list[dict[str, object]],
    partition_count: int,
    *,
    schema_validation_enabled: bool = False,
    schema_validation_strict: bool | None = None,
) -> CompositeOutputExt | None:
    """Extract composite output metadata from merged Gold records."""
    return extract_composite_output_ext(
        records,
        partition_count=partition_count,
        schema_validation_enabled=schema_validation_enabled,
        schema_validation_strict=schema_validation_strict,
    )


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
    resolved_version = transform_version or run_context.transform_version or ""
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
    input_data: SilverMetadataInput,
    record_count: int,
    *,
    run_context: RunContext | None = None,
) -> DQSummary:
    """Build DQ summary using optional batch metrics and provenance."""
    dq_summary = DQSummary(total_records=record_count, valid_records=record_count)
    if input_data.dq_metrics is not None:
        dq_metrics = cast("BatchDQMetrics", input_data.dq_metrics)
        dq_summary = dq_metrics.to_dq_summary()
    if input_data.dq_rule_provenance:
        dq_summary = dq_summary.model_copy(
            update={
                "rule_provenance": _normalize_rule_provenance_entries(
                    input_data.dq_rule_provenance
                )
            }
        )
    return _augment_dq_summary_with_composite_cv(
        dq_summary=dq_summary,
        records=input_data.records or [],
        contract_version=(
            run_context.contract_version if run_context is not None else None
        ),
        dq_report_path=input_data.dq_report_path,
    )


def _build_gold_dq_summary(
    *,
    input_data: GoldMetadataInput,
    record_count: int,
    run_context: RunContext,
) -> DQSummary:
    """Build Gold DQ summary including explicit and composite CV provenance."""
    dq_summary = DQSummary(total_records=record_count, valid_records=record_count)
    if input_data.dq_rule_provenance:
        dq_summary = dq_summary.model_copy(
            update={
                "rule_provenance": _normalize_rule_provenance_entries(
                    input_data.dq_rule_provenance
                )
            }
        )
    return _augment_dq_summary_with_composite_cv(
        dq_summary=dq_summary,
        records=input_data.records or [],
        contract_version=run_context.contract_version,
        dq_report_path=input_data.dq_report_path,
    )


def _normalize_rule_provenance_entries(
    entries: Sequence[dict[str, object] | DQRuleProvenance],
) -> list[dict[str, str | None]]:
    """Normalize provenance objects/dicts into metadata-safe mappings."""
    normalized: list[dict[str, str | None]] = []
    for entry in entries:
        if isinstance(entry, dict):
            normalized.append(
                {
                    str(key): None if value is None else str(value)
                    for key, value in entry.items()
                }
            )
            continue
        normalized.append(
            {
                "rule_id": entry.rule_id,
                "contract_version": entry.contract_version,
                "severity": entry.severity,
                "disposition": str(entry.disposition),
                "config_path": entry.config_path,
                "report_artifact_path": entry.report_artifact_path,
                "policy_hash": entry.policy_hash,
            }
        )
    return normalized


def _augment_dq_summary_with_composite_cv(
    *,
    dq_summary: DQSummary,
    records: list[dict[str, object]],
    contract_version: str | None,
    dq_report_path: str | None,
) -> DQSummary:
    """Merge composite cross-validation markers into DQ summary semantics."""
    cv_summary = summarize_composite_cv_dq(
        records,
        contract_version=contract_version,
        report_artifact_path=dq_report_path,
    )
    if not cv_summary["has_signal"]:
        return dq_summary

    error_records = int(cv_summary["error_records"])
    warning_records = int(cv_summary["warning_records"])
    total_records = dq_summary.total_records
    existing_provenance = _normalize_rule_provenance_entries(dq_summary.rule_provenance)
    composite_provenance = cast(
        "list[dict[str, str | None]]", cv_summary["rule_provenance"]
    )
    return dq_summary.model_copy(
        update={
            "valid_records": max(total_records - error_records, 0),
            "error_records": max(dq_summary.error_records, error_records),
            "warning_records": max(dq_summary.warning_records, warning_records),
            "error_rate": (error_records / total_records) if total_records else 0.0,
            "validation_passed": dq_summary.validation_passed
            and bool(cv_summary["validation_passed"]),
            "rule_provenance": existing_provenance + composite_provenance,
        }
    )


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
        effective_date_column=input_data.scd_config.valid_from_col,
        end_date_column=input_data.scd_config.valid_to_col,
        current_flag_column=input_data.scd_config.current_flag_col,
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


__all__ = [
    "PipelineMetadataProtocol",
    "RuntimeMetadataProtocol",
    "_build_gold_dq_summary",
    "_build_gold_lineage",
    "_build_gold_output",
    "_build_gold_scd",
    "_build_runtime_duration",
    "_build_silver_delta",
    "_build_silver_dq_summary",
    "_build_silver_lineage",
    "_extract_composite_output_ext",
    "_resolve_bronze_paths",
    "_resolve_gold_source_tables",
    "_resolve_record_count",
    "_resolve_source_batch_ids",
    "_resolve_transform_metadata",
]
