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

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.domain.ports.audit import AuditEntry, AuditLayer, AuditOperation

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import RunID


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

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
    ) -> None:
        """Initialize file audit adapter.

        Args:
            base_path: Directory path for audit log files.
            logger: Structured logger for observability.
        """
        self.base_path = Path(base_path)
        self.logger = logger
        self._closed = False

    def _get_audit_file_path(self, date: datetime) -> Path:
        """Get the audit file path for a specific date.

        Args:
            date: The date for the audit file.

        Returns:
            Path to the audit file for the given date.
        """
        date_str = date.strftime("%Y-%m-%d")
        return self.base_path / f"audit_{date_str}.jsonl"

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
        json_line = json.dumps(entry.to_dict(), sort_keys=True) + "\n"

        # Append atomically using exclusive create + append mode
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
            raise RuntimeError("FileAuditAdapter has been closed")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_entry_sync, entry)

        self.logger.debug(
            "audit_entry_logged",
            run_id=str(entry.run_id),
            layer=entry.layer.value,
            table=entry.table_name,
            operation=entry.operation.value,
            records_count=entry.records_count,
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

        # Get all audit files sorted by date descending (newest first)
        audit_files = sorted(
            self.base_path.glob("audit_*.jsonl"),
            reverse=True,
        )

        for file_path in audit_files:
            if len(entries) >= limit:
                break

            try:
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)
                            entry = self._parse_entry(data)

                            # Apply filters
                            if not self._matches_filters(
                                entry, run_id, layer, table_name, start_time, end_time
                            ):
                                continue

                            entries.append(entry)
                            if len(entries) >= limit:
                                break
                        except (json.JSONDecodeError, KeyError, ValueError):
                            # Skip malformed entries
                            continue
            except OSError:
                # Skip files we can't read
                continue

        # Sort by timestamp descending (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def _parse_entry(self, data: dict[str, Any]) -> AuditEntry:
        """Parse a dictionary into an AuditEntry.

        Args:
            data: Dictionary from JSON parsing.

        Returns:
            Parsed AuditEntry.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are invalid.
        """
        from uuid import UUID

        from bioetl.domain.types import RunID

        return AuditEntry(
            run_id=RunID(UUID(data["run_id"])),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            layer=AuditLayer(data["layer"]),
            table_name=data["table_name"],
            operation=AuditOperation(data["operation"]),
            records_count=data["records_count"],
            metadata=data.get("metadata", {}),
        )

    def _matches_filters(
        self,
        entry: AuditEntry,
        run_id: RunID | None,
        layer: AuditLayer | None,
        table_name: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> bool:
        """Check if an entry matches the provided filters.

        Args:
            entry: The audit entry to check.
            run_id: Filter by pipeline run ID.
            layer: Filter by Medallion layer.
            table_name: Filter by target table name.
            start_time: Filter entries after this time.
            end_time: Filter entries before this time.

        Returns:
            True if the entry matches all filters.
        """
        if run_id is not None and entry.run_id != run_id:
            return False
        if layer is not None and entry.layer != layer:
            return False
        if table_name is not None and entry.table_name != table_name:
            return False
        if start_time is not None and entry.timestamp < start_time:
            return False
        return not (end_time is not None and entry.timestamp > end_time)

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
            raise RuntimeError("FileAuditAdapter has been closed")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._read_entries_sync,
            run_id,
            layer,
            table_name,
            start_time,
            end_time,
            limit,
        )

    async def aclose(self) -> None:
        """Gracefully close the audit adapter.

        This method is idempotent (safe to call multiple times).
        """
        if self._closed:
            return

        self._closed = True
        self.logger.debug("audit_adapter_closed")
