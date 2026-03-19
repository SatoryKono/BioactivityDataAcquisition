"""Metadata write operations extracted from ``GoldWriterMetadataMixin``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.gold.metadata_payloads import (
    build_gold_merged_metadata_input,
    build_gold_metadata_payload,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.models.metadata import GoldMetadata
    from bioetl.domain.ports import (
        LoggerPort,
        MetadataCoordinatorPort,
    )
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = [
    "_GoldMergedMetadataWriteHostProtocol",
    "_GoldMergedMetadataWriteRequest",
    "_GoldMetadataWriteHostProtocol",
    "_GoldMetadataWriteRequest",
    "_PreparedGoldMetadataWrite",
    "_extract_delta_table_version",
    "_maybe_prepare_gold_merged_metadata_write",
    "_persist_gold_metadata_write",
    "_prepare_gold_merged_metadata_write",
    "_prepare_gold_metadata_write",
]


@dataclass(frozen=True, slots=True)
class _GoldMetadataWriteRequest:
    """Normalized request payload for one standard Gold metadata write."""

    table_path: str
    table_name: str
    records: list[GoldRecord]
    mode: GoldWriteMode
    scd_config: ScdConfig | None
    ingestion_ts: datetime | None
    run_id: RunID | None
    silver_refs: list[SilverWriteResult] | None = None
    gold_schema: object | None = None


@dataclass(frozen=True, slots=True)
class _GoldMergedMetadataWriteRequest:
    """Normalized request payload for one merged Gold metadata write."""

    table_path: str
    table_name: str
    records: list[GoldRecord]
    schema: DataFrameSchema | None = None


@dataclass(frozen=True, slots=True)
class _PreparedGoldMetadataWrite:
    """Prepared Gold metadata write carried into persistence handoff."""

    request: _GoldMetadataWriteRequest | _GoldMergedMetadataWriteRequest
    provider_name: str
    entity_name: str
    metadata: GoldMetadata


class _GoldMetadataWriteHostProtocol(Protocol):
    """Typed host contract for standard Gold metadata preparation."""

    _metadata_coordinator: MetadataCoordinatorPort | None
    _transform_version: str | None
    _transform_steps: tuple[str, ...]

    async def _write_gold_metadata_file(
        self,
        *,
        table_path: str,
        metadata: GoldMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...


class _GoldMergedMetadataWriteHostProtocol(_GoldMetadataWriteHostProtocol, Protocol):
    """Host contract for merged Gold metadata writes."""

    logger: LoggerPort


def _normalize_delta_version_value(version_value: object) -> int | None:
    """Normalize a DeltaTable.version() result to an integer version."""
    if isinstance(version_value, int):
        return version_value
    if isinstance(version_value, str) and version_value.strip().isdigit():
        return int(version_value.strip())
    return None


def _extract_delta_table_version(table: object) -> int | None:
    """Extract a normalized version from a DeltaTable-like object."""
    version_fn = getattr(table, "version", None)
    if not callable(version_fn):
        return None
    return _normalize_delta_version_value(version_fn())


def _prepare_gold_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    request: _GoldMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite:
    """Resolve provider/entity and build standard Gold metadata payload."""
    from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

    provider_name, entity_name = _parse_table_name(request.table_name)
    metadata = build_gold_metadata_payload(
        coordinator=host._metadata_coordinator,
        table_path=request.table_path,
        table_name=request.table_name,
        records=request.records,
        mode=request.mode,
        scd_config=request.scd_config,
        ingestion_ts=request.ingestion_ts,
        run_id=request.run_id,
        silver_refs=request.silver_refs,
        gold_schema=request.gold_schema,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
    )
    return _PreparedGoldMetadataWrite(
        request=request,
        provider_name=provider_name,
        entity_name=entity_name,
        metadata=metadata,
    )


async def _persist_gold_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    prepared: _PreparedGoldMetadataWrite,
) -> None:
    """Execute one prepared Gold metadata write via the writer handoff."""
    await host._write_gold_metadata_file(
        table_path=prepared.request.table_path,
        metadata=prepared.metadata,
        table_name=prepared.request.table_name,
        provider_name=prepared.provider_name,
        entity_name=prepared.entity_name,
    )


def _prepare_gold_merged_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    request: _GoldMergedMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite:
    """Resolve provider/entity and build merged Gold metadata payload."""
    from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

    provider_name, entity_name = _parse_table_name(request.table_name)
    assert host._metadata_coordinator is not None
    metadata = host._metadata_coordinator.create_gold_metadata(
        build_gold_merged_metadata_input(
            table_path=request.table_path,
            table_name=request.table_name,
            records=request.records,
            schema=request.schema,
            transform_version=host._transform_version,
            transform_steps=host._transform_steps,
        )
    )
    return _PreparedGoldMetadataWrite(
        request=request,
        provider_name=provider_name,
        entity_name=entity_name,
        metadata=metadata,
    )


def _maybe_prepare_gold_merged_metadata_write(
    host: _GoldMergedMetadataWriteHostProtocol,
    request: _GoldMergedMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite | None:
    """Skip merged metadata writes when records or coordinator are missing."""
    if not request.records:
        return None
    if host._metadata_coordinator is None:
        host.logger.debug(
            "gold_merged_metadata_skipped",
            reason="MetadataCoordinator not configured",
            table_path=request.table_path,
        )
        return None
    return _prepare_gold_merged_metadata_write(host, request)
