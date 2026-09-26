"""File-based audit logging adapter."""

from __future__ import annotations

__all__ = ["FileAuditAdapter"]

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import AuditEntry, AuditLayer
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.audit._file_audit_io import FileAuditIOMixin

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID


_AUDIT_STATUS_ATTRIBUTE = "bioetl.audit.status"
_AUDIT_ADAPTER_CLOSED_MESSAGE = "FileAuditAdapter has been closed"


class FileAuditAdapter(FileAuditIOMixin):
    """File-based implementation of the audit port."""

    TRACER_NAME = "bioetl.audit"
    AUDIT_WRITE_EVENTS_TOTAL = "bioetl_audit_write_events_total"
    AUDIT_WRITE_DURATION_SECONDS = "bioetl_audit_write_duration_seconds"
    AUDIT_QUERY_EVENTS_TOTAL = "bioetl_audit_query_events_total"
    AUDIT_QUERY_DURATION_SECONDS = "bioetl_audit_query_duration_seconds"

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        tracing: TracingPort | None = None,
    ) -> None:
        """Initialize file audit adapter."""
        self.base_path = Path(base_path)
        self.logger = logger
        self.metrics = metrics if metrics is not None else NoOpMetrics()
        self.tracing = tracing if tracing is not None else NoOpTracing()
        self._tracer = self.tracing.get_tracer(self.TRACER_NAME)
        self._closed = False

    def _emit_write_metrics(
        self,
        *,
        layer: AuditLayer,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        labels = {
            "layer": layer.value,
            "operation": operation,
            "status": status,
        }
        self.metrics.increment_counter(self.AUDIT_WRITE_EVENTS_TOTAL, 1, labels=labels)
        self.metrics.observe_histogram(
            self.AUDIT_WRITE_DURATION_SECONDS,
            duration_seconds,
            labels=labels,
        )

    def _emit_query_metrics(
        self,
        *,
        layer_filter: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        labels = {
            "layer_filter": layer_filter,
            "status": status,
        }
        self.metrics.increment_counter(self.AUDIT_QUERY_EVENTS_TOTAL, 1, labels=labels)
        self.metrics.observe_histogram(
            self.AUDIT_QUERY_DURATION_SECONDS,
            duration_seconds,
            labels=labels,
        )

    async def log_write(self, entry: AuditEntry) -> None:
        """Log a write operation to the audit trail."""
        if self._closed:
            raise RuntimeError(_AUDIT_ADAPTER_CLOSED_MESSAGE)
        started = time.perf_counter()
        with self._tracer.start_as_current_span("audit.log_write") as span:
            span.set_attribute("bioetl.audit.layer", entry.layer.value)
            span.set_attribute("bioetl.audit.operation", entry.operation.value)
            span.set_attribute("bioetl.audit.records_count", entry.records_count)
            try:
                await asyncio.to_thread(self._write_entry_sync, entry)
            except OSError as exc:
                duration_seconds = time.perf_counter() - started
                self._emit_write_metrics(
                    layer=entry.layer,
                    operation=entry.operation.value,
                    status="error",
                    duration_seconds=duration_seconds,
                )
                span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "error")
                span.record_exception(exc)
                raise

            duration_seconds = time.perf_counter() - started
            self._emit_write_metrics(
                layer=entry.layer,
                operation=entry.operation.value,
                status="success",
                duration_seconds=duration_seconds,
            )
            span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "success")

        self.logger.debug(
            "audit_entry_logged",
            run_id=str(entry.run_id),
            layer=entry.layer.value,
            table=entry.table_name,
            operation=entry.operation.value,
            records_count=entry.records_count,
        )

    async def log_event(
        self,
        event_name: str,
        event_data: JsonDict | None = None,
        *,
        timestamp: datetime,
    ) -> None:
        """Log a non-write lifecycle event to the audit trail."""
        if self._closed:
            raise RuntimeError(_AUDIT_ADAPTER_CLOSED_MESSAGE)
        with self._tracer.start_as_current_span("audit.log_event") as span:
            span.set_attribute("bioetl.audit.event_name", event_name)
            try:
                await asyncio.to_thread(
                    self._write_event_sync,
                    event_name,
                    event_data,
                    timestamp,
                )
            except OSError as exc:
                span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "error")
                span.record_exception(exc)
                raise
            span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "success")

        self.logger.debug(
            "audit_event_logged",
            event_name=event_name,
            event_data=event_data or {},
        )

    async def get_entries(
        self,
        run_id: RunID | None = None,
        layer: AuditLayer | None = None,
        table_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters."""
        if self._closed:
            raise RuntimeError(_AUDIT_ADAPTER_CLOSED_MESSAGE)
        started = time.perf_counter()
        layer_filter = layer.value if layer is not None else "all"
        with self._tracer.start_as_current_span("audit.get_entries") as span:
            span.set_attribute("bioetl.audit.layer_filter", layer_filter)
            span.set_attribute("bioetl.audit.has_run_filter", run_id is not None)
            span.set_attribute("bioetl.audit.has_table_filter", table_name is not None)
            span.set_attribute(
                "bioetl.audit.has_time_range",
                start_time is not None or end_time is not None,
            )
            span.set_attribute("bioetl.audit.limit", limit)
            try:
                entries = await asyncio.to_thread(
                    self._read_entries_sync,
                    run_id,
                    layer,
                    table_name,
                    start_time,
                    end_time,
                    limit,
                )
            except OSError as exc:
                duration_seconds = time.perf_counter() - started
                self._emit_query_metrics(
                    layer_filter=layer_filter,
                    status="error",
                    duration_seconds=duration_seconds,
                )
                span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "error")
                span.record_exception(exc)
                raise

            duration_seconds = time.perf_counter() - started
            self._emit_query_metrics(
                layer_filter=layer_filter,
                status="success",
                duration_seconds=duration_seconds,
            )
            span.set_attribute("bioetl.audit.entries_count", len(entries))
            span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "success")
            return entries

    async def aclose(self) -> None:
        """Gracefully close the audit adapter."""
        await asyncio.sleep(0)
        with self._tracer.start_as_current_span("audit.close") as span:
            span.set_attribute("bioetl.audit.already_closed", self._closed)
            if self._closed:
                return

            self._closed = True
            span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "success")
            self.logger.debug("audit_adapter_closed")
