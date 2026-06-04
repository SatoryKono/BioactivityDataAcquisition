"""Metadata write operations extracted from ``GoldWriterMetadataMixin``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.models.metadata import GoldMetadata
from bioetl.domain.ports import LineageStorePort
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.gold.metadata_operation_helpers import (
    extract_delta_table_version as _extract_delta_table_version,
)
from bioetl.infrastructure.storage.gold.metadata_operation_helpers import (
    normalize_delta_version_value as _normalize_delta_version_value,
)
from bioetl.infrastructure.storage.gold.metadata_operation_helpers import (
    raise_missing_gold_metadata_bundle as _raise_missing_gold_metadata_bundle,
)
from bioetl.infrastructure.storage.gold.metadata_payloads import (
    build_gold_merged_metadata_input,
    build_gold_metadata_input,
)
from bioetl.infrastructure.storage.lineage_persistence import (
    emit_composite_source_selection_metrics,
    emit_lineage_refs_missing_metric,
    lineage_fragment_publication_required,
    persist_lineage_fragment_if_present,
    resolve_metadata_and_lineage_fragment,
)
from bioetl.infrastructure.storage.metadata.builder_base import _parse_table_name

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.lineage import LineageGraphFragment
    from bioetl.domain.ports import LoggerPort, MetadataCoordinatorPort, MetricsPort
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
    "_normalize_delta_version_value",
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
    completed_at: datetime | None = None
    run_id: RunID | None = None
    schema: DataFrameSchema | None = None


@dataclass(frozen=True, slots=True)
class _PreparedGoldMetadataWrite:
    """Prepared Gold metadata write carried into persistence handoff."""

    request: _GoldMetadataWriteRequest | _GoldMergedMetadataWriteRequest
    provider_name: str
    entity_name: str
    metadata: GoldMetadata
    lineage_fragment: LineageGraphFragment | None = None


class _GoldMetadataWriteHostProtocol(Protocol):
    """Typed host contract for standard Gold metadata preparation."""

    _metadata_coordinator: MetadataCoordinatorPort | None
    _lineage_store: LineageStorePort | None
    _metrics: MetricsPort | None
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


def _prepare_gold_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    request: _GoldMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite:
    """Resolve provider/entity and build standard Gold metadata payload."""
    provider_name, entity_name = _parse_table_name(request.table_name)
    gold_input = build_gold_metadata_input(
        table_path=request.table_path,
        table_name=request.table_name,
        records=request.records,
        mode=request.mode,
        scd_config=request.scd_config,
        completed_at=request.ingestion_ts,
        silver_refs=request.silver_refs,
        gold_schema=request.gold_schema,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
    )
    metadata, lineage_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=host._metadata_coordinator,
        bundle_factory_name="create_gold_metadata_bundle",
        coordinator_factory_name=None,
        input_data=gold_input,
        fallback_factory=lambda: _raise_missing_gold_metadata_bundle(
            table_path=request.table_path,
            table_name=request.table_name,
        ),
    )
    return _PreparedGoldMetadataWrite(
        request=request,
        provider_name=provider_name,
        entity_name=entity_name,
        metadata=metadata,
        lineage_fragment=lineage_fragment,
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
    await persist_lineage_fragment_if_present(
        lineage_store=getattr(host, "_lineage_store", None),
        lineage_fragment=prepared.lineage_fragment,
        metrics=getattr(host, "_metrics", None),
        pipeline_name=f"{prepared.provider_name}_{prepared.entity_name}",
        layer="gold",
        required=lineage_fragment_publication_required(
            getattr(host, "_metadata_coordinator", None)
        ),
    )
    pipeline_name = f"{prepared.provider_name}_{prepared.entity_name}"
    if isinstance(prepared.request, _GoldMetadataWriteRequest):
        if not prepared.request.silver_refs:
            emit_lineage_refs_missing_metric(
                getattr(host, "_metrics", None),
                pipeline_name=pipeline_name,
                layer="gold",
                ref_type="silver_dataset",
            )
        return
    emit_composite_source_selection_metrics(
        getattr(host, "_metrics", None),
        pipeline_name=pipeline_name,
        layer="gold",
        records=prepared.request.records,
    )


def _prepare_gold_merged_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    request: _GoldMergedMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite:
    """Resolve provider/entity and build merged Gold metadata payload."""
    provider_name, entity_name = _parse_table_name(request.table_name)
    coordinator = host._metadata_coordinator
    assert coordinator is not None
    gold_input = build_gold_merged_metadata_input(
        table_path=request.table_path,
        table_name=request.table_name,
        records=request.records,
        completed_at=request.completed_at,
        composite_run_id=None if request.run_id is None else str(request.run_id),
        schema=request.schema,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
    )
    metadata, lineage_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="create_gold_metadata_bundle",
        coordinator_factory_name=None,
        input_data=gold_input,
        fallback_factory=lambda: _raise_missing_gold_metadata_bundle(
            table_path=request.table_path,
            table_name=request.table_name,
        ),
    )
    return _PreparedGoldMetadataWrite(
        request=request,
        provider_name=provider_name,
        entity_name=entity_name,
        metadata=metadata,
        lineage_fragment=lineage_fragment,
    )


def _maybe_prepare_gold_merged_metadata_write(
    host: _GoldMergedMetadataWriteHostProtocol,
    request: _GoldMergedMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite | None:
    """Skip only empty merged metadata writes; missing coordinator fails closed."""
    if not request.records:
        return None
    if host._metadata_coordinator is None:
        raise RuntimeError(
            "MetadataCoordinator with create_gold_metadata_bundle is required "
            f"for Gold metadata publication: table_name={request.table_name}, "
            f"table_path={request.table_path}"
        )
    return _prepare_gold_merged_metadata_write(host, request)
