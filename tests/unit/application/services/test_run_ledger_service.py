"""Unit tests for RunLedgerService."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from json import dumps
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID, RunType
from bioetl.domain.types.dq_contracts import DQDisposition

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-run-ledger-service-"))
SILVER_ARTIFACT_PATH = str(TEST_ROOT / "output" / "silver" / "chembl" / "activity")
SILVER_METADATA_PATH = str(Path(SILVER_ARTIFACT_PATH) / "_metadata.yaml")
GOLD_DQ_REPORT_PATH = str(
    TEST_ROOT / "output" / "gold" / "chembl" / "activity" / "_dq.json"
)


class _InMemoryRunLedgerStore(RunLedgerPort):
    def __init__(self) -> None:
        self._items: list[RunLedgerEntry] = []

    def append(self, entry: RunLedgerEntry) -> None:
        self._items.append(entry)

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.manifest_id == manifest_id]

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.run_id == run_id]

    def list_entries_after(
        self,
        manifest_id: str,
        after_entry_id: str | None,
    ) -> list[RunLedgerEntry]:
        entries = self.list_entries(manifest_id)
        if after_entry_id is None:
            return entries
        for index, item in enumerate(entries):
            if item.entry_id == after_entry_id:
                return entries[index + 1 :]
        raise ValueError(f"missing watermark {after_entry_id!r}")


def _make_manifest(
    run_id: RunID,
    *,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> RunManifest:
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
            contract_ref=contract_ref,
            contract_version=contract_version,
            effective_config_artifact_id=effective_config_artifact_id,
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
            "diagnostic_contract_version": "v1",
            "event_type": "manifest_created",
            "event_family": "diagnostic",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "pipeline": "chembl_activity",
            "provider": "chembl",
            "entity": "activity",
            "run_type": "incremental",
            "effective_config_hash": "deadbeef",
            "status": "created",
        },
    }
    assert store.list_entries("manifest-1") == [entry]


def test_record_manifest_created_rejects_mismatched_manifest_identity() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="pending",
        run_id=run_id,
    )

    with pytest.raises(
        ValueError,
        match="manifest_id must match the persisted manifest",
    ):
        service.record_manifest_created(_make_manifest(run_id))


def test_record_run_started_uses_canonical_identity_anchor_names() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-canonical-anchors",
    )

    service.record_manifest_created(
        _make_manifest(
            run_id,
            contract_ref="chembl.activity",
            contract_version="1.2.0",
            effective_config_artifact_id="eca-123",
        )
    )
    entry = service.record_run_started()

    diagnostic = (entry.details or {})["_diagnostic"]
    assert diagnostic["diagnostic_contract_version"] == "v1"
    assert diagnostic["contract_ref"] == "chembl.activity"
    assert diagnostic["contract_version"] == "1.2.0"
    assert diagnostic["effective_config_artifact_id"] == "eca-123"
    assert "data_contract_version" not in diagnostic


def test_record_run_started_rejects_missing_persisted_manifest_link() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="pending",
        run_id=run_id,
    )

    with pytest.raises(
        RuntimeError,
        match="persisted manifest_id",
    ):
        service.record_run_started()


def test_record_stage_started_captures_stage_and_details() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-stage-started",
    )

    entry = service.record_stage_started(
        stage="Seed",
        details={"count": 1},
    )

    assert entry.event_type == "stage_started"
    assert entry.event_family == "pipeline.phase"
    assert entry.status == "running"
    assert entry.stage == "seed"
    assert entry.details == {
        "count": 1,
        "_diagnostic": {
            "diagnostic_contract_version": "v1",
            "event_type": "stage_started",
            "event_family": "pipeline.phase",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "running",
            "stage": "seed",
        },
    }


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
            "diagnostic_contract_version": "v1",
            "event_type": "run_failed",
            "event_family": "pipeline.lifecycle",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "failed",
            "error_type": "RuntimeError",
        }
    }
    assert store.list_entries_by_run_id(run_id) == [entry]


def test_record_run_exception_uses_canonical_failure_payload() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-run-exception",
    )

    entry = service.record_run_exception(
        error=RuntimeError("boom"),
        metrics_snapshot={"records_fetched": 10},
    )

    assert entry.event_type == "run_failed"
    assert entry.status == "failed"
    assert entry.message == "boom"
    assert entry.error_type == "RuntimeError"
    assert entry.metrics_snapshot == {"records_fetched": 10}


def test_record_run_finished_captures_success_metrics() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-run-finished",
    )

    entry = service.record_run_finished(
        metrics_snapshot={"records_gold": 9},
    )

    assert entry.event_type == "run_finished"
    assert entry.event_family == "pipeline.lifecycle"
    assert entry.status == "success"
    assert entry.metrics_snapshot == {"records_gold": 9}
    assert entry.details == {
        "_diagnostic": {
            "diagnostic_contract_version": "v1",
            "event_type": "run_finished",
            "event_family": "pipeline.lifecycle",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "success",
        }
    }


def test_record_run_shutdown_captures_shutdown_metrics() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-run-shutdown",
    )

    entry = service.record_run_shutdown(
        metrics_snapshot={"records_silver": 3},
    )

    assert entry.event_type == "run_shutdown"
    assert entry.event_family == "pipeline.lifecycle"
    assert entry.status == "shutdown"
    assert entry.metrics_snapshot == {"records_silver": 3}
    assert entry.details == {
        "_diagnostic": {
            "diagnostic_contract_version": "v1",
            "event_type": "run_shutdown",
            "event_family": "pipeline.lifecycle",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "shutdown",
        }
    }


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
        stage="Postrun",
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
            "diagnostic_contract_version": "v1",
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
        artifact_path=SILVER_ARTIFACT_PATH,
        dataset_ref="silver:chembl.activity@7",
        lineage_fragment_id="silver:fragment-1",
        details={"metadata_path": SILVER_METADATA_PATH},
    )

    assert entry.event_type == "artifact_published"
    assert entry.event_family == "artifact"
    assert entry.status == "published"
    assert entry.stage == "silver"
    assert entry.dataset_ref == "silver:chembl.activity@7"
    assert entry.lineage_fragment_id == "silver:fragment-1"
    assert entry.details == {
        "artifact_path": SILVER_ARTIFACT_PATH,
        "metadata_path": SILVER_METADATA_PATH,
        "_diagnostic": {
            "diagnostic_contract_version": "v1",
            "event_type": "artifact_published",
            "event_family": "artifact",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "published",
            "stage": "silver",
            "artifact_id": "silver:chembl.activity@7",
            "dataset_ref": "silver:chembl.activity@7",
            "lineage_fragment_id": "silver:fragment-1",
        },
    }


def test_record_artifact_published_rejects_unlinked_artifact() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-unlinked",
    )

    with pytest.raises(
        ValueError,
        match="Artifact publication requires dataset_ref or lineage_fragment_id",
    ):
        service.record_artifact_published(
            layer="silver",
            artifact_path=SILVER_ARTIFACT_PATH,
        )


def test_record_dq_policy_applied_captures_trace_anchors() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-5",
    )

    entry = service.record_dq_policy_applied(
        stage="gold",
        rule_id="gold.not_null.id",
        disposition=DQDisposition.FAIL,
        dq_report_path=GOLD_DQ_REPORT_PATH,
    )

    assert entry.event_type == "dq_policy_applied"
    assert entry.event_family == "dq"
    assert entry.status == "failed"
    assert entry.stage == "gold"
    assert entry.details == {
        "rule_id": "gold.not_null.id",
        "disposition": "fail",
        "dq_report_path": GOLD_DQ_REPORT_PATH,
        "_diagnostic": {
            "diagnostic_contract_version": "v1",
            "event_type": "dq_policy_applied",
            "event_family": "dq",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "failed",
            "stage": "gold",
        },
    }
    assert store.list_entries("manifest-1") == [entry]


def test_record_stage_started_canonicalizes_nested_detail_order() -> None:
    run_id = RunID(uuid4())
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-canonical-details",
    )

    entry = service.record_stage_started(
        stage="Seed",
        details={"beta": {"z": 1, "a": 2}, "alpha": "value"},
    )

    assert list((entry.details or {}).keys()) == ["_diagnostic", "alpha", "beta"]
    assert dumps(entry.to_dict()["details"], separators=(",", ":")) == (
        '{"_diagnostic":{"diagnostic_contract_version":"v1","event_family":"pipeline.phase",'
        f'"event_type":"stage_started","manifest_id":"manifest-1","run_id":"{run_id}",'
        '"stage":"seed","status":"running"},"alpha":"value","beta":{"a":2,"z":1}}'
    )
