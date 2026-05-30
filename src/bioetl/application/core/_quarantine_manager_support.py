"""Private support mixin for filtered and admin quarantine operations."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core._quarantine_support import (
    QuarantineRuntimeDependencies,
    build_dq_quarantine_request,
    build_filtered_quarantine_request,
    build_quarantine_runtime_ports,
    persist_dq_quarantine_request,
    persist_dq_quarantine_requests,
    persist_filtered_quarantine_request,
    persist_filtered_quarantine_requests,
)
from bioetl.domain.types import BatchID, ErrorType, JsonDict, RunID

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )
    from bioetl.domain.ports import MetricsPort, QuarantinePort
    from bioetl.domain.types import BronzeRecord


class _DqQuarantineEntryProtocol(Protocol):
    """Structural DQ-entry shape used by the support mixin."""

    record: BronzeRecord
    error_type: ErrorType
    error_details: str


class _FilteredQuarantineEntryProtocol(Protocol):
    """Structural filtered-entry shape used by the support mixin."""

    record: JsonDict
    reason: str
    details: JsonDict | None


class QuarantineManagerSupportMixin:
    """Own filtered-record and inspection helpers outside the main service shell."""

    _pipeline_name: str
    _quarantine: QuarantinePort
    _domain_event_emitter: DomainEventEmitterProtocol | None
    _metrics: MetricsPort | None
    _batch_metrics: BatchMetricsRecorderService | None
    _pipeline_metrics: PipelineMetricsRecorder
    _run_type: str

    def _quarantine_runtime_ports(self) -> QuarantineRuntimeDependencies:
        return build_quarantine_runtime_ports(
            quarantine=self._quarantine,
            emitter=self._domain_event_emitter,
            pipeline_name=self._pipeline_name,
            metrics=self._metrics,
            pipeline_metrics=self._pipeline_metrics,
            batch_metrics=self._batch_metrics,
            run_type=getattr(self, "_run_type", "unknown"),
        )

    async def quarantine_record(
        self,
        record: JsonDict,
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
        run_id: RunID | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        request = build_dq_quarantine_request(
            pipeline_name=self._pipeline_name,
            record=record,
            error_type=error_type,
            error_details=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        await persist_dq_quarantine_request(
            self._quarantine_runtime_ports(),
            request=request,
            error_type=error_type,
            error_details=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

    async def quarantine_records(
        self,
        records: list[_DqQuarantineEntryProtocol],
        batch_id: BatchID,
        run_id: RunID | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        if not records:
            return

        write_requests = [
            build_dq_quarantine_request(
                pipeline_name=self._pipeline_name,
                record=record,
                error_type=error_type,
                error_details=error_details,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
            )
            for record, error_type, error_details in records
        ]
        await persist_dq_quarantine_requests(
            self._quarantine_runtime_ports(),
            requests=write_requests,
            records=records,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

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
        await persist_filtered_quarantine_request(
            self._quarantine_runtime_ports(),
            request=request,
            error_details=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

    async def quarantine_filtered_records(
        self,
        records: list[_FilteredQuarantineEntryProtocol],
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
        await persist_filtered_quarantine_requests(
            self._quarantine_runtime_ports(),
            requests=write_requests,
            reasons=tuple(entry.reason for entry in records),
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
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
