"""Internal helpers for reading and filtering JSONL audit files."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.serialization import deserialize_from_json
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.types import RunID


def parse_entry(
    data: JsonDict,  # Any: audit entry fields are heterogeneous
) -> AuditEntry:  # Any: audit entry fields are heterogeneous
    """Parse raw JSON dict payload into an ``AuditEntry``."""
    from uuid import UUID

    from bioetl.domain.types import RunID

    timestamp = datetime.fromisoformat(data["timestamp"])
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    return AuditEntry(
        run_id=RunID(UUID(data["run_id"])),
        timestamp=timestamp,
        layer=AuditLayer(data["layer"]),
        table_name=data["table_name"],
        operation=AuditOperation(data["operation"]),
        records_count=data["records_count"],
        metadata=data.get("metadata", {}),
    )


def matches_filters(
    entry: AuditEntry,
    run_id: RunID | None,
    layer: AuditLayer | None,
    table_name: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
) -> bool:
    """Return ``True`` when entry satisfies all optional filters."""
    if run_id is not None and entry.run_id != run_id:
        return False
    if layer is not None and entry.layer != layer:
        return False
    if table_name is not None and entry.table_name != table_name:
        return False
    if start_time is not None and entry.timestamp < start_time:
        return False
    return not (end_time is not None and entry.timestamp > end_time)


def process_audit_line(
    line: str,
    run_id: RunID | None,
    layer: AuditLayer | None,
    table_name: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
) -> AuditEntry | None:
    """Parse single JSONL line and return matching entry when possible."""
    if not line.strip():
        return None

    try:
        data = deserialize_from_json(line)
        if not isinstance(data, dict):
            return None
        entry = parse_entry(data)
        return (
            entry
            if matches_filters(entry, run_id, layer, table_name, start_time, end_time)
            else None
        )
    except (ValueError, KeyError):
        return None


def process_audit_file(
    file_path: Path,
    run_id: RunID | None,
    layer: AuditLayer | None,
    table_name: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
    limit: int,
    current_count: int,
) -> list[AuditEntry]:
    """Read one JSONL audit file and return filtered entries."""
    entries: list[AuditEntry] = []
    try:
        with open(file_path, encoding="utf-8") as file_obj:
            for line in file_obj:
                entry = process_audit_line(
                    line,
                    run_id,
                    layer,
                    table_name,
                    start_time,
                    end_time,
                )
                if entry is not None:
                    entries.append(entry)
                    if current_count + len(entries) >= limit:
                        break
    except OSError:
        pass  # Why: audit file missing or unreadable; return empty entries list
    return entries
