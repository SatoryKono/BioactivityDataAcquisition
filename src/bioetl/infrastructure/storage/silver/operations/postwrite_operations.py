"""Postwrite operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.storage.silver.operations.postwrite_execution import (
    _build_postwrite_audit_hook_request,
    _build_postwrite_export_hook_request,
    _complete_silver_write_pipeline_impl,
    _finalize_silver_postwrite_result,
    _run_postwrite_audit_via_host_hook,
    _run_postwrite_export_via_host_hook,
    _SilverPostwriteAuditHookRequest,
    _SilverPostwriteExportHookRequest,
)
from bioetl.infrastructure.storage.silver.operations.postwrite_protocols import (
    _SilverMaintenancePostwriteOps,
    _SilverMetadataPostwriteOps,
    _SilverPostwriteExecutorProtocol,
    _SilverPostwriteFinalizerProtocol,
    _SilverPostwriteHostProtocol,
    _SilverWritePostwriteContext,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)

if TYPE_CHECKING:
    from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = [
    "SilverPostwriteOperations",
    "_SilverMaintenancePostwriteOps",
    "_SilverMetadataPostwriteOps",
    "_SilverPostwriteAuditHookRequest",
    "_SilverPostwriteExecutorProtocol",
    "_SilverPostwriteExportHookRequest",
    "_SilverPostwriteFinalizerProtocol",
    "_SilverPostwriteHostProtocol",
    "_SilverWritePostwriteContext",
    "_build_postwrite_audit_hook_request",
    "_build_postwrite_export_hook_request",
    "_complete_silver_write_pipeline_impl",
    "_finalize_silver_postwrite_result",
    "_run_postwrite_audit_via_host_hook",
    "_run_postwrite_export_via_host_hook",
]


class SilverPostwriteOperations:
    """Postwrite operations service for Silver layer writes."""

    def __init__(self, host: _SilverPostwriteHostProtocol) -> None:
        """Initialize postwrite operations with host dependencies."""
        self._host = host

    async def _run_postwrite_export(
        self,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> None:
        """Run the postwrite export branch for composition-backed writers."""
        if hasattr(self._host, "_maintenance") and self._host._maintenance is not None:
            export_path = (
                Path(self._host.base_path) / f"{ctx.table_name}.csv"
            ).as_posix()
            await self._host._maintenance.maybe_export_csv(
                table_name=ctx.table_name,
                arrow_data=payload.arrow_data,
                export_path=export_path,
                primary_keys=ctx.primary_keys,
                audit_timestamp=ctx.ingestion_ts,
            )
            return

        await _run_postwrite_export_via_host_hook(
            self._host,
            request=_build_postwrite_export_hook_request(
                ctx=ctx,
                payload=payload,
            ),
        )

    async def _run_postwrite_audit(
        self,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> None:
        """Run the postwrite audit branch for composition-backed writers."""
        if hasattr(self._host, "_metadata") and self._host._metadata is not None:
            await self._host._metadata.log_silver_audit(
                table_name=ctx.table_name,
                records=payload.records,
                mode=str(payload.validated_mode),
                validated_mode=payload.validated_mode,
                run_id=ctx.run_id,
                run_type=ctx.run_type,
                source_batch_id=ctx.source_batch_id,
                ingestion_ts=ctx.ingestion_ts,
            )

    async def _finalize_postwrite_result(
        self,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Finalize the postwrite flow after export/audit orchestration."""
        return await _finalize_silver_postwrite_result(
            self._host._finalize_silver_write_result,
            ctx=ctx,
            payload=payload,
        )

    async def _complete_silver_write_pipeline(
        self,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Run post-write stages: CSV export, audit, and result finalization."""
        return await _complete_silver_write_pipeline_impl(
            self,
            ctx=ctx,
            payload=payload,
        )
