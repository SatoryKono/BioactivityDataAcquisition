"""Output and lineage builder helpers for metadata assemblers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from bioetl.domain.lineage import DatasetRef
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    CompositeOutputExt,
    DeltaMetrics,
    LineageMetadata,
    SCDMetadata,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput
    from bioetl.domain.value_objects.run_context import RunContext


def build_silver_delta(
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


def build_silver_lineage(
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


def build_silver_artifact_id(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> str:
    """Build the canonical Silver dataset artifact identifier."""
    dataset = DatasetRef(
        layer="silver",
        logical_name=f"{run_context.provider}.{run_context.entity}",
        version=input_data.version_after,
        provider=run_context.provider,
        entity=run_context.entity,
        path=input_data.table_path,
        manifest_id=run_context.manifest_id,
        run_id=str(run_context.run_id),
    )
    return str(dataset.node_id)


def build_gold_lineage(
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


def build_gold_artifact_id(
    *,
    run_context: RunContext,
    input_data: GoldMetadataInput,
) -> str:
    """Build the canonical Gold dataset artifact identifier."""
    dataset = DatasetRef(
        layer="gold",
        logical_name=input_data.table_name,
        provider=run_context.provider,
        entity=run_context.entity,
        path=input_data.table_path,
        manifest_id=run_context.manifest_id,
        run_id=str(run_context.run_id),
    )
    return str(dataset.node_id)


def resolve_gold_source_tables(input_data: GoldMetadataInput) -> dict[str, int]:
    """Resolve Gold lineage source tables from Silver refs."""
    if not input_data.silver_refs:
        return {}
    return {ref.table_name: ref.delta_version for ref in input_data.silver_refs}


def build_gold_scd(input_data: GoldMetadataInput) -> SCDMetadata | None:
    """Build SCD2 metadata when SCD mode and config are available."""
    if input_data.mode != GoldWriteMode.SCD2 or not input_data.scd_config:
        return None
    return SCDMetadata(
        enabled=True,
        effective_date_column=input_data.scd_config.valid_from_col,
        end_date_column=input_data.scd_config.valid_to_col,
        current_flag_column=input_data.scd_config.current_flag_col,
    )


def build_gold_output(
    *,
    run_context: RunContext | None = None,
    input_data: GoldMetadataInput,
    record_count: int,
    composite_ext: CompositeOutputExt | None,
    content_hash: str | None,
) -> BaseOutputMetadata:
    """Build Gold base output metadata."""
    composite_run_id = composite_ext.composite_run_id if composite_ext else None
    return BaseOutputMetadata(
        artifact_id=(
            build_gold_artifact_id(
                run_context=run_context,
                input_data=input_data,
            )
            if run_context is not None
            else None
        ),
        record_count=record_count,
        total_bytes=input_data.total_bytes,
        content_hash=content_hash,
        write_started_at=input_data.started_at,
        write_completed_at=input_data.completed_at,
        composite_run_id=composite_run_id,
    )


__all__ = [
    "build_gold_artifact_id",
    "build_gold_lineage",
    "build_gold_output",
    "build_gold_scd",
    "build_silver_artifact_id",
    "build_silver_delta",
    "build_silver_lineage",
    "resolve_gold_source_tables",
]
