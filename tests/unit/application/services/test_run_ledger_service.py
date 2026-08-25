# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for RunLedgerService."""

from __future__ import annotations

from datetime import UTC, datetime
from json import dumps
from pathlib import Path

import pytest

from bioetl.application.services.control_plane import RunLedgerService
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunLedgerStore
from bioetl.domain.types.dq_contracts import DQDisposition
from tests.helpers.clock import FixedClock
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.helpers.synthetic_paths import synthetic_test_root

pytestmark = pytest.mark.unit

TEST_ROOT = synthetic_test_root("run-ledger-service")
SILVER_ARTIFACT_PATH = str(TEST_ROOT / "output" / "silver" / "chembl" / "activity")
SILVER_METADATA_PATH = str(Path(SILVER_ARTIFACT_PATH) / "_metadata.yaml")
SILVER_ARTIFACT_CONTENT_HASH = "a" * 64
GOLD_DQ_REPORT_PATH = str(
    TEST_ROOT / "output" / "gold" / "chembl" / "activity" / "_dq.json"
)


_InMemoryRunLedgerStore = InMemoryRunLedgerStore


def _run_id(label: str) -> RunID:
    return RunID(deterministic_uuid(f"run-ledger:{label}"))


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
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("manifest-created")
    store = _InMemoryRunLedgerStore()
    occurred_at = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-1",
        _occurred_at_factory=FixedClock(occurred_at).now,
    )

    entry = service.record_manifest_created(_make_manifest(run_id))

    assert entry.entry_id == "entry-1"
    assert entry.event_type == "manifest_created"
    assert entry.event_family == "diagnostic"
    assert entry.status == "created"
    assert entry.occurred_at == occurred_at
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
            "status": "created",
        },
    }
    assert store.list_entries("manifest-1") == [entry]


def test_record_input_snapshot_published_appends_bounded_snapshot_event() -> None:
    run_id = _run_id("input-snapshot-published")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-input-snapshot",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    entry = service.record_input_snapshot_published(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        snapshot_id="snapshot-1",
        content_hash="sha256:snapshot-1",
        immutable_uri="file:///bronze/snapshot-1.jsonl",
        bronze_batch_ref="data/bronze/chembl/activity/batch-1",
        query_fingerprint="query-fingerprint-1",
    )

    assert entry.entry_id == "entry-input-snapshot"
    assert entry.event_type == "input_snapshot_published"
    assert entry.event_family == "input_snapshot"
    assert entry.status == "published"
    assert entry.stage == "bronze"
    assert entry.details["snapshot_id"] == "snapshot-1"
    assert entry.details["content_hash"] == "sha256:snapshot-1"
    assert entry.details["immutable_uri"] == "file:///bronze/snapshot-1.jsonl"


def test_record_input_snapshot_published_rejects_missing_required_identity() -> None:
    run_id = _run_id("input-snapshot-missing-required-identity")
    service = RunLedgerService(
        ledger_port=_InMemoryRunLedgerStore(),
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-input-snapshot-invalid",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="content_hash is required"):
        service.record_input_snapshot_published(
            provider="chembl",
            entity="activity",
            pipeline_name="chembl_activity",
            snapshot_id="snapshot-1",
            content_hash=" ",
            immutable_uri="file:///bronze/snapshot-1.jsonl",
            bronze_batch_ref="data/bronze/chembl/activity/batch-1",
        )


def test_record_manifest_created_rejects_mismatched_manifest_identity() -> None:
    run_id = _run_id("manifest-created-mismatch")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="pending",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-manifest-mismatch",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(
        ValueError,
        match="manifest_id must match the persisted manifest",
    ):
        service.record_manifest_created(_make_manifest(run_id))


def test_record_run_started_uses_canonical_identity_anchor_names() -> None:
    run_id = _run_id("run-started-canonical-anchors")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-canonical-anchors",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("run-started-missing-manifest-link")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="pending",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-missing-manifest-link",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(
        RuntimeError,
        match="persisted manifest_id",
    ):
        service.record_run_started()


def test_record_stage_started_captures_stage_and_details() -> None:
    run_id = _run_id("stage-started-captures-details")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-stage-started",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("run-failed-captures-metrics")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-2",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("run-exception-canonical-payload")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-run-exception",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("run-finished-success-metrics")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-run-finished",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    entry = service.record_run_finished(
        metrics_snapshot={"records_gold": 9},
        details={
            "adaptive_memory": {
                "decision_count": 1,
                "batch_size_reductions": 1,
            }
        },
    )

    assert entry.event_type == "run_finished"
    assert entry.event_family == "pipeline.lifecycle"
    assert entry.status == "success"
    assert entry.metrics_snapshot == {"records_gold": 9}
    assert entry.details == {
        "adaptive_memory": {
            "decision_count": 1,
            "batch_size_reductions": 1,
        },
        "_diagnostic": {
            "diagnostic_contract_version": "v1",
            "event_type": "run_finished",
            "event_family": "pipeline.lifecycle",
            "manifest_id": "manifest-1",
            "run_id": str(run_id),
            "status": "success",
        },
    }


def test_record_run_finished_retry_reuses_logical_idempotency_key() -> None:
    run_id = _run_id("run-finished-idempotency-retry")
    store = _InMemoryRunLedgerStore()
    entry_ids = iter(["entry-run-finished-1", "entry-run-finished-2"])
    occurred_at_values = iter(
        [
            datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            datetime(2026, 4, 24, 12, 1, tzinfo=UTC),
        ]
    )
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: next(entry_ids),
        _occurred_at_factory=lambda: next(occurred_at_values),
    )

    first = service.record_run_finished(metrics_snapshot={"records_gold": 9})
    retry = service.record_run_finished(metrics_snapshot={"records_gold": 9})

    assert first.entry_id == "entry-run-finished-1"
    assert retry.entry_id == "entry-run-finished-2"
    assert first.occurred_at != retry.occurred_at
    assert first.idempotency_key is not None
    assert first.idempotency_key == retry.idempotency_key
    assert store.list_entries("manifest-1") == [first]


def test_record_run_finished_distinguishes_different_logical_payloads() -> None:
    run_id = _run_id("run-finished-distinguishes-payloads")
    store = _InMemoryRunLedgerStore()
    entry_ids = iter(["entry-run-finished-1", "entry-run-finished-2"])
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: next(entry_ids),
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    first = service.record_run_finished(metrics_snapshot={"records_gold": 9})
    second = service.record_run_finished(metrics_snapshot={"records_gold": 10})

    assert first.idempotency_key != second.idempotency_key
    assert store.list_entries("manifest-1") == [first, second]


def test_record_run_shutdown_captures_shutdown_metrics() -> None:
    run_id = _run_id("run-shutdown-metrics")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-run-shutdown",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("stage-completed-metrics")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-3",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("artifact-published-layer-path")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-4",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    entry = service.record_artifact_published(
        layer="silver",
        artifact_path=SILVER_ARTIFACT_PATH,
        artifact_content_hash=SILVER_ARTIFACT_CONTENT_HASH,
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
        "artifact_content_hash": SILVER_ARTIFACT_CONTENT_HASH,
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
    run_id = _run_id("artifact-published-unlinked")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-unlinked",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(
        ValueError,
        match="Artifact publication requires dataset_ref or lineage_fragment_id",
    ):
        service.record_artifact_published(
            layer="silver",
            artifact_path=SILVER_ARTIFACT_PATH,
            artifact_content_hash=SILVER_ARTIFACT_CONTENT_HASH,
        )


def test_record_artifact_published_rejects_missing_content_hash() -> None:
    run_id = _run_id("artifact-published-missing-hash")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-missing-hash",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="artifact_content_hash is required"):
        service.record_artifact_published(
            layer="silver",
            artifact_path=SILVER_ARTIFACT_PATH,
            artifact_content_hash=" ",
            dataset_ref="silver:chembl.activity@7",
        )


def test_record_dq_policy_applied_captures_trace_anchors() -> None:
    run_id = _run_id("dq-policy-applied-anchors")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-5",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
    run_id = _run_id("stage-started-canonical-detail-order")
    store = _InMemoryRunLedgerStore()
    service = RunLedgerService(
        ledger_port=store,
        manifest_id="manifest-1",
        run_id=run_id,
        _entry_id_factory=lambda: "entry-canonical-details",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
