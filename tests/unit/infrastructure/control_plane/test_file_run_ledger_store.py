"""Unit tests for file-backed run-ledger storage."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.exceptions import StorageError
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileRunLedgerStore

_FIXED_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


def test_file_store_round_trips_entries_by_manifest_and_run_id(tmp_path) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    first = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )
    second = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=_FIXED_TIME,
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
        occurred_at=_FIXED_TIME,
        status="success",
        details={"_diagnostic": {"pipeline": "chembl_activity"}},
    )

    store.append(entry)

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_ledger_appends_total",
        1,
        {
            "pipeline": "chembl_activity",
            "event_type": "run_finished",
            "status": "success",
        },
    )


def test_file_store_emits_ledger_read_metric_on_list_success(tmp_path) -> None:
    metrics = MagicMock()
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(
        base_path=tmp_path / "run_ledger",
        metrics=metrics,
    )
    entry = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-2",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=_FIXED_TIME,
        status="success",
    )

    store.append(entry)
    metrics.reset_mock()

    assert store.list_entries("manifest-2") == [entry]

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "ledger",
            "operation": "list_entries",
            "status": "success",
        },
    )
    metrics.observe_histogram.assert_called_once()


def test_file_store_emits_ledger_read_metric_on_miss(tmp_path) -> None:
    metrics = MagicMock()
    store = FileRunLedgerStore(
        base_path=tmp_path / "run_ledger",
        metrics=metrics,
    )

    assert store.list_entries("missing-manifest") == []

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "ledger",
            "operation": "list_entries",
            "status": "miss",
        },
    )
    metrics.observe_histogram.assert_called_once()


def test_file_store_preserves_append_only_jsonl_order(tmp_path) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    first = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-append-only",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )
    second = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-append-only",
        run_id=run_id,
        event_type="run_started",
        occurred_at=_FIXED_TIME,
        status="running",
    )

    store.append(first)
    store.append(second)

    ledger_path = tmp_path / "run_ledger" / "manifest-append-only.jsonl"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["entry_id"] == "entry-1"
    assert json.loads(lines[1])["entry_id"] == "entry-2"
    assert store.list_entries("manifest-append-only") == [first, second]


def test_file_store_wraps_partial_append_failure_and_preserves_existing_events(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial_run_id = RunID(uuid4())
    failed_run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    initial = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=initial_run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )
    failed = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-1",
        run_id=failed_run_id,
        event_type="run_finished",
        occurred_at=_FIXED_TIME,
        status="failed",
    )

    store.append(initial)

    original_write = os.write
    state = {"calls": 0}

    def _partial_write_then_fail(fd: int, payload: bytes) -> int:
        state["calls"] += 1
        if state["calls"] == 1:
            chunk = max(1, len(payload) // 2)
            return original_write(fd, payload[:chunk])
        raise OSError("simulated partial append failure")

    monkeypatch.setattr(
        "bioetl.infrastructure.control_plane.file_run_ledger_store.os.write",
        _partial_write_then_fail,
    )

    with pytest.raises(StorageError) as exc_info:
        store.append(failed)

    assert "Run ledger append failed" in str(exc_info.value)
    assert exc_info.value.operation == "append"
    assert exc_info.value.manifest_id == "manifest-1"
    assert store.list_entries("manifest-1") == [initial]
    assert store.list_entries_by_run_id(initial_run_id) == [initial]
    assert store.list_entries_by_run_id(failed_run_id) == []


def test_file_store_rolls_back_ledger_append_when_run_index_write_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    entry = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=_FIXED_TIME,
        status="success",
    )

    def _raise_index_failure(*args: object, **kwargs: object) -> None:
        raise OSError("index write failed")

    monkeypatch.setattr(
        "bioetl.infrastructure.control_plane.file_run_ledger_store.atomic_write_text",
        _raise_index_failure,
    )

    with pytest.raises(StorageError) as exc_info:
        store.append(entry)

    assert "Run ledger append failed" in str(exc_info.value)
    assert store.list_entries("manifest-1") == []
    assert store.list_entries_by_run_id(run_id) == []


def test_file_store_fails_closed_on_truncated_tail_line_during_reads(tmp_path) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    entry = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )

    store.append(entry)
    ledger_path = tmp_path / "run_ledger" / "manifest-1.jsonl"
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write('{"entry_id":"broken-tail"')

    with pytest.raises(
        StorageError, match="corrupted: truncated tail line"
    ) as exc_info:
        store.list_entries("manifest-1")
    assert exc_info.value.operation == "list_entries"
    assert exc_info.value.manifest_id == "manifest-1"

    with pytest.raises(
        StorageError, match="corrupted: truncated tail line"
    ) as run_id_exc:
        store.list_entries_by_run_id(run_id)
    assert run_id_exc.value.operation == "list_entries_by_run_id"
    assert run_id_exc.value.run_id == str(run_id)

    with pytest.raises(
        StorageError, match="corrupted: truncated tail line"
    ) as after_exc:
        store.list_entries_after("manifest-1", None)
    assert after_exc.value.operation == "list_entries_after"
    assert after_exc.value.manifest_id == "manifest-1"


def test_file_store_fails_closed_on_invalid_json_line_during_reads(tmp_path) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    entry = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )

    store.append(entry)
    ledger_path = tmp_path / "run_ledger" / "manifest-1.jsonl"
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    with pytest.raises(StorageError, match="corrupted at line 2"):
        store.list_entries("manifest-1")


def test_file_store_lists_entries_after_watermark(tmp_path) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    first = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )
    second = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="stage_completed",
        occurred_at=_FIXED_TIME,
        status="completed",
    )
    third = RunLedgerEntry(
        entry_id="entry-3",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=_FIXED_TIME,
        status="success",
    )

    store.append(first)
    store.append(second)
    store.append(third)

    assert store.list_entries_after("manifest-1", None) == [first, second, third]
    assert store.list_entries_after("manifest-1", "entry-1") == [second, third]
    assert store.list_entries_after("manifest-1", "entry-3") == []
    with pytest.raises(ValueError):
        store.list_entries_after("manifest-1", "missing")
