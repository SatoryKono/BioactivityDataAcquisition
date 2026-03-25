"""Unit tests for RunLedgerService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID, RunType


class _InMemoryRunLedgerStore(RunLedgerPort):
    def __init__(self) -> None:
        self._items: list[RunLedgerEntry] = []

    def append(self, entry: RunLedgerEntry) -> None:
        self._items.append(entry)

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.manifest_id == manifest_id]

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.run_id == run_id]


def _make_manifest(run_id: RunID) -> RunManifest:
    return RunManifest(
        manifest_id="manifest-1",
        execution_fingerprint="fingerprint-1",
        schema_version="1.0",
        created_at=datetime.now(UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 100},
        runtime_config={"run_type": "incremental"},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash="deadbeef",
        ),
    )


def test_record_manifest_created_appends_first_control_plane_event() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-1",
    )

    entry = service.record_manifest_created(_make_manifest(run_id))

    assert entry.entry_id == "entry-1"
    assert entry.event_type == "manifest_created"
    assert entry.event_family == "diagnostic"
    assert entry.status == "created"
    assert entry.details == {
        "execution_fingerprint": "fingerprint-1",
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "_diagnostic": {
            "contract_version": "v1",
            "event_type": "manifest_created",
            "event_family": "diagnostic",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "created",
        },
    }
    assert store.list_entries("manifest-1") == [entry]


def test_record_run_failed_captures_message_and_metrics() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-2",
    )

    entry = service.record_run_failed(
        message="boom",
        error_type="RuntimeError",
        metrics_snapshot={"records_fetched": 10},
    )

    assert entry.event_type == "run_failed"
    assert entry.event_family == "pipeline.lifecycle"
    assert entry.status == "failed"
    assert entry.message == "boom"
    assert entry.error_type == "RuntimeError"
    assert entry.metrics_snapshot == {"records_fetched": 10}
    assert entry.details == {
        "_diagnostic": {
            "contract_version": "v1",
            "event_type": "run_failed",
            "event_family": "pipeline.lifecycle",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "failed",
            "error_type": "RuntimeError",
        }
    }
    assert store.list_entries_by_run_id(run_id) == [entry]


def test_record_stage_completed_captures_stage_and_metrics() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-3",
    )

    entry = service.record_stage_completed(
        stage="postrun",
        metrics_snapshot={"records_silver": 42},
        details={"result": "ok"},
    )

    assert entry.event_type == "stage_completed"
    assert entry.event_family == "pipeline.phase"
    assert entry.status == "completed"
    assert entry.stage == "postrun"
    assert entry.metrics_snapshot == {"records_silver": 42}
    assert entry.details == {
        "result": "ok",
        "_diagnostic": {
            "contract_version": "v1",
            "event_type": "stage_completed",
            "event_family": "pipeline.phase",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "completed",
            "stage": "postrun",
        },
    }


def test_record_artifact_published_captures_layer_and_path() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-4",
    )

    entry = service.record_artifact_published(
        layer="silver",
        artifact_path="/tmp/output/silver/chembl/activity",
        dataset_ref="silver:chembl.activity@7",
        lineage_fragment_id="silver:fragment-1",
        details={"metadata_path": "/tmp/output/silver/chembl/activity/_metadata.yaml"},
    )

    assert entry.event_type == "artifact_published"
    assert entry.event_family == "artifact"
    assert entry.status == "published"
    assert entry.stage == "silver"
    assert entry.dataset_ref == "silver:chembl.activity@7"
    assert entry.lineage_fragment_id == "silver:fragment-1"
    assert entry.details == {
        "artifact_path": "/tmp/output/silver/chembl/activity",
        "metadata_path": "/tmp/output/silver/chembl/activity/_metadata.yaml",
        "_diagnostic": {
            "contract_version": "v1",
            "event_type": "artifact_published",
            "event_family": "artifact",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "published",
            "stage": "silver",
            "dataset_ref": "silver:chembl.activity@7",
            "lineage_fragment_id": "silver:fragment-1",
        },
    }
