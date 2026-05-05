"""Unit tests for file-backed run-ledger storage."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_SHUTDOWN_EVENT,
    STAGE_COMPLETED_EVENT,
)
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

    assert metrics.increment_counter.call_args_list[0].args == (
        "bioetl_control_plane_ledger_appends_total",
        1,
        {
            "pipeline": "chembl_activity",
            "event_type": "run_finished",
            "status": "success",
        },
    )
    assert metrics.increment_counter.call_args_list[1].args == (
        "bioetl_control_plane_terminal_events_total",
        1,
        {
            "pipeline": "chembl_activity",
            "terminal_status": "success",
        },
    )
    metrics.observe_histogram.assert_called_once()
    args, kwargs = metrics.observe_histogram.call_args
    assert args[0] == "bioetl_control_plane_ledger_append_duration_seconds"
    assert isinstance(args[1], float)
    assert args[2] == {
        "pipeline": "chembl_activity",
        "event_type": "run_finished",
        "status": "success",
    }
    assert kwargs == {}


@pytest.mark.parametrize(
    ("event_type", "status", "terminal_status"),
    [
        (RUN_FAILED_EVENT, "failed", "failed"),
        (RUN_SHUTDOWN_EVENT, "shutdown", "shutdown"),
    ],
)
def test_file_store_emits_terminal_metric_for_all_terminal_outcomes(
    tmp_path,
    event_type: str,
    status: str,
    terminal_status: str,
) -> None:
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
        event_type=event_type,
        occurred_at=_FIXED_TIME,
        status=status,
        details={"_diagnostic": {"pipeline": "chembl_activity"}},
    )

    store.append(entry)

    assert metrics.increment_counter.call_args_list[1].args == (
        "bioetl_control_plane_terminal_events_total",
        1,
        {
            "pipeline": "chembl_activity",
            "terminal_status": terminal_status,
        },
    )


def test_file_store_noops_duplicate_idempotency_key_without_terminal_recount(
    tmp_path,
) -> None:
    metrics = MagicMock()
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(
        base_path=tmp_path / "run_ledger",
        metrics=metrics,
    )
    first = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=_FIXED_TIME,
        status="success",
        idempotency_key="sha256:logical-event",
        details={"_diagnostic": {"pipeline": "chembl_activity"}},
    )
    retry = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=datetime(2025, 1, 1, 12, 1, tzinfo=UTC),
        status="success",
        idempotency_key="sha256:logical-event",
        details={"_diagnostic": {"pipeline": "chembl_activity"}},
    )

    store.append(first)
    run_index_path = tmp_path / "run_ledger" / "_by_run_id" / f"{run_id}.txt"
    run_index_path.unlink()
    metrics.reset_mock()
    store.append(retry)

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_ledger_appends_total",
        1,
        {
            "pipeline": "chembl_activity",
            "event_type": "run_finished",
            "status": "duplicate",
        },
    )
    metrics.observe_histogram.assert_called_once()
    args, kwargs = metrics.observe_histogram.call_args
    assert args[0] == "bioetl_control_plane_ledger_append_duration_seconds"
    assert isinstance(args[1], float)
    assert args[2] == {
        "pipeline": "chembl_activity",
        "event_type": "run_finished",
        "status": "duplicate",
    }
    assert kwargs == {}
    metrics.reset_mock()

    ledger_path = tmp_path / "run_ledger" / "manifest-1.jsonl"
    assert len(ledger_path.read_text(encoding="utf-8").splitlines()) == 1
    assert store.list_entries("manifest-1") == [first]
    assert store.list_entries_by_run_id(run_id) == [first]


def test_file_store_does_not_emit_terminal_metric_for_non_terminal_events(
    tmp_path,
) -> None:
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
        event_type=STAGE_COMPLETED_EVENT,
        occurred_at=_FIXED_TIME,
        status="completed",
        stage="execute_pipeline",
        details={"_diagnostic": {"pipeline": "chembl_activity"}},
    )

    store.append(entry)

    assert metrics.increment_counter.call_args_list == [
        call(
            "bioetl_control_plane_ledger_appends_total",
            1,
            {
                "pipeline": "chembl_activity",
                "event_type": "stage_completed",
                "status": "success",
            },
        )
    ]


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


def test_file_store_emits_ledger_append_failure_metric(tmp_path, monkeypatch) -> None:
    metrics = MagicMock()
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(
        base_path=tmp_path / "run_ledger",
        metrics=metrics,
    )
    entry = RunLedgerEntry(
        entry_id="entry-failed",
        manifest_id="manifest-failed",
        run_id=run_id,
        event_type="stage_completed",
        occurred_at=_FIXED_TIME,
        status="completed",
        details={"_diagnostic": {"pipeline": "chembl_activity"}},
    )

    monkeypatch.setattr(
        "bioetl.infrastructure.control_plane.file_run_ledger_store.atomic_write_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("index write failed")),
    )

    with pytest.raises(StorageError, match="Run ledger append failed"):
        store.append(entry)

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_ledger_appends_total",
        1,
        {
            "pipeline": "chembl_activity",
            "event_type": "stage_completed",
            "status": "failed",
        },
    )
    metrics.observe_histogram.assert_called_once()
    args, kwargs = metrics.observe_histogram.call_args
    assert args[0] == "bioetl_control_plane_ledger_append_duration_seconds"
    assert isinstance(args[1], float)
    assert args[2] == {
        "pipeline": "chembl_activity",
        "event_type": "stage_completed",
        "status": "failed",
    }
    assert kwargs == {}


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


def test_file_store_rejects_run_id_remap_to_different_manifest(tmp_path) -> None:
    run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    first = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-original",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )
    conflicting = RunLedgerEntry(
        entry_id="entry-2",
        manifest_id="manifest-conflicting",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )

    store.append(first)

    with pytest.raises(StorageError, match="already mapped to a different manifest_id"):
        store.append(conflicting)

    assert store.list_entries("manifest-original") == [first]
    assert store.list_entries("manifest-conflicting") == []
    assert store.list_entries_by_run_id(run_id) == [first]


def test_file_store_fails_closed_when_manifest_ledger_contains_multiple_run_ids(
    tmp_path,
) -> None:
    run_id = RunID(uuid4())
    other_run_id = RunID(uuid4())
    store = FileRunLedgerStore(base_path=tmp_path / "run_ledger")
    first = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="manifest_created",
        occurred_at=_FIXED_TIME,
        status="created",
    )

    store.append(first)
    ledger_path = tmp_path / "run_ledger" / "manifest-1.jsonl"
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                RunLedgerEntry(
                    entry_id="entry-2",
                    manifest_id="manifest-1",
                    run_id=other_run_id,
                    event_type="run_started",
                    occurred_at=_FIXED_TIME,
                    status="running",
                ).to_dict(),
                sort_keys=True,
            )
            + "\n"
        )

    with pytest.raises(StorageError, match="multiple run_id values"):
        store.list_entries("manifest-1")

    with pytest.raises(StorageError, match="multiple run_id values"):
        store.list_entries_by_run_id(run_id)


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
