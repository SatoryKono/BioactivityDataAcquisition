"""Write, audit, and finalization facade methods for Silver metadata services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_audit_operations import (
    log_internal_silver_audit_operation,
    log_silver_audit_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_context_facade import (
    _SilverMetadataContextFacade,
)
from bioetl.infrastructure.storage.silver.operations.metadata_finalization_operations import (
    finalize_silver_write_result_operation,
    prepare_silver_write_finalization_context_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_operations import (
    _ExecuteSilverMetadataWrite,
    write_internal_silver_metadata_operation,
    write_silver_merged_metadata_operation,
    write_silver_metadata_via_support_request,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _SilverMetadataAuditSupportRequest,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)

__all__ = ["_SilverMetadataWriteFacade"]


def _resolve_execute_silver_metadata_write() -> _ExecuteSilverMetadataWrite:
    """Resolve the legacy patch seam from ``operations.metadata_operations``."""
    from bioetl.infrastructure.storage.silver.operations import metadata_operations

    return metadata_operations._execute_silver_metadata_write


class _SilverMetadataWriteFacade(_SilverMetadataContextFacade):
    """Write, audit, and finalization methods for metadata services."""

    async def _write_silver_metadata(
        self,
        request: _SilverMetadataWriteRequest,
    ) -> None:
        """Canonical Silver metadata publication path for composition-backed ops."""
        await write_internal_silver_metadata_operation(
            self,
            request,
            execute_silver_metadata_write=_resolve_execute_silver_metadata_write(),
        )

    async def _write_silver_merged_metadata(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Canonical Silver metadata publication path for merged composite writes."""
        await write_silver_merged_metadata_operation(
            self,
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            execute_silver_metadata_write=_resolve_execute_silver_metadata_write(),
        )

    async def write_silver_metadata(
        self,
        table_name: str,
        dq_metrics: BatchDQMetrics,
        records: list[BronzeRecord],
        bronze_refs: list[BronzeWriteResult] | None = None,
        mode: str = "merge",
        validated_mode: SilverWriteMode = SilverWriteMode.MERGE,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
    ) -> SilverWriteResult | None:
        """Write metadata for Silver layer."""
        return await write_silver_metadata_via_support_request(
            self,
            table_name=table_name,
            dq_metrics=dq_metrics,
            records=records,
            bronze_refs=bronze_refs,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

    async def log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: str,
        validated_mode: SilverWriteMode,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        error: str | None = None,
    ) -> None:
        """Log Silver write audit event."""
        await log_silver_audit_operation(
            self,
            table_name=table_name,
            records=records,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            error=error,
        )

    async def _log_silver_audit(
        self,
        request: _SilverMetadataAuditSupportRequest,
    ) -> None:
        """Log Silver audit through the canonical request payload."""
        await log_internal_silver_audit_operation(
            self,
            request,
        )

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest,
        *,
        perf_counter: Callable[[], float] | None = None,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before Silver metadata persistence."""
        return await prepare_silver_write_finalization_context_operation(
            self,
            request,
            perf_counter=perf_counter,
        )

    async def _finalize_silver_write_result(
        self,
        request: _SilverWriteResultFinalizationRequest,
    ) -> SilverWriteResult | None:
        """Compute DQ metrics, write metadata, and build final result."""
        return await finalize_silver_write_result_operation(
            self,
            request,
        )
