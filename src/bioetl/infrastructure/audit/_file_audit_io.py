# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods provided by concrete composition.
"""Synchronous file operations for ``FileAuditAdapter``."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bioetl.domain.ports import AuditEntry, AuditLayer
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict, RunID
from bioetl.infrastructure.audit._file_audit_payloads import (
    build_canonical_event_payload,
)
from bioetl.infrastructure.audit._file_audit_readers import process_audit_file


class FileAuditIOMixin:
    """Synchronous audit file read/write helpers."""

    base_path: Path

    def _get_audit_file_path(self, date: datetime) -> Path:
        """Get the audit file path for a specific date."""
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
        """Synchronously write an entry to the audit file."""
        self._ensure_directory()
        file_path = self._get_audit_file_path(entry.timestamp)
        json_line = serialize_to_json(entry.to_dict(), sort_keys=True) + "\n"
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
        payload = build_canonical_event_payload(
            event_name=event_name,
            event_data=event_data,
            timestamp=timestamp,
        )
        json_line = serialize_to_json(payload, sort_keys=True) + "\n"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json_line)
            f.flush()

    def _read_entries_sync(
        self,
        run_id: RunID | None,
        layer: AuditLayer | None,
        table_name: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
    ) -> list[AuditEntry]:
        """Synchronously read and filter audit entries."""
        entries: list[AuditEntry] = []
        if not self.base_path.exists():
            return entries
        audit_files = sorted(self.base_path.glob("audit_*.jsonl"), reverse=True)
        for file_path in audit_files:
            if len(entries) >= limit:
                break
            entries.extend(
                process_audit_file(
                    file_path,
                    run_id,
                    layer,
                    table_name,
                    start_time,
                    end_time,
                    limit,
                    len(entries),
                )
            )
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]
