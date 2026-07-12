"""Append-only status event log for immutable quarantine records."""

from __future__ import annotations

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import JsonDict, QuarantineRecordStatus

__all__ = [
    "append_status_event",
    "apply_latest_statuses",
    "status_events_path",
]


def status_events_path(base_path: str) -> str:
    """Return the sibling Delta table path for quarantine status events."""
    return f"{base_path.rstrip('/')}_status_events"


def _load_status_events(
    event_path: str,
    storage_options: dict[str, str] | None,
) -> list[JsonDict]:
    try:
        dt = DeltaTable(event_path, storage_options=storage_options)
    except TableNotFoundError:
        return []
    return dt.to_pyarrow_table().to_pylist()


def _next_status_sequence(
    event_path: str,
    storage_options: dict[str, str] | None,
    payload_hash: str,
) -> int:
    max_sequence = 0
    for row in _load_status_events(event_path, storage_options):
        if str(row.get("payload_hash", "")) != payload_hash:
            continue
        raw_sequence = row.get("status_sequence", 0)
        try:
            sequence = int(raw_sequence)
        except (TypeError, ValueError):
            sequence = 0
        max_sequence = max(max_sequence, sequence)
    return max_sequence + 1


def append_status_event(
    event_path: str,
    storage_options: dict[str, str] | None,
    *,
    payload_hash: str,
    new_status: QuarantineRecordStatus,
) -> None:
    """Append one status transition without mutating the quarantined payload row."""
    row: JsonDict = {
        "payload_hash": payload_hash,
        "dq_status": new_status.value,
        "status_sequence": _next_status_sequence(
            event_path, storage_options, payload_hash
        ),
    }
    arrow_table = pa.Table.from_pylist([row])
    arrow_reader = pa.RecordBatchReader.from_batches(
        arrow_table.schema, arrow_table.to_batches()
    )
    try:
        write_deltalake(
            table_or_uri=event_path,
            data=arrow_reader,
            mode="append",
            storage_options=storage_options,
        )
    except TableNotFoundError:
        arrow_reader = pa.RecordBatchReader.from_batches(
            arrow_table.schema, arrow_table.to_batches()
        )
        write_deltalake(
            table_or_uri=event_path,
            data=arrow_reader,
            mode="overwrite",
            storage_options=storage_options,
        )


def _latest_status_by_payload_hash(
    event_path: str,
    storage_options: dict[str, str] | None,
    payload_hashes: set[str],
) -> dict[str, str]:
    latest_statuses: dict[str, str] = {}
    latest_sequences: dict[str, int] = {}
    for row in _load_status_events(event_path, storage_options):
        payload_hash = str(row.get("payload_hash", ""))
        if not payload_hash or payload_hash not in payload_hashes:
            continue
        dq_status = str(row.get("dq_status", ""))
        if not dq_status:
            continue
        raw_sequence = row.get("status_sequence", 0)
        try:
            sequence = int(raw_sequence)
        except (TypeError, ValueError):
            sequence = 0
        if sequence >= latest_sequences.get(payload_hash, -1):
            latest_sequences[payload_hash] = sequence
            latest_statuses[payload_hash] = dq_status
    return latest_statuses


def apply_latest_statuses(
    records: list[JsonDict],
    event_path: str | None,
    storage_options: dict[str, str] | None,
) -> list[JsonDict]:
    """Return records with the latest append-only status event overlaid."""
    if not records or event_path is None:
        return records
    payload_hashes = {
        str(row.get("payload_hash", ""))
        for row in records
        if str(row.get("payload_hash", ""))
    }
    if not payload_hashes:
        return records
    latest_statuses = _latest_status_by_payload_hash(
        event_path, storage_options, payload_hashes
    )
    if not latest_statuses:
        return records
    overlaid: list[JsonDict] = []
    for row in records:
        updated = dict(row)
        payload_hash = str(updated.get("payload_hash", ""))
        if payload_hash in latest_statuses:
            updated["dq_status"] = latest_statuses[payload_hash]
        overlaid.append(updated)
    return overlaid
