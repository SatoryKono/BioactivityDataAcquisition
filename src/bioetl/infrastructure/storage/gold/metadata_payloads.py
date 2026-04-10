"""Pure metadata payload builders for Gold writer flows."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.models.metadata import GoldMetadata
from bioetl.domain.ports import GoldMetadataInput, MetadataCoordinatorPort
from bioetl.domain.types import GoldRecord, RunID, ScdConfig
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.metadata.builder_base import (
    _resolve_records_metadata_timestamp,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

__all__ = [
    "build_gold_merged_metadata_input",
    "build_gold_metadata_input",
    "build_gold_metadata_payload",
    "build_gold_metadata_via_coordinator",
    "build_gold_metadata_via_fallback",
]


def build_gold_metadata_input(
    *,
    table_path: str,
    table_name: str,
    records: list[GoldRecord],
    mode: GoldWriteMode,
    scd_config: ScdConfig | None,
    completed_at: datetime | None,
    silver_refs: list[SilverWriteResult] | None,
    gold_schema: object | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...],
) -> GoldMetadataInput:
    """Build the coordinator-facing Gold metadata input payload."""
    from bioetl.domain.ports import SilverRef

    converted_refs = (
        [
            SilverRef(
                table_name=ref.table_name,
                table_path=ref.table_path,
                delta_version=ref.delta_version,
            )
            for ref in silver_refs
        ]
        if silver_refs
        else None
    )
    return GoldMetadataInput(
        table_path=table_path,
        table_name=table_name,
        records=records,
        mode=mode,
        scd_config=scd_config,
        completed_at=completed_at,
        silver_refs=converted_refs,
        transform_version=transform_version,
        transform_steps=transform_steps,
        gold_schema=gold_schema,
    )


def build_gold_merged_metadata_input(
    *,
    table_path: str,
    table_name: str,
    records: list[GoldRecord],
    schema: DataFrameSchema | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...],
) -> GoldMetadataInput:
    """Build merged-table Gold metadata input payload."""
    return GoldMetadataInput(
        table_path=table_path,
        table_name=table_name,
        records=records,
        mode=GoldWriteMode.OVERWRITE,
        completed_at=_extract_completed_at(records),
        transform_version=transform_version,
        transform_steps=transform_steps,
        total_bytes=0,
        partition_count=0,
        schema_validation_enabled=schema is not None,
        schema_validation_strict=True if schema is not None else None,
    )


def _extract_completed_at(records: list[GoldRecord]) -> datetime | None:
    """Extract canonical merged-write completion timestamp from record metadata."""
    return cast(datetime | None, _resolve_records_metadata_timestamp(records))


def build_gold_metadata_payload(
    *,
    coordinator: MetadataCoordinatorPort | None,
    table_path: str,
    table_name: str,
    records: list[GoldRecord],
    mode: GoldWriteMode,
    scd_config: ScdConfig | None,
    ingestion_ts: datetime | None,
    run_id: RunID | None,
    silver_refs: list[SilverWriteResult] | None,
    gold_schema: object | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...],
) -> GoldMetadata:
    """Build standard Gold metadata via the coordinator contract only."""
    if coordinator is None:
        raise RuntimeError(
            "MetadataCoordinator is required for build_gold_metadata_payload: "
            f"table_name={table_name}, table_path={table_path}"
        )
    return build_gold_metadata_via_coordinator(
        coordinator=coordinator,
        table_path=table_path,
        table_name=table_name,
        records=records,
        mode=mode,
        scd_config=scd_config,
        completed_at=ingestion_ts,
        silver_refs=silver_refs,
        gold_schema=gold_schema,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )


def build_gold_metadata_via_coordinator(
    *,
    coordinator: MetadataCoordinatorPort,
    table_path: str,
    table_name: str,
    records: list[GoldRecord],
    mode: GoldWriteMode,
    scd_config: ScdConfig | None,
    completed_at: datetime | None,
    silver_refs: list[SilverWriteResult] | None,
    gold_schema: object | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...],
) -> GoldMetadata:
    """Create Gold metadata using the configured coordinator contract."""
    return coordinator.create_gold_metadata(
        build_gold_metadata_input(
            table_path=table_path,
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            completed_at=completed_at,
            silver_refs=silver_refs,
            gold_schema=gold_schema,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )
    )


def build_gold_metadata_via_fallback(
    *,
    table_name: str,
    records: list[GoldRecord],
    mode: GoldWriteMode,
    scd_config: ScdConfig | None,
    ingestion_ts: datetime | None,
    run_id: RunID | None,
    silver_refs: list[SilverWriteResult] | None,
    gold_schema: object | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...],
) -> GoldMetadata:
    """Create Gold metadata via the legacy fallback metadata builder."""
    from bioetl.infrastructure.storage.metadata_builder import GoldMetadataBuilder

    builder = GoldMetadataBuilder(
        transform_version=transform_version,
        transform_steps=transform_steps,
    )
    return builder.build_fallback_metadata(
        table_name=table_name,
        records=records,
        mode=mode,
        scd_config=scd_config,
        ingestion_ts=ingestion_ts,
        run_id=run_id,
        silver_refs=silver_refs,
        gold_schema=gold_schema,
    )
