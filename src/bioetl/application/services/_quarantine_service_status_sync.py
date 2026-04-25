"""Sync status update helpers for QuarantineService."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.services._quarantine_service_support import (
    _QUARANTINE_OPERATOR_ERRORS,
)
from bioetl.application.services._quarantine_service_sync_support import (
    _QuarantineSyncHost,
    _run_traced_sync_operation,
)
from bioetl.domain.types import JsonDict, QuarantineRecordStatus

__all__ = ["QuarantineServiceStatusSyncMixin"]


class QuarantineServiceStatusSyncMixin:
    """Sync reprocessed-status and direct status update flows."""

    def mark_as_reprocessed(
        self: _QuarantineSyncHost,
        records: list[JsonDict],
    ) -> int:
        """Mark replay records as reprocessed."""
        return _run_traced_sync_operation(
            self,
            span_name="quarantine.mark_reprocessed",
            operation="mark_reprocessed",
            pipeline=None,
            trace_attributes={"bioetl.input_record_count": len(records)},
            execute=lambda started_at, started_monotonic: self._mark_as_reprocessed_impl(
                records=records,
                started_at=started_at,
                started_monotonic=started_monotonic,
            ),
            success_of=lambda count: count == len(records),
            result_extra_of=lambda count: {"bioetl.updated_count": count},
        )

    def _mark_as_reprocessed_impl(
        self: _QuarantineSyncHost,
        *,
        records: list[JsonDict],
        started_at: datetime,
        started_monotonic: float,
    ) -> int:
        """Implement reprocessed status updates without tracing concerns."""
        count = 0
        for rec in records:
            payload_hash = rec.get("payload_hash")
            if payload_hash and self.quarantine_port.update_status(
                payload_hash,
                QuarantineRecordStatus.REPROCESSED,
            ):
                count += 1

        completed_at, duration_seconds = self._derive_operator_completion(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        self.logger.info(
            "Marked records as reprocessed",
            record_count=count,
            completed_at=completed_at.isoformat(),
            duration_seconds=duration_seconds,
        )
        status = "success" if count == len(records) else "partial"
        self._record_operator_metrics(
            operation="mark_reprocessed",
            status=status,
            duration_seconds=duration_seconds,
        )
        return count

    def update_status(
        self: _QuarantineSyncHost,
        payload_hash: str,
        new_status: QuarantineRecordStatus,
    ) -> bool:
        """Update DQ status for a quarantined record."""
        return _run_traced_sync_operation(
            self,
            span_name="quarantine.update_status",
            operation="update_status",
            pipeline=None,
            trace_attributes={"bioetl.new_status": new_status.value},
            execute=lambda started_at, started_monotonic: self._update_status_impl(
                payload_hash=payload_hash,
                new_status=new_status,
                started_at=started_at,
                started_monotonic=started_monotonic,
            ),
            success_of=lambda success: success,
            result_extra_of=lambda success: {"bioetl.status_found": success},
        )

    def _update_status_impl(
        self: _QuarantineSyncHost,
        *,
        payload_hash: str,
        new_status: QuarantineRecordStatus,
        started_at: datetime,
        started_monotonic: float,
    ) -> bool:
        """Implement status update flow without tracing concerns."""
        self.logger.debug(
            "Updating quarantine status",
            payload_hash=payload_hash,
            new_status=new_status.value,
        )

        try:
            success = self.quarantine_port.update_status(payload_hash, new_status)
        except _QUARANTINE_OPERATOR_ERRORS:
            _, duration_seconds = self._derive_operator_completion(
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            self._record_operator_metrics(
                operation="update_status",
                status="failed",
                duration_seconds=duration_seconds,
            )
            raise

        completed_at, duration_seconds = self._derive_operator_completion(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        if success:
            self.logger.info(
                "Updated quarantine status",
                payload_hash=payload_hash,
                new_status=new_status.value,
                completed_at=completed_at.isoformat(),
                duration_seconds=duration_seconds,
            )
        else:
            self.logger.warning(
                "Failed to update quarantine status - record not found",
                payload_hash=payload_hash,
                completed_at=completed_at.isoformat(),
                duration_seconds=duration_seconds,
            )

        self._record_operator_metrics(
            operation="update_status",
            status="success" if success else "not_found",
            duration_seconds=duration_seconds,
        )
        return bool(success)
