"""Skip quarantine appends whose entry id is already stored for the batch."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.delta.table_ops import read_delta_records

if TYPE_CHECKING:
    from bioetl.domain.ports import QuarantineWriteRequest

__all__ = ["select_new_quarantine_requests"]


def select_new_quarantine_requests(
    base_path: str,
    records: list[QuarantineWriteRequest],
) -> list[QuarantineWriteRequest]:
    """Drop requests whose entry id was already appended or repeats in-batch.

    Stored ids are read only for the ``bronze_batch_id`` values in this write.
    Metadata JSON for every other batch is left unparsed.
    """
    if not any(_request_entry_id(record) for record in records):
        return records
    batch_ids = {
        str(record["bronze_batch_id"])
        for record in records
        if _request_entry_id(record) is not None
    }
    known = _stored_entry_ids(base_path, batch_ids)
    kept: list[QuarantineWriteRequest] = []
    seen: set[str] = set()
    for record in records:
        entry_id = _request_entry_id(record)
        if entry_id is None:
            kept.append(record)
            continue
        if entry_id in known or entry_id in seen:
            continue
        seen.add(entry_id)
        kept.append(_with_metadata_entry_id(record, entry_id))
    return kept


def _request_entry_id(record: QuarantineWriteRequest) -> str | None:
    """Return a non-empty entry id when the request carries one."""
    raw = record.get("entry_id")
    if isinstance(raw, str) and raw.strip():
        return raw
    return None


def _with_metadata_entry_id(
    record: QuarantineWriteRequest,
    entry_id: str,
) -> QuarantineWriteRequest:
    """Copy ``entry_id`` into metadata so append-only storage can see it."""
    metadata = dict(record.get("metadata") or {})
    if metadata.get("entry_id") == entry_id:
        return record
    metadata["entry_id"] = entry_id
    updated = dict(record)
    updated["metadata"] = metadata
    return cast("QuarantineWriteRequest", updated)


def _stored_entry_ids(base_path: str, batch_ids: set[str]) -> set[str]:
    """Read entry ids already stored for the batches in this write.

    A missing table yields an empty set. Any other read failure propagates so
    a retry cannot append a duplicate while the stored ids are unknown.
    """
    found: set[str] = set()
    for row in _read_stored_metadata_rows(base_path, batch_ids):
        entry_id = _entry_id_for_batch(row, batch_ids)
        if entry_id is not None:
            found.add(entry_id)
    return found


def _read_stored_metadata_rows(
    base_path: str,
    batch_ids: set[str],
) -> list[BronzeRecord]:
    """Load batch id and metadata, or ``[]`` when the table is absent."""
    if not batch_ids or not DeltaTable.is_deltatable(base_path):
        return []
    try:
        return read_delta_records(
            DeltaTable(base_path),
            columns=["bronze_batch_id", "metadata"],
        )
    except TableNotFoundError:
        return []


def _entry_id_for_batch(row: BronzeRecord, batch_ids: set[str]) -> str | None:
    """Return a stored entry id when the row belongs to ``batch_ids``."""
    if str(row.get("bronze_batch_id", "")) not in batch_ids:
        return None
    raw = row.get("metadata")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(meta, dict):
        return None
    entry_id = meta.get("entry_id")
    if isinstance(entry_id, str) and entry_id:
        return entry_id
    return None
