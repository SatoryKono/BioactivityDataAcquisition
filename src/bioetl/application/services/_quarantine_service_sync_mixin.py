"""Synchronous quarantine admin methods for QuarantineService."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
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


class QuarantineServiceSyncMixin:
    """Sync admin operations for QuarantineService."""

    def replay(
        self: _QuarantineSyncHost,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> list[JsonDict]:
        """Replay quarantine records for reprocessing."""
        now = datetime.now(tz=UTC)
        start_time = perf_counter()
        if self.tracer is None:
            return self._replay_impl(
                pipeline=pipeline,
                error_code=error_code,
                max_age_days=max_age_days,
                now=now,
                start_time=start_time,
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
                now=now,
                start_time=start_time,
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
        start_time: float,
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
            self._record_operator_metrics(
                operation="replay",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

        self.logger.info(
            "Replay records retrieved",
            pipeline=pipeline,
            record_count=len(records),
        )
        self._record_operator_metrics(
            operation="replay",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return records

    def mark_as_reprocessed(
        self: _QuarantineSyncHost,
        records: list[JsonDict],
    ) -> int:
        """Mark replay records as reprocessed."""
        start_time = perf_counter()
        if self.tracer is None:
            return self._mark_as_reprocessed_impl(records=records, start_time=start_time)
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
            count = self._mark_as_reprocessed_impl(records=records, start_time=start_time)
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
        start_time: float,
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

        self.logger.info(
            "Marked records as reprocessed",
            record_count=count,
        )
        status = "success" if count == len(records) else "partial"
        self._record_operator_metrics(
            operation="mark_reprocessed",
            status=status,
            duration_seconds=perf_counter() - start_time,
        )
        return count

    def purge(
        self: _QuarantineSyncHost,
        pipeline: str,
        older_than_days: int = 30,
    ) -> int:
        """Purge old quarantine records."""
        now = datetime.now(tz=UTC)
        start_time = perf_counter()
        if self.tracer is None:
            return self._purge_impl(
                pipeline=pipeline,
                older_than_days=older_than_days,
                now=now,
                start_time=start_time,
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
                now=now,
                start_time=start_time,
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
        start_time: float,
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
            self._record_operator_metrics(
                operation="purge",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

        self.logger.info(
            "Purged quarantine records",
            pipeline=pipeline,
            records_purged=count,
        )
        self._record_operator_metrics(
            operation="purge",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return int(count)

    def update_status(
        self: _QuarantineSyncHost,
        payload_hash: str,
        new_status: QuarantineRecordStatus,
    ) -> bool:
        """Update DQ status for a quarantined record."""
        start_time = perf_counter()
        if self.tracer is None:
            return self._update_status_impl(
                payload_hash=payload_hash,
                new_status=new_status,
                start_time=start_time,
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
                start_time=start_time,
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
        start_time: float,
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
            self._record_operator_metrics(
                operation="update_status",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

        if success:
            self.logger.info(
                "Updated quarantine status",
                payload_hash=payload_hash,
                new_status=new_status.value,
            )
        else:
            self.logger.warning(
                "Failed to update quarantine status - record not found",
                payload_hash=payload_hash,
            )

        self._record_operator_metrics(
            operation="update_status",
            status="success" if success else "not_found",
            duration_seconds=perf_counter() - start_time,
        )
        return bool(success)
