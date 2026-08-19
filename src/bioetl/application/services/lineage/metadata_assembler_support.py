"""Shared support helpers for metadata assembler services."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.behavior.composite_metadata_helpers import (
    extract_composite_output_ext,
    parse_composite_list,
    parse_composite_status,
    parse_lineage_created_at,
    summarize_composite_cv_dq,
)
from bioetl.domain.behavior.dataset_content_identity import (
    build_dataset_content_hash,
)
from bioetl.domain.models.metadata import DQSummary

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from bioetl.domain.models.metadata import (
        CompositeOutputExt,
        PipelineMetadata,
        RuntimeMetadata,
    )
    from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput
    from bioetl.domain.types.dq_contracts import DQRuleProvenance
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
    from bioetl.domain.value_objects.run_context import RunContext


class RuntimeMetadataBuilderProtocol(Protocol):
    """Callable protocol for runtime metadata building."""

    def __call__(
        self,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> RuntimeMetadata: ...


class PipelineMetadataBuilderProtocol(Protocol):
    """Callable protocol for pipeline metadata building."""

    def __call__(self) -> PipelineMetadata: ...


def _stable_unique_text(values: object) -> list[str]:
    """Return unique non-empty text values in content-stable order."""
    if not isinstance(values, (list, tuple, set, frozenset)):
        return []
    normalized = {text for value in values if (text := str(value).strip())}
    return sorted(normalized)


def parse_composite_list_metadata(value: object) -> list[str]:
    """Parse composite list metadata stored as list or stringified list."""
    return parse_composite_list(value)


def parse_composite_status_metadata(value: object) -> dict[str, str]:
    """Parse enrichment status stored as dict or stringified dict."""
    return parse_composite_status(value)


def parse_lineage_created_at_metadata(value: object) -> datetime | None:
    """Parse lineage timestamp from raw metadata payload."""
    return parse_lineage_created_at(value)


def extract_composite_output_extension(
    records: list[dict[str, object]],
    partition_count: int,
    *,
    schema_validation_enabled: bool = False,
    schema_validation_strict: bool | None = None,
    composite_run_id: str | None = None,
    lineage_created_at: datetime | None = None,
) -> CompositeOutputExt | None:
    """Extract composite output metadata from merged Gold records."""
    return extract_composite_output_ext(
        records,
        partition_count=partition_count,
        schema_validation_enabled=schema_validation_enabled,
        schema_validation_strict=schema_validation_strict,
        composite_run_id=composite_run_id,
        lineage_created_at=lineage_created_at,
    )


def resolve_source_batch_ids(input_data: SilverMetadataInput) -> list[str]:
    """Resolve source batch IDs from explicit input or embedded records."""
    if input_data.source_batch_ids is not None:
        return _stable_unique_text(input_data.source_batch_ids)

    records = input_data.records or []
    ids = {
        str(record["_source_batch_id"])
        for record in records
        if record.get("_source_batch_id")
    }
    return sorted(ids)


def resolve_bronze_paths(input_data: SilverMetadataInput) -> list[str]:
    """Extract Bronze relative paths when lineage refs are provided."""
    if input_data.bronze_refs is None:
        return []
    bronze_refs = cast("list[BronzeWriteResult]", input_data.bronze_refs)
    return sorted({ref.relative_path for ref in bronze_refs if ref.relative_path})


def resolve_transform_metadata(
    *,
    run_context: RunContext,
    transform_version: str | None,
    transform_steps: Sequence[str] | None,
) -> tuple[str, list[str]]:
    """Resolve transform metadata using input override or run context defaults."""
    resolved_version = transform_version or run_context.transform_version or ""
    resolved_steps = list(transform_steps or run_context.transform_steps)
    return resolved_version, resolved_steps


def resolve_record_count(
    *,
    records: list[dict[str, object]] | None,
    total_records: int | None,
) -> int:
    """Resolve final record count from aggregate total or batch records."""
    if total_records is not None:
        return total_records
    return len(records or [])


def build_silver_dq_summary(
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
                "rule_provenance": normalize_rule_provenance_entries(
                    input_data.dq_rule_provenance
                )
            }
        )
    return augment_dq_summary_with_composite_cv(
        dq_summary=dq_summary,
        records=input_data.records or [],
        contract_version=(
            run_context.contract_version if run_context is not None else None
        ),
        dq_report_path=input_data.dq_report_path,
    )


def build_gold_dq_summary(
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
                "rule_provenance": normalize_rule_provenance_entries(
                    input_data.dq_rule_provenance
                )
            }
        )
    return augment_dq_summary_with_composite_cv(
        dq_summary=dq_summary,
        records=input_data.records or [],
        contract_version=run_context.contract_version,
        dq_report_path=input_data.dq_report_path,
    )


def normalize_rule_provenance_entries(
    entries: Sequence[Mapping[str, object] | DQRuleProvenance],
) -> list[dict[str, str | None]]:
    """Normalize provenance objects and dicts into metadata-safe mappings."""
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
        entry_obj = cast("DQRuleProvenance", entry)
        normalized.append(
            {
                "rule_id": entry_obj.rule_id,
                "contract_version": entry_obj.contract_version,
                "severity": entry_obj.severity,
                "disposition": str(entry_obj.disposition),
                "config_path": entry_obj.config_path,
                "report_artifact_path": entry_obj.report_artifact_path,
                "policy_hash": entry_obj.policy_hash,
            }
        )
    return normalized


def coerce_rule_provenance_mappings(value: object) -> list[dict[str, object]]:
    """Coerce untyped provenance payloads into mapping entries only."""
    if not isinstance(value, list):
        return []
    return [
        {str(key): item_value for key, item_value in item.items()}
        for item in value
        if isinstance(item, dict)
    ]


def augment_dq_summary_with_composite_cv(
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

    error_records = max(dq_summary.error_records, int(cv_summary["error_records"]))
    warning_records = max(
        dq_summary.warning_records, int(cv_summary["warning_records"])
    )
    total_records = dq_summary.total_records
    existing_provenance = normalize_rule_provenance_entries(dq_summary.rule_provenance)
    composite_provenance = normalize_rule_provenance_entries(
        coerce_rule_provenance_mappings(cv_summary["rule_provenance"])
    )
    return dq_summary.model_copy(
        update={
            "valid_records": max(total_records - error_records, 0),
            "error_records": error_records,
            "warning_records": warning_records,
            "error_rate": (error_records / total_records) if total_records else 0.0,
            "validation_passed": dq_summary.validation_passed
            and bool(cv_summary["validation_passed"]),
            "rule_provenance": existing_provenance + composite_provenance,
        }
    )


def build_runtime_duration(
    started_at: datetime | None,
    completed_at: datetime | None,
) -> float:
    """Compute operation duration in seconds."""
    if started_at is None or completed_at is None:
        return 0.0
    return (completed_at - started_at).total_seconds()


__all__ = [
    "PipelineMetadataBuilderProtocol",
    "RuntimeMetadataBuilderProtocol",
    "augment_dq_summary_with_composite_cv",
    "build_dataset_content_hash",
    "build_gold_dq_summary",
    "build_runtime_duration",
    "build_silver_dq_summary",
    "coerce_rule_provenance_mappings",
    "extract_composite_output_extension",
    "normalize_rule_provenance_entries",
    "parse_composite_list_metadata",
    "parse_composite_status_metadata",
    "parse_lineage_created_at_metadata",
    "resolve_bronze_paths",
    "resolve_record_count",
    "resolve_source_batch_ids",
    "resolve_transform_metadata",
]
