"""Quarantine service for administrative operations (Application layer).

Provides high-level quarantine management for CLI and other interfaces.
Uses QuarantinePort for actual persistence operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

__all__ = ["QuarantineRecord", "QuarantineService"]


from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.observability.span_helpers import (
    traced_async_operation,
    traced_operation,
)
from bioetl.application.services._quarantine_service_filtered_mixin import (
    QuarantineServiceFilteredMixin,
)
from bioetl.domain.types import JsonDict, QuarantineRecordStatus

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort, TracingPort


_QUARANTINE_OPERATOR_DURATION_METRIC = "bioetl_quarantine_operator_duration_seconds"
_QUARANTINE_OPERATOR_OPERATIONS_METRIC = (
    "bioetl_quarantine_operator_operations_total"
)
_QUARANTINE_OPERATOR_ERRORS = (OSError, RuntimeError, TypeError, ValueError)


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """Representation of a quarantined record.

    Attributes:
        error_code: Error code that caused quarantine, or None if unknown.
        payload: Original record data.
        batch_id: Bronze batch ID.
        pipeline: Pipeline name.
        ingestion_ts: When record was quarantined.
        metadata: Additional metadata.
    """

    error_code: str | None
    payload: JsonDict  # Any: quarantine payload has heterogeneous values
    batch_id: str | None
    pipeline: str
    ingestion_ts: datetime | None
    metadata: JsonDict  # Any: metadata values are heterogeneous


@dataclass
class QuarantineService(QuarantineServiceFilteredMixin):
    """Service for administrative quarantine operations.

    Provides high-level operations for quarantine management
    used by CLI and other interfaces. Wraps QuarantinePort
    for Application-layer abstraction.

    Attributes:
        quarantine_port: Port for quarantine persistence.
        logger: Structured logger for observability.

    Example:
        >>> service = QuarantineService(quarantine_port=port, logger=logger)
        >>> records = await service.inspect("chembl_activity", limit=10)
        >>> for rec in records:
        ...     logger.info("quarantine_record", error_code=rec.error_code, payload=rec.payload)
    """

    quarantine_port: QuarantinePort
    logger: LoggerPort
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    TRACER_NAME = "bioetl.quarantine_admin"

    def _trace_attributes(
        self,
        *,
        operation: str,
        pipeline: str | None = None,
        **extra: object,
    ) -> dict[str, object]:
        """Build bounded tracing attributes for quarantine admin operations."""
        attributes: dict[str, object] = {
            "bioetl.component": "quarantine_service",
            "bioetl.operation": operation,
        }
        if pipeline is not None:
            attributes["bioetl.pipeline"] = pipeline
        attributes.update(extra)
        return attributes

    @staticmethod
    def _set_trace_result(
        span: Span,
        *,
        success: bool,
        **extra: object,
    ) -> None:
        """Attach bounded result attributes to an active trace span."""
        span.set_attribute("bioetl.success", success)
        for key, value in extra.items():
            span.set_attribute(key, value)

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record bounded admin/explorer metrics when a metrics port is available."""
        if self.metrics is None:
            return
        labels = {"operation": operation, "status": status}
        self.metrics.increment_counter(
            _QUARANTINE_OPERATOR_OPERATIONS_METRIC,
            1,
            labels=labels,
        )
        self.metrics.observe_histogram(
            _QUARANTINE_OPERATOR_DURATION_METRIC,
            duration_seconds,
            labels=labels,
        )

    async def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[QuarantineRecord]:
        """Inspect quarantined records for a pipeline.

        Args:
            pipeline: Pipeline name to inspect.
            limit: Maximum number of records to return.
            error_code: Optional filter by error code.

        Returns:
            List of QuarantineRecord objects.
        """
        start_time = perf_counter()
        if self.tracer is None:
            return await self._inspect_impl(
                pipeline=pipeline,
                limit=limit,
                error_code=error_code,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "quarantine.inspect",
            self._trace_attributes(
                operation="inspect",
                pipeline=pipeline,
                **{
                    "bioetl.limit": limit,
                    "bioetl.has_error_code_filter": error_code is not None,
                },
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            records = await self._inspect_impl(
                pipeline=pipeline,
                limit=limit,
                error_code=error_code,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                **{"bioetl.record_count": len(records)},
            )
            return records

    async def _inspect_impl(
        self,
        *,
        pipeline: str,
        limit: int,
        error_code: str | None,
        start_time: float,
    ) -> list[QuarantineRecord]:
        """Implement quarantine inspection without tracing concerns."""
        self.logger.debug(
            "Inspecting quarantine",
            pipeline=pipeline,
            limit=limit,
            error_code=error_code,
        )

        try:
            raw_records = await self.quarantine_port.inspect(
                pipeline=pipeline,
                limit=limit,
                error_code=error_code,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="inspect",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

        records = [
            QuarantineRecord(
                error_code=rec.get("error_code"),
                payload=rec.get("payload", {}),
                batch_id=rec.get("bronze_batch_id"),
                pipeline=pipeline,
                ingestion_ts=rec.get("ingestion_ts"),
                metadata=rec.get("metadata", {}),
            )
            for rec in raw_records
        ]

        self.logger.info(
            "Inspected quarantine",
            pipeline=pipeline,
            record_count=len(records),
        )
        self._record_operator_metrics(
            operation="inspect",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )

        return records

    async def get_stats(
        self,
        pipeline: str,
        error_code: str | None = None,
    ) -> JsonDict:  # Any: quarantine record has heterogeneous values
        """Get statistics about quarantined records.

        Args:
            pipeline: Pipeline name.
            error_code: Optional error code to scope the statistics.

        Returns:
            Dictionary with quarantine statistics by error code.
        """
        start_time = perf_counter()
        if self.tracer is None:
            return await self._get_stats_impl(
                pipeline=pipeline,
                error_code=error_code,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "quarantine.stats",
            self._trace_attributes(
                operation="stats",
                pipeline=pipeline,
                **{"bioetl.has_error_code_filter": error_code is not None},
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            stats = await self._get_stats_impl(
                pipeline=pipeline,
                error_code=error_code,
                start_time=start_time,
            )
            self._set_trace_result(span, success=True)
            return stats

    async def _get_stats_impl(
        self,
        *,
        pipeline: str,
        error_code: str | None,
        start_time: float,
    ) -> JsonDict:
        """Implement quarantine statistics lookup without tracing concerns."""
        self.logger.debug("Getting quarantine stats", pipeline=pipeline)

        try:
            stats = await self.quarantine_port.get_stats(pipeline, error_code)
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="stats",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

        self.logger.info(
            "Got quarantine stats",
            pipeline=pipeline,
            stats=stats,
        )
        self._record_operator_metrics(
            operation="stats",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )

        return stats

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> list[JsonDict]:  # Any: quarantine record has heterogeneous values
        """Replay quarantine records for reprocessing.

        Retrieves quarantined records that match the filter criteria
        for reprocessing by the pipeline.

        Args:
            pipeline: Pipeline name to filter by.
            error_code: Optional error code to filter by.
            max_age_days: Maximum age of records to replay (default 7).

        Returns:
            List of quarantine records suitable for replay.
        """
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
        self,
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
        self,
        records: list[
            JsonDict  # Any: quarantine record has heterogeneous values
        ],  # Any: quarantine record has heterogeneous values
    ) -> int:
        """Mark replay records as reprocessed.

        Updates the status of records to REPROCESSED after successful replay.

        Args:
            records: List of records from replay() to mark as reprocessed.

        Returns:
            Number of records successfully marked.
        """
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
        self,
        *,
        records: list[JsonDict],
        start_time: float,
    ) -> int:
        """Implement reprocessed status updates without tracing concerns."""
        count = 0
        for rec in records:
            payload_hash = rec.get("payload_hash")
            if payload_hash and self.quarantine_port.update_status(
                payload_hash, QuarantineRecordStatus.REPROCESSED
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
        self,
        pipeline: str,
        older_than_days: int = 30,
    ) -> int:
        """Purge old quarantine records.

        Removes quarantine records older than the specified age.
        Implements RULES.md §2.6 - 30-day retention policy.

        Args:
            pipeline: Pipeline name.
            older_than_days: Records older than this will be purged (default 30).

        Returns:
            Number of records deleted.
        """
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
        self,
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
        self,
        payload_hash: str,
        new_status: QuarantineRecordStatus,
    ) -> bool:
        """Update DQ status for a quarantined record.

        Used to mark records as IGNORED, REVIEWED, or REPROCESSED
        after manual inspection.

        Args:
            payload_hash: Hash of the payload to identify the record.
            new_status: New status to set.

        Returns:
            True if record was found and updated, False otherwise.
        """
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
        self,
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

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.quarantine_port.aclose()
