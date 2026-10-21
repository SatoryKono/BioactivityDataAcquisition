"""Skip quarantine appends whose entry id is already stored for the batch."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

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
    """Read entry ids already stored for the batches in this write."""
    if not batch_ids or not DeltaTable.is_deltatable(base_path):
        return set()
    try:
        rows = read_delta_records(
            DeltaTable(base_path),
            columns=["bronze_batch_id", "metadata"],
        )
    except (OSError, TableNotFoundError, ValueError, KeyError, TypeError):
        return set()
    found: set[str] = set()
    for row in rows:
        if str(row.get("bronze_batch_id", "")) not in batch_ids:
            continue
        raw = row.get("metadata")
        if not isinstance(raw, str) or not raw:
            continue
        try:
            meta = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(meta, dict):
            continue
        entry_id = meta.get("entry_id")
        if isinstance(entry_id, str) and entry_id:
            found.add(entry_id)
    return found
