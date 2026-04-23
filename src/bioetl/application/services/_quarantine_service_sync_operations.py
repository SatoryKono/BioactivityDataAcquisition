"""Internal sync quarantine operation mixins."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.observability.span_helpers import traced_operation
from bioetl.application.services._quarantine_service_support import (
    _QUARANTINE_OPERATOR_ERRORS,
)
from bioetl.domain.types import JsonDict, QuarantineRecordStatus

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, QuarantinePort, TracingPort


class _QuarantineSyncHost(Protocol):
    """Structural contract required by sync quarantine admin helpers."""

    TRACER_NAME: str
    logger: LoggerPort
    quarantine_port: QuarantinePort
    tracer: TracingPort | None

    def _capture_operator_timing_anchor(self) -> tuple[datetime, float]: ...

    def _derive_operator_completion(
        self,
        *,
        started_at: datetime,
        started_monotonic: float,
    ) -> tuple[datetime, float]: ...

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None: ...

    def _trace_attributes(
        self,
        *,
        operation: str,
        pipeline: str | None = None,
        **extra: object,
    ) -> dict[str, object]: ...

    def _set_trace_result(
        self,
        span: Span,
        *,
        success: bool,
        **extra: object,
    ) -> None: ...


class QuarantineServiceReplayPurgeSyncMixin:
    """Sync replay and purge quarantine flows."""

    def replay(
        self: _QuarantineSyncHost,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> list[JsonDict]:
        """Replay quarantine records for reprocessing."""
        started_at, started_monotonic = self._capture_operator_timing_anchor()
        if self.tracer is None:
            return self._replay_impl(
                pipeline=pipeline,
                error_code=error_code,
                max_age_days=max_age_days,
                now=started_at,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
        with traced_operation(
            self.tracer,
            "quarantine.replay",
            self._trace_attributes(
                operation="replay",
                pipeline=pipeline,
                **{
                    "bioetl.has_error_code_filter": error_code is not None,
                    "bioetl.max_age_days": max_age_days,
                },
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            records = self._replay_impl(
                pipeline=pipeline,
                error_code=error_code,
                max_age_days=max_age_days,
                now=started_at,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            self._set_trace_result(
                span,
                success=True,
                **{"bioetl.record_count": len(records)},
            )
            return records

    def _replay_impl(
        self: _QuarantineSyncHost,
        *,
        pipeline: str,
        error_code: str | None,
        max_age_days: int,
        now: datetime,
        started_at: datetime,
        started_monotonic: float,
    ) -> list[JsonDict]:
        """Implement quarantine replay lookup without tracing concerns."""
        self.logger.info(
            "Replaying quarantine records",
            pipeline=pipeline,
            error_code=error_code,
            max_age_days=max_age_days,
        )

        try:
            records = list(
                self.quarantine_port.replay(
                    pipeline=pipeline,
                    error_code=error_code,
                    max_age_days=max_age_days,
                    now=now,
                )
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            _, duration_seconds = self._derive_operator_completion(
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            self._record_operator_metrics(
                operation="replay",
                status="failed",
                duration_seconds=duration_seconds,
            )
            raise

        completed_at, duration_seconds = self._derive_operator_completion(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        self.logger.info(
            "Replay records retrieved",
            pipeline=pipeline,
            record_count=len(records),
            completed_at=completed_at.isoformat(),
            duration_seconds=duration_seconds,
        )
        self._record_operator_metrics(
            operation="replay",
            status="success",
            duration_seconds=duration_seconds,
        )
        return records

    def purge(
        self: _QuarantineSyncHost,
        pipeline: str,
        older_than_days: int = 30,
    ) -> int:
        """Purge old quarantine records."""
        started_at, started_monotonic = self._capture_operator_timing_anchor()
        if self.tracer is None:
            return self._purge_impl(
                pipeline=pipeline,
                older_than_days=older_than_days,
                now=started_at,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
        with traced_operation(
            self.tracer,
            "quarantine.purge",
            self._trace_attributes(
                operation="purge",
                pipeline=pipeline,
                **{"bioetl.older_than_days": older_than_days},
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            count = self._purge_impl(
                pipeline=pipeline,
                older_than_days=older_than_days,
                now=started_at,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            self._set_trace_result(
                span,
                success=True,
                **{"bioetl.records_purged": count},
            )
            return count

    def _purge_impl(
        self: _QuarantineSyncHost,
        *,
        pipeline: str,
        older_than_days: int,
        now: datetime,
        started_at: datetime,
        started_monotonic: float,
    ) -> int:
        """Implement purge flow without tracing concerns."""
        self.logger.info(
            "Purging old quarantine records",
            pipeline=pipeline,
            older_than_days=older_than_days,
        )

        try:
            count = self.quarantine_port.purge(
                pipeline=pipeline,
                older_than_days=older_than_days,
                now=now,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            _, duration_seconds = self._derive_operator_completion(
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            self._record_operator_metrics(
                operation="purge",
                status="failed",
                duration_seconds=duration_seconds,
            )
            raise

        completed_at, duration_seconds = self._derive_operator_completion(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        self.logger.info(
            "Purged quarantine records",
            pipeline=pipeline,
            records_purged=count,
            completed_at=completed_at.isoformat(),
            duration_seconds=duration_seconds,
        )
        self._record_operator_metrics(
            operation="purge",
            status="success",
            duration_seconds=duration_seconds,
        )
        return int(count)


class QuarantineServiceStatusSyncMixin:
    """Sync reprocessed-status and direct status update flows."""

    def mark_as_reprocessed(
        self: _QuarantineSyncHost,
        records: list[JsonDict],
    ) -> int:
        """Mark replay records as reprocessed."""
        started_at, started_monotonic = self._capture_operator_timing_anchor()
        if self.tracer is None:
            return self._mark_as_reprocessed_impl(
                records=records,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
        with traced_operation(
            self.tracer,
            "quarantine.mark_reprocessed",
            self._trace_attributes(
                operation="mark_reprocessed",
                pipeline=None,
                **{"bioetl.input_record_count": len(records)},
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            count = self._mark_as_reprocessed_impl(
                records=records,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            self._set_trace_result(
                span,
                success=count == len(records),
                **{"bioetl.updated_count": count},
            )
            return count

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
        started_at, started_monotonic = self._capture_operator_timing_anchor()
        if self.tracer is None:
            return self._update_status_impl(
                payload_hash=payload_hash,
                new_status=new_status,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
        with traced_operation(
            self.tracer,
            "quarantine.update_status",
            self._trace_attributes(
                operation="update_status",
                **{"bioetl.new_status": new_status.value},
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            success = self._update_status_impl(
                payload_hash=payload_hash,
                new_status=new_status,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            self._set_trace_result(
                span,
                success=success,
                **{"bioetl.status_found": success},
            )
            return success

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
