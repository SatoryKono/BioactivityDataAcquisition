"""Pure metadata payload builders for Gold writer flows."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.models.metadata import GoldMetadata
from bioetl.domain.ports import GoldMetadataInput, MetadataCoordinatorPort
from bioetl.domain.types import GoldRecord, RunID, ScdConfig
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.lineage_persistence import (
    resolve_metadata_and_lineage_fragment,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

__all__ = [
    "build_gold_merged_metadata_input",
    "build_gold_metadata_input",
    "build_gold_metadata_payload",
    "build_gold_metadata_via_coordinator",
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
    composite_run_id: str | None = None,
    lineage_created_at: datetime | None = None,
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
        composite_run_id=composite_run_id,
        lineage_created_at=lineage_created_at,
    )


def build_gold_merged_metadata_input(
    *,
    table_path: str,
    table_name: str,
    records: list[GoldRecord],
    completed_at: datetime | None,
    schema: DataFrameSchema | None,
    transform_version: str | None,
    transform_steps: tuple[str, ...],
    composite_run_id: str | None = None,
) -> GoldMetadataInput:
    """Build merged-table Gold metadata input payload."""
    return GoldMetadataInput(
        table_path=table_path,
        table_name=table_name,
        records=records,
        mode=GoldWriteMode.OVERWRITE,
        completed_at=completed_at or _extract_completed_at(records),
        composite_run_id=composite_run_id,
        lineage_created_at=completed_at,
        transform_version=transform_version,
        transform_steps=transform_steps,
        total_bytes=0,
        partition_count=0,
        schema_validation_enabled=schema is not None,
        schema_validation_strict=True if schema is not None else None,
    )


def _extract_completed_at(records: list[GoldRecord]) -> datetime | None:
    """Extract merged-write timestamp only from persisted ingestion anchors."""
    candidates: list[datetime] = []
    for record in records:
        ingestion_ts = record.get("_ingestion_ts")
        if isinstance(ingestion_ts, datetime):
            candidates.append(ingestion_ts)
            continue
        if isinstance(ingestion_ts, str):
            try:
                candidates.append(datetime.fromisoformat(ingestion_ts))
            except ValueError:
                continue
    if not candidates:
        return None
    return min(candidates)


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
    del run_id
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
    """Create Gold metadata using the canonical bundle-aware coordinator seam."""
    metadata_input = build_gold_metadata_input(
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
    metadata, _lineage_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="create_gold_metadata_bundle",
        coordinator_factory_name=None,
        input_data=metadata_input,
        fallback_factory=lambda: _raise_missing_gold_metadata_bundle(
            table_path=table_path,
            table_name=table_name,
        )
    )
    return metadata


def _raise_missing_gold_metadata_bundle(
    *,
    table_path: str,
    table_name: str,
) -> GoldMetadata:
    """Fail closed when bundle-only Gold metadata construction is unavailable."""
    raise RuntimeError(
        "MetadataCoordinator with create_gold_metadata_bundle is required "
        "for build_gold_metadata_payload: "
        f"table_name={table_name}, table_path={table_path}"
    )
