"""Unit tests for file-backed workflow-ledger storage."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import bioetl.infrastructure.control_plane.file_workflow_ledger_store as workflow_ledger_module
from bioetl.domain.control_plane import WorkflowLedgerEntry
from bioetl.domain.control_plane.workflow_ledger import WORKFLOW_STARTED_EVENT
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileWorkflowLedgerStore
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def test_file_workflow_ledger_round_trips_by_manifest_and_run_id(tmp_path) -> None:
    workflow_run_id = RunID(
        deterministic_uuid_value("workflow_ledger_store.round_trip")
    )
    entry = WorkflowLedgerEntry(
        entry_id="workflow-entry-1",
        manifest_id="workflow-manifest-1",
        workflow_run_id=workflow_run_id,
        event_type=WORKFLOW_STARTED_EVENT,
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        status="running",
    )
    store = FileWorkflowLedgerStore(base_path=tmp_path / "workflow_ledger")

    store.append(entry)

    assert store.list_entries("workflow-manifest-1") == [entry]
    assert store.list_entries_by_run_id(workflow_run_id) == [entry]


def test_append_jsonl_payload_uses_control_plane_flush_policy(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flush_calls: list[int] = []

    monkeypatch.setattr(
        workflow_ledger_module,
        "flush_control_plane_file_descriptor",
        flush_calls.append,
    )

    workflow_ledger_module._append_jsonl_payload(
        tmp_path / "workflow" / "manifest-1.jsonl",
        b'{"entry_id":"entry-1"}\n',
    )

    assert len(flush_calls) == 1
