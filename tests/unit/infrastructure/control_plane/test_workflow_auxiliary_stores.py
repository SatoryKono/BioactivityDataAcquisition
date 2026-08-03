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
"""Coverage boost tests for workflow control-plane file stores."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

import bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads as lifecycle_payloads_module
import bioetl.infrastructure.control_plane.file_workflow_ledger_store as workflow_ledger_module
import bioetl.infrastructure.control_plane.file_workflow_execution_state_store as execution_state_module
import bioetl.infrastructure.control_plane.file_workflow_manifest_store as manifest_store_module
from bioetl.domain.control_plane import (
    ControlPlaneArtifactSurface,
    WorkflowExecutionState,
    WorkflowManifest,
    WorkflowManifestStep,
    WorkflowStepState,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import (
    FileWorkflowExecutionStateStore,
    FileWorkflowManifestStore,
)


pytestmark = pytest.mark.unit


def _run_id(seed: str) -> RunID:
    return RunID(UUID(seed))


def _manifest(
    *,
    manifest_id: str,
    workflow_run_id: RunID,
    created_at: datetime | None = None,
) -> WorkflowManifest:
    return WorkflowManifest(
        manifest_id=manifest_id,
        workflow_run_id=workflow_run_id,
        execution_fingerprint=f"fp-{manifest_id}",
        schema_version="1.0",
        created_at=created_at or datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        workflow_name="chembl_core",
        workflow_version="2026.1",
        launch_context={"mode": "test"},
        defaults={"limit": 10},
        selected_step_ids=("ingest",),
        steps=(
            WorkflowManifestStep(
                step_id="ingest",
                kind="pipeline",
                run_options={},
                config={},
            ),
        ),
    )


def _state(
    *,
    workflow_run_id: RunID,
    manifest_id: str,
    workflow_name: str = "chembl_core",
) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_run_id=workflow_run_id,
        manifest_id=manifest_id,
        workflow_name=workflow_name,
        execution_fingerprint=f"fp-{manifest_id}",
        status="running",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
        completed_at=None,
        selected_step_ids=("ingest",),
        steps=(
            WorkflowStepState(step_id="ingest", step_kind="pipeline", status="running"),
        ),
        completed_transform_fingerprints={"ingest": "fp-ingest"},
        last_event_id="workflow-entry-1",
        repair_required=False,
    )


def test_workflow_manifest_store_round_trip_and_conflicting_run_id(
    tmp_path: Path,
) -> None:
    store = FileWorkflowManifestStore(base_path=tmp_path / "workflow_manifest")
    workflow_run_id = _run_id("00000000-0000-0000-0000-000000000101")
    manifest = _manifest(
        manifest_id="manifest-1",
        workflow_run_id=workflow_run_id,
    )

    store.save(manifest)

    assert store.get("manifest-1") == manifest
    assert store.get_by_run_id(workflow_run_id) == manifest

    with pytest.raises(Exception) as exc_info:
        store.save(
            _manifest(
                manifest_id="manifest-2",
                workflow_run_id=workflow_run_id,
            )
        )

    assert "Workflow manifest" in str(exc_info.value)
    assert "different manifest_id" in str(exc_info.value)


def test_workflow_manifest_store_list_all_orders_by_created_at(
    tmp_path: Path,
) -> None:
    store = FileWorkflowManifestStore(base_path=tmp_path / "workflow_manifest")
    older = _manifest(
        manifest_id="manifest-older",
        workflow_run_id=_run_id("00000000-0000-0000-0000-000000000111"),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    newer = _manifest(
        manifest_id="manifest-newer",
        workflow_run_id=_run_id("00000000-0000-0000-0000-000000000112"),
        created_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
    )

    store.save(newer)
    store.save(older)

    assert store.list_all() == (older, newer)


def test_workflow_manifest_store_rolls_back_manifest_file_when_run_index_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileWorkflowManifestStore(base_path=tmp_path / "workflow_manifest")
    manifest = _manifest(
        manifest_id="manifest-rollback",
        workflow_run_id=_run_id("00000000-0000-0000-0000-000000000102"),
    )
    writes: list[Path] = []
    original = manifest_store_module.atomic_write_text

    def _failing_atomic_write(path: Path, payload: str) -> None:
        writes.append(path)
        if path.name.endswith(".txt"):
            raise OSError("boom")
        original(path, payload)

    monkeypatch.setattr(
        manifest_store_module, "atomic_write_text", _failing_atomic_write
    )

    with pytest.raises(Exception) as exc_info:
        store.save(manifest)

    assert "Workflow manifest" in str(exc_info.value)
    assert writes[-1].name.endswith(".txt")
    assert not (store.base_path / "manifest-rollback.json").exists()


def test_workflow_manifest_store_get_by_run_id_detects_index_corruption(
    tmp_path: Path,
) -> None:
    store = FileWorkflowManifestStore(base_path=tmp_path / "workflow_manifest")
    run_id = _run_id("00000000-0000-0000-0000-000000000103")
    index_path = store.base_path / "_by_run_id" / f"{run_id}.txt"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("missing-manifest", encoding="utf-8")

    with pytest.raises(ValueError, match="index corruption"):
        store.get_by_run_id(run_id)


def test_workflow_execution_state_store_round_trip_with_manifest_and_latest_indexes(
    tmp_path: Path,
) -> None:
    store = FileWorkflowExecutionStateStore(base_path=tmp_path / "workflow_state")
    state = _state(
        workflow_run_id=_run_id("00000000-0000-0000-0000-000000000201"),
        manifest_id="manifest-state-1",
    )

    store.save(state)

    assert store.get_by_run_id(state.workflow_run_id) == state
    assert store.get_by_manifest_id("manifest-state-1") == state
    assert store.get_latest("chembl_core") == state


def test_workflow_execution_state_store_handles_blank_indexes_and_invalid_payloads(
    tmp_path: Path,
) -> None:
    store = FileWorkflowExecutionStateStore(base_path=tmp_path / "workflow_state")
    manifest_index = store.base_path / "_by_manifest_id" / "manifest-state-2.txt"
    latest_index = store.base_path / "_latest_by_workflow" / "chembl_core.txt"
    manifest_index.parent.mkdir(parents=True, exist_ok=True)
    latest_index.parent.mkdir(parents=True, exist_ok=True)
    manifest_index.write_text("   ", encoding="utf-8")
    latest_index.write_text("", encoding="utf-8")

    assert store.get_by_manifest_id("manifest-state-2") is None
    assert store.get_latest("chembl_core") is None

    broken_state_path = store.base_path / "00000000-0000-0000-0000-000000000202.json"
    broken_state_path.parent.mkdir(parents=True, exist_ok=True)
    broken_state_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        store.get_by_run_id(_run_id("00000000-0000-0000-0000-000000000202"))


def test_workflow_execution_state_store_emits_success_miss_and_failed_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileWorkflowExecutionStateStore(base_path=tmp_path / "workflow_state")
    emitted: list[tuple[str, str]] = []

    def _capture_metrics(
        _metrics: object,
        *,
        store: str,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        assert duration_seconds >= 0.0
        emitted.append((operation, status))

    monkeypatch.setattr(
        execution_state_module,
        "emit_control_plane_read_metrics",
        _capture_metrics,
    )

    saved_state = _state(
        workflow_run_id=_run_id("00000000-0000-0000-0000-000000000203"),
        manifest_id="manifest-state-3",
        workflow_name="workflow-a",
    )
    store.save(saved_state)

    assert store.get_by_run_id(saved_state.workflow_run_id) == saved_state
    assert store.get_by_manifest_id("missing-manifest") is None

    broken_state_path = store.base_path / "00000000-0000-0000-0000-000000000204.json"
    broken_state_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        store.get_by_run_id(_run_id("00000000-0000-0000-0000-000000000204"))

    assert ("get_by_run_id", "success") in emitted
    assert ("get_by_manifest_id", "miss") in emitted
    assert emitted[-1] == ("get_by_run_id", "failed")


def test_workflow_ledger_store_miss_conflict_and_invalid_payload_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = workflow_ledger_module.FileWorkflowLedgerStore(
        base_path=tmp_path / "workflow_ledger"
    )
    emitted: list[tuple[str, str]] = []

    def _capture_metrics(
        _metrics: object,
        *,
        store: str,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        assert store == "workflow_ledger"
        assert duration_seconds >= 0.0
        emitted.append((operation, status))

    monkeypatch.setattr(
        workflow_ledger_module,
        "emit_control_plane_read_metrics",
        _capture_metrics,
    )

    missing_run_id = _run_id("00000000-0000-0000-0000-000000000301")
    assert store.list_entries("missing-manifest") == []
    assert store.list_entries_by_run_id(missing_run_id) == []

    run_id = _run_id("00000000-0000-0000-0000-000000000302")
    entry = workflow_ledger_module.WorkflowLedgerEntry(
        entry_id="workflow-entry-2",
        manifest_id="manifest-ledger-1",
        workflow_run_id=run_id,
        event_type="workflow_started",
        occurred_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        status="running",
    )
    store.append(entry)
    with pytest.raises(Exception, match="different manifest_id"):
        store.append(
            workflow_ledger_module.WorkflowLedgerEntry(
                entry_id="workflow-entry-3",
                manifest_id="manifest-ledger-2",
                workflow_run_id=run_id,
                event_type="workflow_started",
                occurred_at=datetime(2026, 1, 2, 12, 5, tzinfo=UTC),
                status="running",
            )
        )

    broken_path = store.base_path / "broken.jsonl"
    broken_path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        store.list_entries("broken")

    assert ("list_entries", "miss") in emitted
    assert ("list_entries_by_run_id", "miss") in emitted
    assert emitted[-1] == ("list_entries", "failed")


def test_append_jsonl_payload_truncates_partial_write_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_path = tmp_path / "workflow" / "manifest.jsonl"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    writes = {"count": 0}

    def _partial_then_fail(file_descriptor: int, payload: bytes) -> int:
        writes["count"] += 1
        if writes["count"] == 1:
            return max(1, min(4, len(payload)))
        raise OSError("append failed")

    monkeypatch.setattr(
        workflow_ledger_module,
        "flush_control_plane_file_descriptor",
        lambda _fd: None,
    )
    monkeypatch.setattr(workflow_ledger_module.os, "write", _partial_then_fail)

    with pytest.raises(OSError, match="append failed"):
        workflow_ledger_module._append_jsonl_payload(target_path, b'{"entry":1}\n')

    assert target_path.exists()
    assert target_path.read_bytes() == b""


def test_artifact_lifecycle_payload_helpers_cover_identity_and_fallback_branches(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "artifact.jsonl"
    jsonl_path.write_text('\n{"manifest_id": "m-1"}\n', encoding="utf-8")

    assert (
        lifecycle_payloads_module._read_json_object_or_empty(tmp_path / "artifact.txt")
        == {}
    )
    assert lifecycle_payloads_module._read_json_object_or_empty(jsonl_path) == {
        "manifest_id": "m-1"
    }

    broken_json_path = tmp_path / "broken.json"
    broken_json_path.write_text("[]", encoding="utf-8")
    assert lifecycle_payloads_module._read_json_object_or_empty(broken_json_path) == {}

    payload = {
        "manifest_id": "manifest-1",
        "artifact_id": "effective-1",
        "stored_fragment_id": "fragment-stored",
        "fragment_id": "fragment-fallback",
        "metadata": {
            "run_id": "run-meta",
            "effective_config_artifact_id": "cfg-meta",
        },
        "code_provenance": {"effective_config_artifact_id": "cfg-123"},
        "source_refs": [
            {"input_snapshots": [{"snapshot_id": "snap-a"}, {"snapshot_id": None}]},
            {"input_snapshots": "skip"},
        ],
    }
    index_path = tmp_path / "_by_run_id" / "run-index.txt"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("index", encoding="utf-8")

    assert (
        lifecycle_payloads_module._artifact_id(
            surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
            path=tmp_path / "manifest.json",
            payload=payload,
        )
        == "manifest-1"
    )
    assert (
        lifecycle_payloads_module._artifact_id(
            surface=ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
            path=tmp_path / "effective.json",
            payload=payload,
        )
        == "effective-1"
    )
    assert (
        lifecycle_payloads_module._artifact_id(
            surface=ControlPlaneArtifactSurface.LINEAGE,
            path=tmp_path / "fragment.json",
            payload=payload,
        )
        == "fragment-stored"
    )
    assert (
        lifecycle_payloads_module._artifact_id(
            surface=ControlPlaneArtifactSurface.CHECKPOINT,
            path=tmp_path / "checkpoint.json",
            payload={"metadata": {"run_id": "run-meta"}},
        )
        == "run-meta"
    )
    assert lifecycle_payloads_module._effective_config_artifact_id(payload) == "cfg-123"
    assert lifecycle_payloads_module._input_snapshot_ids(payload) == ("snap-a",)
    assert lifecycle_payloads_module._payload_text(payload, "run_id") == "run-meta"
    assert (
        lifecycle_payloads_module._payload_value(
            payload,
            "effective_config_artifact_id",
        )
        == "cfg-meta"
    )
    assert lifecycle_payloads_module._indexed_stem(index_path) == "run-index"
    assert lifecycle_payloads_module._lineage_fragment_id_candidates(payload) == (
        "fragment-stored",
        "fragment-fallback",
    )
    assert lifecycle_payloads_module._manifest_or_run_is_protected(
        {"manifest_id": "manifest-1", "run_id": "run-1"},
        manifest_ids=frozenset({"manifest-1"}),
        run_ids=frozenset(),
    )
    assert lifecycle_payloads_module._optional_text("  value  ") == "value"
    assert lifecycle_payloads_module._optional_text("   ") is None
    assert (
        lifecycle_payloads_module._resolve_lifecycle_reason(
            stale=False,
            protected_by=("evidence_floor:manifest:manifest-1",),
        )
        == "reproducibility_evidence_floor"
    )
    assert (
        lifecycle_payloads_module._resolve_lifecycle_reason(
            stale=False,
            protected_by=("manifest:manifest-1",),
        )
        == "protected_reference"
    )
    assert (
        lifecycle_payloads_module._resolve_lifecycle_reason(
            stale=True,
            protected_by=(),
        )
        == "retention_expired"
    )


def test_artifact_lifecycle_payload_helpers_cover_time_and_hash_fallbacks(
    tmp_path: Path,
) -> None:
    timestamped = tmp_path / "created.json"
    timestamped.write_text("{}", encoding="utf-8")
    unreadable = tmp_path / "missing.bin"
    binary_path = tmp_path / "snapshot.bin"
    binary_path.write_bytes(b"snapshot")

    resolved = lifecycle_payloads_module._resolve_payload_or_file_time(
        timestamped,
        {"created_at": "2026-01-03T09:30:00"},
    )
    assert resolved is not None
    assert resolved.tzinfo is not None
    assert lifecycle_payloads_module._parse_datetime("not-a-date") is None
    assert lifecycle_payloads_module._content_addressed_file_snapshot_id(
        unreadable
    ).startswith("unreadable:")
    assert lifecycle_payloads_module._content_addressed_file_snapshot_id(
        binary_path
    ).startswith("sha256:")
