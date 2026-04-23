"""Helper functions and protocols for metadata assembly services."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_assembler_support import (
    PipelineMetadataProtocol,
    RuntimeMetadataProtocol,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    augment_dq_summary_with_composite_cv as _augment_dq_summary_with_composite_cv_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_dataset_content_hash as _build_dataset_content_hash_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_gold_dq_summary as _build_gold_dq_summary_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_runtime_duration as _build_runtime_duration_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    build_silver_dq_summary as _build_silver_dq_summary_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    coerce_rule_provenance_mappings as _coerce_rule_provenance_mappings_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    extract_composite_output_extension as _extract_composite_output_extension_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    normalize_rule_provenance_entries as _normalize_rule_provenance_entries_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    parse_composite_list_metadata as _parse_composite_list_metadata,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    parse_composite_status_metadata as _parse_composite_status_metadata,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    parse_lineage_created_at_metadata as _parse_lineage_created_at_metadata,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_bronze_paths as _resolve_bronze_paths_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_record_count as _resolve_record_count_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_source_batch_ids as _resolve_source_batch_ids_support,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    resolve_transform_metadata as _resolve_transform_metadata_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_artifact_id as _build_gold_artifact_id_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_lineage as _build_gold_lineage_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_output as _build_gold_output_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_gold_scd as _build_gold_scd_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_silver_artifact_id as _build_silver_artifact_id_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_silver_delta as _build_silver_delta_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    build_silver_lineage as _build_silver_lineage_support,
)
from bioetl.application.services.lineage.metadata_output_support import (
    resolve_gold_source_tables as _resolve_gold_source_tables_support,
)
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    CompositeOutputExt,
    DeltaMetrics,
    DQSummary,
    LineageMetadata,
    SCDMetadata,
)
from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput
from bioetl.domain.value_objects.run_context import RunContext

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from bioetl.domain.types.dq_contracts import DQRuleProvenance


def _parse_composite_list(value: object) -> list[str]:
    """Parse composite list metadata stored as list or stringified list."""
    return _parse_composite_list_metadata(value)


def _parse_composite_status(value: object) -> dict[str, str]:
    """Parse enrichment status stored as dict or stringified dict."""
    return _parse_composite_status_metadata(value)


def _parse_lineage_created_at(value: object) -> datetime | None:
    """Parse lineage timestamp from raw metadata payload."""
    return _parse_lineage_created_at_metadata(value)


def _extract_composite_output_ext(
    records: list[dict[str, object]],
    partition_count: int,
    *,
    schema_validation_enabled: bool = False,
    schema_validation_strict: bool | None = None,
    composite_run_id: str | None = None,
    lineage_created_at: datetime | None = None,
) -> CompositeOutputExt | None:
    """Extract composite output metadata from merged Gold records."""
    return _extract_composite_output_extension_support(
        records,
        partition_count=partition_count,
        schema_validation_enabled=schema_validation_enabled,
        schema_validation_strict=schema_validation_strict,
        composite_run_id=composite_run_id,
        lineage_created_at=lineage_created_at,
    )


def _resolve_source_batch_ids(input_data: SilverMetadataInput) -> list[str]:
    """Resolve source batch IDs from explicit input or embedded records."""
    return _resolve_source_batch_ids_support(input_data)


def _resolve_bronze_paths(input_data: SilverMetadataInput) -> list[str]:
    """Extract Bronze relative paths when lineage refs are provided."""
    return _resolve_bronze_paths_support(input_data)


def _resolve_transform_metadata(
    *,
    run_context: RunContext,
    transform_version: str | None,
    transform_steps: Sequence[str] | None,
) -> tuple[str, list[str]]:
    """Resolve transform metadata using input override or run context defaults."""
    return _resolve_transform_metadata_support(
        run_context=run_context,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )


def _resolve_record_count(
    *,
    records: list[dict[str, object]] | None,
    total_records: int | None,
) -> int:
    """Resolve final record count from aggregate total or batch records."""
    return _resolve_record_count_support(records=records, total_records=total_records)


def _build_silver_delta(
    input_data: SilverMetadataInput, rows_inserted: int
) -> DeltaMetrics:
    """Build Silver Delta metrics payload."""
    return _build_silver_delta_support(input_data, rows_inserted)


def _build_silver_dq_summary(
    input_data: SilverMetadataInput,
    record_count: int,
    *,
    run_context: RunContext | None = None,
) -> DQSummary:
    """Build DQ summary using optional batch metrics and provenance."""
    return _build_silver_dq_summary_support(
        input_data,
        record_count,
        run_context=run_context,
    )


def _build_gold_dq_summary(
    *,
    input_data: GoldMetadataInput,
    record_count: int,
    run_context: RunContext,
) -> DQSummary:
    """Build Gold DQ summary including explicit and composite CV provenance."""
    return _build_gold_dq_summary_support(
        input_data=input_data,
        record_count=record_count,
        run_context=run_context,
    )


def _normalize_rule_provenance_entries(
    entries: Sequence[Mapping[str, object] | DQRuleProvenance],
) -> list[dict[str, str | None]]:
    """Normalize provenance objects/dicts into metadata-safe mappings."""
    return _normalize_rule_provenance_entries_support(entries)


def _coerce_rule_provenance_mappings(value: object) -> list[dict[str, object]]:
    """Coerce untyped provenance payloads into mapping entries only."""
    return _coerce_rule_provenance_mappings_support(value)


def _augment_dq_summary_with_composite_cv(
    *,
    dq_summary: DQSummary,
    records: list[dict[str, object]],
    contract_version: str | None,
    dq_report_path: str | None,
) -> DQSummary:
    """Merge composite cross-validation markers into DQ summary semantics."""
    return _augment_dq_summary_with_composite_cv_support(
        dq_summary=dq_summary,
        records=records,
        contract_version=contract_version,
        dq_report_path=dq_report_path,
    )


def _build_runtime_duration(
    started_at: datetime | None,
    completed_at: datetime | None,
) -> float:
    """Compute operation duration in seconds."""
    return _build_runtime_duration_support(started_at, completed_at)


def _build_silver_lineage(
    *,
    source_batch_ids: list[str],
    bronze_paths: list[str],
    transform_version: str,
    transform_steps: list[str],
) -> LineageMetadata:
    """Build lineage metadata for Silver writes."""
    return _build_silver_lineage_support(
        source_batch_ids=source_batch_ids,
        bronze_paths=bronze_paths,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )


def _build_silver_artifact_id(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> str:
    """Build the canonical Silver dataset artifact identifier."""
    return _build_silver_artifact_id_support(
        run_context=run_context,
        input_data=input_data,
    )


def _build_dataset_content_hash(
    *,
    provider: str,
    records: Sequence[Mapping[str, object]] | None,
) -> str | None:
    """Build an order-insensitive dataset-level content hash for one sidecar.

    Dataset-level sidecar identity must remain semantic-only. Occurrence-scoped
    runtime anchors such as run identifiers and write timestamps are excluded
    even when they appear as non-underscored keys in one record payload.
    """
    return _build_dataset_content_hash_support(provider=provider, records=records)


def _build_gold_lineage(
    *,
    source_tables: dict[str, int],
    transform_version: str,
    transform_steps: list[str],
) -> LineageMetadata:
    """Build lineage metadata for Gold writes."""
    return _build_gold_lineage_support(
        source_tables=source_tables,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )


def _build_gold_artifact_id(
    *,
    run_context: RunContext,
    input_data: GoldMetadataInput,
) -> str:
    """Build the canonical Gold dataset artifact identifier."""
    return _build_gold_artifact_id_support(
        run_context=run_context,
        input_data=input_data,
    )


def _resolve_gold_source_tables(input_data: GoldMetadataInput) -> dict[str, int]:
    """Resolve Gold lineage source tables from Silver refs."""
    return _resolve_gold_source_tables_support(input_data)


def _build_gold_scd(input_data: GoldMetadataInput) -> SCDMetadata | None:
    """Build SCD2 metadata when SCD mode and config are available."""
    return _build_gold_scd_support(input_data)


def _build_gold_output(
    *,
    run_context: RunContext | None = None,
    input_data: GoldMetadataInput,
    record_count: int,
    composite_ext: CompositeOutputExt | None,
) -> BaseOutputMetadata:
    """Build Gold base output metadata."""
    return _build_gold_output_support(
        run_context=run_context,
        input_data=input_data,
        record_count=record_count,
        composite_ext=composite_ext,
        content_hash=(
            _build_dataset_content_hash(
                provider=run_context.provider,
                records=input_data.records,
            )
            if run_context is not None
            else None
        ),
    )


__all__ = [
    "PipelineMetadataProtocol",
    "RuntimeMetadataProtocol",
    "_build_dataset_content_hash",
    "_build_gold_dq_summary",
    "_build_gold_lineage",
    "_build_gold_output",
    "_build_gold_scd",
    "_build_runtime_duration",
    "_build_silver_delta",
    "_build_silver_dq_summary",
    "_build_silver_lineage",
    "_extract_composite_output_ext",
    "_parse_composite_list",
    "_parse_composite_status",
    "_parse_lineage_created_at",
    "_resolve_bronze_paths",
    "_resolve_gold_source_tables",
    "_resolve_record_count",
    "_resolve_source_batch_ids",
    "_resolve_transform_metadata",
]
