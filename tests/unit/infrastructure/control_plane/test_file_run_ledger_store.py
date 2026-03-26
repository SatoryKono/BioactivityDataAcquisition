"""Unit tests for file-backed run-ledger storage."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
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
        dataset_ref="gold:chembl.activity",
        lineage_fragment_id="gold:fragment-1",
        metrics_snapshot={"records_fetched": 5},
    )

    store.append(first)
    store.append(second)

    assert store.list_entries("manifest-1") == [first, second]
    assert store.list_entries_by_run_id(run_id) == [first, second]


def test_file_store_emits_ledger_append_metric(tmp_path) -> None:
    metrics = MagicMock()
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(
        base_path=tmp_path / "run_ledger",
        metrics=metrics,
    )
    entry = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=datetime.now(UTC),
        status="success",
        details={"_diagnostic": {"pipeline": "chembl_activity"}},
    )

    store.append(entry)

    metrics.increment_counter.assert_called_once_with(
        "control_plane_ledger_appends_total",
        1,
        {
            "pipeline": "chembl_activity",
            "event_type": "run_finished",
            "status": "success",
        },
    )
