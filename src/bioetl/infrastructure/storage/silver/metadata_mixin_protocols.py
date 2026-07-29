# MRO/override residual on mixin or client hierarchies.
"""Runtime protocol for ``SilverWriterMetadataMixin`` delegates."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol

import pyarrow as pa

from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
)
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_operation_protocols import (
    _SilverMetadataWriteHostProtocol,
    _SilverWriteFinalizationHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)

__all__ = ["_SilverWriterMetadataRuntimeProtocol"]


class _SilverWriterMetadataRuntimeProtocol(
    _SilverMetadataWriteHostProtocol,
    _SilverWriteFinalizationHostProtocol,
    Protocol,
):
    """Full runtime contract expected by ``SilverWriterMetadataMixin`` methods."""

    logger: LoggerPort
    _audit: AuditPort | None
    _dq_calculator: DQMetricsCalculator
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]
    _metadata_coordinator: MetadataCoordinatorPort | None  # pyright: ignore[reportIncompatibleMethodOverride]
    _lineage_store: LineageStorePort | None  # pyright: ignore[reportIncompatibleMethodOverride]
    _metadata_writer: MetadataWriterPort
    _metrics: MetricsPort | None  # pyright: ignore[reportIncompatibleMethodOverride]
    _flat_structure: bool  # pyright: ignore[reportIncompatibleMethodOverride]
    _transform_version: str | None  # pyright: ignore[reportIncompatibleMethodOverride]
    _transform_steps: tuple[str, ...]  # pyright: ignore[reportIncompatibleMethodOverride]

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
    ) -> bool: ...

    async def _log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
        *,
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
    ) -> None: ...

    async def _write_silver_metadata(
        self,
        request: _SilverMetadataWriteRequest,
    ) -> None: ...

    async def _maybe_log_silver_audit(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
    ) -> None: ...

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest,
        *,
        perf_counter: Callable[[], float] | None = None,
    ) -> _PreparedSilverWriteFinalizationContext: ...

    async def _get_delta_version(self, table_path: str) -> int | None: ...

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...
