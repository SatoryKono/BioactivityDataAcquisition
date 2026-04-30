"""Private support mixin for filtered and admin quarantine operations."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core._quarantine_support import (
    FILTERED_OUT_SILVER,
    build_filtered_quarantine_request,
    record_filtered_quarantine_metrics,
    write_quarantine_request_with_events,
    write_quarantine_requests_with_events,
)

if TYPE_CHECKING:
    from bioetl.application.core.quarantine_manager import FilteredQuarantineEntry
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.domain.ports import MetricsPort, QuarantinePort
    from bioetl.domain.types import BatchID, JsonDict, RunID


class QuarantineManagerSupportMixin:
    """Own filtered-record and inspection helpers outside the main service shell."""

    _pipeline_name: str
    _quarantine: QuarantinePort
    _domain_event_emitter: DomainEventEmitterProtocol | None
    _metrics: MetricsPort | None
    _batch_metrics: BatchMetricsRecorderService | None
    _pipeline_metrics: PipelineMetricsRecorder

    async def quarantine_filtered_record(
        self,
        record: JsonDict,
        batch_id: BatchID,
        error_details: str,
        run_id: RunID | None = None,
        *,
        details: JsonDict | None = None,
        ingestion_ts: datetime,
    ) -> None:
        request = build_filtered_quarantine_request(
            pipeline_name=self._pipeline_name,
            record=record,
            reason=error_details,
            details=details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        await write_quarantine_request_with_events(
            quarantine=self._quarantine,
            request=request,
            emitter=self._domain_event_emitter,
            pipeline_name=self._pipeline_name,
            error_code=FILTERED_OUT_SILVER,
            error_message=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        record_filtered_quarantine_metrics(
            metrics=self._metrics,
            pipeline_metrics=self._pipeline_metrics,
            count=1,
        )

    async def quarantine_filtered_records(
        self,
        records: list[FilteredQuarantineEntry],
        batch_id: BatchID,
        run_id: RunID | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        if not records:
            return

        write_requests = [
            build_filtered_quarantine_request(
                pipeline_name=self._pipeline_name,
                record=entry.record,
                reason=entry.reason,
                details=entry.details,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
            )
            for entry in records
        ]
        await write_quarantine_requests_with_events(
            quarantine=self._quarantine,
            requests=write_requests,
            emitter=self._domain_event_emitter,
            pipeline_name=self._pipeline_name,
            error_codes=tuple(FILTERED_OUT_SILVER for _ in records),
            error_messages=tuple(entry.reason for entry in records),
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        record_filtered_quarantine_metrics(
            metrics=self._metrics,
            pipeline_metrics=self._pipeline_metrics,
            count=len(records),
        )

    async def inspect(
        self,
        limit: int = 100,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> list[JsonDict]:
        return list(
            await self._quarantine.inspect(
                pipeline=self._pipeline_name,
                limit=limit,
                error_code=error_code,
                run_id=run_id,
            )
        )

    async def get_stats(
        self,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> JsonDict:
        return {
            **await self._quarantine.get_stats(
                self._pipeline_name,
                error_code,
                run_id,
            )
        }
