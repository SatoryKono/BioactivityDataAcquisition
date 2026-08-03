"""Preparation helpers for canonical Silver metadata writes."""

from __future__ import annotations

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import MetadataCoordinatorPort, SilverMetadataInput
from bioetl.infrastructure.storage.lineage_persistence import (
    emit_composite_source_selection_metrics,
    emit_lineage_refs_missing_metric,
    resolve_metadata_and_lineage_fragment,
)
from bioetl.infrastructure.storage.metadata.builder_base import (
    _parse_table_name,
    _resolve_metadata_timestamp,
)
from bioetl.infrastructure.storage.silver.metadata_operation_protocols import (
    _SilverMetadataWriteHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverMetadataWriteOperation,
    _ResolvedSilverMetadataContext,
    _SilverMergedMetadataWriteRequest,
)

__all__ = [
    "_emit_prepared_silver_metadata_metrics",
    "_prepare_silver_merged_metadata_write",
    "_prepare_silver_metadata_write",
    "_raise_missing_silver_metadata_bundle",
    "_resolve_silver_metadata_bundle",
    "_resolve_silver_metadata_context",
]


def _emit_prepared_silver_metadata_metrics(
    host: _SilverMetadataWriteHostProtocol,
    prepared: _PreparedSilverMetadataWriteOperation,
) -> None:
    """Emit lineage/composite metrics for an already prepared metadata operation."""
    pipeline_name = f"{prepared.provider_name}_{prepared.entity_name}"
    if isinstance(prepared.request, _SilverMetadataWriteRequest):
        if not prepared.request.bronze_refs:
            emit_lineage_refs_missing_metric(
                getattr(host, "_metrics", None),
                pipeline_name=pipeline_name,
                layer="silver",
                ref_type="bronze_batch",
            )
        return
    emit_composite_source_selection_metrics(
        getattr(host, "_metrics", None),
        pipeline_name=pipeline_name,
        layer="silver",
        sources_used=prepared.request.sources_used,
        records=prepared.request.records,
    )


async def _resolve_silver_metadata_context(
    host: _SilverMetadataWriteHostProtocol,
    *,
    table_path: str,
    table_name: str,
    version_after: int | None = None,
) -> _ResolvedSilverMetadataContext:
    """Resolve shared provider/entity/version context for Silver metadata writes."""
    provider_name, entity_name = _parse_table_name(table_name)
    version = (
        version_after
        if version_after is not None
        else await host._get_delta_version(table_path)
    )
    return _ResolvedSilverMetadataContext(provider_name, entity_name, version)


def _resolve_silver_metadata_bundle(
    *,
    coordinator: MetadataCoordinatorPort | None,
    table_path: str,
    table_name: str,
    silver_input: SilverMetadataInput,
) -> tuple[SilverMetadata, LineageGraphFragment | None]:
    """Build the canonical Silver metadata bundle with a shared fallback policy."""
    return resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="create_silver_metadata_bundle",
        coordinator_factory_name=None,
        input_data=silver_input,
        fallback_factory=lambda: _raise_missing_silver_metadata_bundle(
            table_path=table_path,
            table_name=table_name,
        ),
    )


async def _prepare_silver_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMetadataWriteRequest,
) -> _PreparedSilverMetadataWriteOperation:
    """Resolve provider/entity and build standard Silver metadata payload."""
    context = await _resolve_silver_metadata_context(
        host,
        table_path=request.table_path,
        table_name=request.table_name,
        version_after=request.version_after,
    )
    silver_input = SilverMetadataInput(
        table_path=request.table_path,
        records=request.records,
        primary_keys=request.primary_keys,
        mode=request.mode,
        bronze_refs=request.bronze_refs,
        dq_metrics=request.dq_metrics,
        version_after=context.version_after,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
        dq_report_path=request.dq_report_path,
        partition_by=request.partition_by,
        source_batch_ids=request.source_batch_ids,
        started_at=request.started_at,
        completed_at=request.completed_at,
    )
    metadata, lineage_fragment = _resolve_silver_metadata_bundle(
        coordinator=host._metadata_coordinator,
        table_path=request.table_path,
        table_name=request.table_name,
        silver_input=silver_input,
    )
    return _PreparedSilverMetadataWriteOperation(
        request=request,
        provider_name=context.provider_name,
        entity_name=context.entity_name,
        metadata=metadata,
        lineage_fragment=lineage_fragment,
    )


async def _prepare_silver_merged_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMergedMetadataWriteRequest,
) -> _PreparedSilverMetadataWriteOperation:
    """Resolve provider/entity and build merged Silver metadata payload."""
    context = await _resolve_silver_metadata_context(
        host,
        table_path=request.table_path,
        table_name=request.table_name,
    )
    merged_completed_at = _resolve_metadata_timestamp(
        explicit=request.completed_at,
        records=request.records,
    )
    silver_input = SilverMetadataInput(
        table_path=request.table_path,
        records=request.records,
        primary_keys=request.primary_keys,
        mode=SilverWriteMode.DELETE,
        started_at=merged_completed_at,
        completed_at=merged_completed_at,
        composite_run_id=request.run_id,
        lineage_created_at=merged_completed_at,
        version_after=context.version_after,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
    )
    metadata, lineage_fragment = _resolve_silver_metadata_bundle(
        coordinator=host._metadata_coordinator,
        table_path=request.table_path,
        table_name=request.table_name,
        silver_input=silver_input,
    )
    return _PreparedSilverMetadataWriteOperation(
        request=request,
        provider_name=context.provider_name,
        entity_name=context.entity_name,
        metadata=metadata,
        lineage_fragment=lineage_fragment,
    )


def _raise_missing_silver_metadata_bundle(
    *,
    table_path: str,
    table_name: str,
) -> SilverMetadata:
    """Fail closed when canonical Silver metadata bundle construction is unavailable."""
    raise RuntimeError(
        "MetadataCoordinator with create_silver_metadata_bundle is required "
        f"for Silver metadata publication: table_name={table_name}, "
        f"table_path={table_path}"
    )
