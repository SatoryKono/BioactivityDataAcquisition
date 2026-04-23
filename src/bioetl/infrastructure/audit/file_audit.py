"""File-based audit logging adapter.

Implements AuditPort using JSON Lines format for audit trail storage.
Each audit entry is written as a single line of JSON to enable efficient
append operations and streaming reads.

Path structure:
    audit/
    └── audit_YYYY-MM-DD.jsonl

Requirements:
- REQ-AUDIT-001: Each write operation must be logged
- REQ-AUDIT-002: Audit log must contain run_id, timestamp, records_count, table
"""

from __future__ import annotations

__all__ = ["FileAuditAdapter"]


import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import AuditEntry, AuditLayer
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict

from ._file_audit_readers import process_audit_file

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID

from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing

_AUDIT_STATUS_ATTRIBUTE = "bioetl.audit.status"
_AUDIT_ADAPTER_CLOSED_MESSAGE = "FileAuditAdapter has been closed"


class FileAuditAdapter:
    """File-based implementation of AuditPort.

    Writes audit entries to daily JSON Lines files in the configured
    audit directory. Each entry is appended atomically to prevent
    data loss on concurrent writes.

    Example:
        >>> adapter = FileAuditAdapter(Path("./data/audit"), logger)
        >>> await adapter.log_write(entry)
        >>> entries = await adapter.get_entries(run_id=run_id)

    Implements:
        AuditPort: Domain port for audit logging.
    """

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
        """Initialize file audit adapter.

        Args:
            base_path: Directory path for audit log files.
            logger: Structured logger for observability.
        """
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

    def _get_audit_file_path(self, date: datetime) -> Path:
        """Get the audit file path for a specific date.

        Args:
            date: The date for the audit file.

        Returns:
            Path to the audit file for the given date.
        """
        date_str = date.strftime("%Y-%m-%d")
        return self.base_path / f"audit_{date_str}.jsonl"

    def _get_event_file_path(self, date: datetime) -> Path:
        """Get the audit event file path for a specific date."""
        date_str = date.strftime("%Y-%m-%d")
        return self.base_path / f"events_{date_str}.jsonl"

    def _ensure_directory(self) -> None:
        """Ensure the audit directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _write_entry_sync(self, entry: AuditEntry) -> None:
        """Synchronously write an entry to the audit file.

        Args:
            entry: The audit entry to write.
        """
        self._ensure_directory()
        file_path = self._get_audit_file_path(entry.timestamp)

        # Convert entry to JSON line
        json_line = serialize_to_json(entry.to_dict(), sort_keys=True) + "\n"

        # Append atomically using exclusive create + append mode
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json_line)
            f.flush()

    def _write_event_sync(
        self,
        event_name: str,
        event_data: JsonDict | None,
        timestamp: datetime,
    ) -> None:
        self._ensure_directory()
        file_path = self._get_event_file_path(timestamp)
        payload = {
            "event_name": event_name,
            "event_data": event_data or {},
            "timestamp": timestamp.isoformat(),
        }
        json_line = serialize_to_json(payload, sort_keys=True) + "\n"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json_line)
            f.flush()

    async def log_write(self, entry: AuditEntry) -> None:
        """Log a write operation to the audit trail.

        Args:
            entry: The audit entry containing operation details.

        Raises:
            RuntimeError: If the adapter has been closed.
            OSError: If the file write fails.
        """
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

    def log_event(
        self,
        event_name: str,
        event_data: JsonDict | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Log a non-write lifecycle event to the audit trail."""
        if self._closed:
            raise RuntimeError(_AUDIT_ADAPTER_CLOSED_MESSAGE)
        timestamp = timestamp or datetime.now(UTC)
        with self._tracer.start_as_current_span("audit.log_event") as span:
            span.set_attribute("bioetl.audit.event_name", event_name)
            try:
                self._write_event_sync(event_name, event_data, timestamp)
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

    def _read_entries_sync(
        self,
        run_id: RunID | None,
        layer: AuditLayer | None,
        table_name: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
    ) -> list[AuditEntry]:
        """Synchronously read and filter audit entries.

        Args:
            run_id: Filter by pipeline run ID.
            layer: Filter by Medallion layer.
            table_name: Filter by target table name.
            start_time: Filter entries after this time.
            end_time: Filter entries before this time.
            limit: Maximum number of entries to return.

        Returns:
            List of matching audit entries.
        """
        entries: list[AuditEntry] = []

        if not self.base_path.exists():
            return entries

        audit_files = sorted(self.base_path.glob("audit_*.jsonl"), reverse=True)

        for file_path in audit_files:
            if len(entries) >= limit:
                break
            file_entries = process_audit_file(
                file_path,
                run_id,
                layer,
                table_name,
                start_time,
                end_time,
                limit,
                len(entries),
            )
            entries.extend(file_entries)

        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    async def get_entries(
        self,
        run_id: RunID | None = None,
        layer: AuditLayer | None = None,
        table_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters.

        Args:
            run_id: Filter by pipeline run ID.
            layer: Filter by Medallion layer.
            table_name: Filter by target table name.
            start_time: Filter entries after this time.
            end_time: Filter entries before this time.
            limit: Maximum number of entries to return.

        Returns:
            List of matching audit entries, ordered by timestamp descending.

        Raises:
            RuntimeError: If the adapter has been closed.
        """
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
        """Gracefully close the audit adapter.

        This method is idempotent (safe to call multiple times).
        """
        await asyncio.sleep(0)
        with self._tracer.start_as_current_span("audit.close") as span:
            span.set_attribute("bioetl.audit.already_closed", self._closed)
            if self._closed:
                return

            self._closed = True
            span.set_attribute(_AUDIT_STATUS_ATTRIBUTE, "success")
            self.logger.debug("audit_adapter_closed")
