"""Sync replay and purge helpers for QuarantineService."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.services._quarantine_service_support import (
    _QUARANTINE_OPERATOR_ERRORS,
)
from bioetl.application.services._quarantine_service_sync_support import (
    _QuarantineSyncHost,
    _run_traced_sync_operation,
)
from bioetl.domain.types import JsonDict

__all__ = ["QuarantineServiceReplayPurgeSyncMixin"]


class QuarantineServiceReplayPurgeSyncMixin:
    """Sync replay and purge quarantine flows."""

    def replay(
        self: _QuarantineSyncHost,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> list[JsonDict]:
        """Replay quarantine records for reprocessing."""
        return _run_traced_sync_operation(
            self,
            span_name="quarantine.replay",
            operation="replay",
            pipeline=pipeline,
            trace_attributes={
                "bioetl.has_error_code_filter": error_code is not None,
                "bioetl.max_age_days": max_age_days,
            },
            execute=lambda started_at, started_monotonic: self._replay_impl(
                pipeline=pipeline,
                error_code=error_code,
                max_age_days=max_age_days,
                now=started_at,
                started_at=started_at,
                started_monotonic=started_monotonic,
            ),
            success_of=lambda _records: True,
            result_extra_of=lambda records: {"bioetl.record_count": len(records)},
        )

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
        return _run_traced_sync_operation(
            self,
            span_name="quarantine.purge",
            operation="purge",
            pipeline=pipeline,
            trace_attributes={"bioetl.older_than_days": older_than_days},
            execute=lambda started_at, started_monotonic: self._purge_impl(
                pipeline=pipeline,
                older_than_days=older_than_days,
                now=started_at,
                started_at=started_at,
                started_monotonic=started_monotonic,
            ),
            success_of=lambda _count: True,
            result_extra_of=lambda count: {"bioetl.records_purged": count},
        )

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
