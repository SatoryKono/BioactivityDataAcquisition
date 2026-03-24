"""Unit tests for file-backed run-ledger storage."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileRunLedgerStore


def test_file_store_round_trips_entries_by_manifest_and_run_id(tmp_path) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    first = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=datetime.now(UTC),
        status="created",
    )
    second = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=datetime.now(UTC),
        status="success",
        metrics_snapshot={"records_fetched": 5},
    )

    store.append(first)
    store.append(second)

    assert store.list_entries("manifest-1") == [first, second]
    assert store.list_entries_by_run_id(run_id) == [first, second]
