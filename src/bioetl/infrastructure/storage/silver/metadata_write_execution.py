"""Execution helpers for prepared Silver metadata writes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from bioetl.infrastructure.storage.lineage_persistence import (
    lineage_fragment_publication_required,
    persist_lineage_fragment_if_present,
)
from bioetl.infrastructure.storage.silver.metadata_operation_protocols import (
    _SilverMetadataWriteHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.metadata_write_preparation import (
    _emit_prepared_silver_metadata_metrics,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverMetadataWriteOperation,
    _SilverMergedMetadataWriteRequest,
)

__all__ = [
    "_execute_prepared_silver_metadata_write_operation",
    "_execute_silver_metadata_write",
]


async def _execute_prepared_silver_metadata_write_operation(
    host: _SilverMetadataWriteHostProtocol,
    prepared: _PreparedSilverMetadataWriteOperation,
) -> None:
    """Execute one prepared Silver metadata operation via the writer handoff."""
    await host._write_silver_metadata_file(
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
        layer="silver",
        required=lineage_fragment_publication_required(
            getattr(host, "_metadata_coordinator", None)
        ),
    )
    _emit_prepared_silver_metadata_metrics(host, prepared)


async def _execute_silver_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest,
    prepare: Callable[..., Awaitable[_PreparedSilverMetadataWriteOperation]],
) -> None:
    """Prepare and persist one Silver metadata write via the canonical lifecycle."""
    prepared = await prepare(host, request)
    await _execute_prepared_silver_metadata_write_operation(host, prepared)
