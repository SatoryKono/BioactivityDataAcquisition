"""Persisted evidence must retain identity and rollback failed publication."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.infrastructure.checkpoint import metrics_rehydrate as checkpoints
from bioetl.infrastructure.control_plane import _file_run_ledger_queries as ledger
from bioetl.infrastructure.control_plane import (
    _file_run_manifest_persistence as manifests,
)
from bioetl.infrastructure.control_plane import file_run_ledger_store as ledger_store
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    FileProviderHealthEvidenceStore,
    ProviderHealthEvidenceRecord,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "entry",
    [
        SimpleNamespace(manifest_id="foreign", run_id="run"),
        SimpleNamespace(manifest_id="allowed", run_id="foreign"),
    ],
)
def test_successor_chain_rejects_foreign_manifest_or_run(entry):
    with pytest.raises(ledger.RunLedgerCorruptionError):
        ledger._ensure_entries_match_run_chain(
            entries=[entry], manifest_ids={"allowed"}, run_id="run"
        )


@pytest.mark.parametrize("previous", [None, "predecessor"])
def test_failed_publication_rolls_back_only_new_files(tmp_path, previous):
    pointer, index, predecessor = (
        tmp_path / name for name in ("pointer", "index", "ledger")
    )
    for path in (pointer, index, predecessor):
        path.write_text("new", encoding="utf-8")
    ledger._rollback_successor_ledger_publish(
        pointer_path=pointer,
        pointer_created=True,
        run_index_path=index,
        previous_index=previous,
        predecessor_ledger=predecessor,
        created_predecessor_ledger=True,
    )
    assert not pointer.exists() and not predecessor.exists()
    if previous is None:
        assert not index.exists()
    else:
        assert index.read_text(encoding="utf-8") == previous


@pytest.mark.parametrize(
    "predecessor, successor", [("", "new"), ("old", " "), ("same", "same")]
)
def test_successor_rebind_requires_distinct_nonempty_ids(
    tmp_path, predecessor, successor
):
    store = ledger_store.FileRunLedgerStore(tmp_path)
    with pytest.raises(ValueError, match="two distinct manifest ids"):
        store.record_manifest_successor(
            run_id="run",
            predecessor_manifest_id=predecessor,
            successor_manifest_id=successor,
        )
    assert list(tmp_path.iterdir()) == []


def test_conflicting_successor_pointer_cannot_be_overwritten(tmp_path):
    store = ledger_store.FileRunLedgerStore(tmp_path)
    pointer = tmp_path / "_predecessors" / "new.txt"
    pointer.parent.mkdir()
    pointer.write_text("other", encoding="utf-8")
    with pytest.raises(ledger.RunLedgerCorruptionError, match="different predecessor"):
        store.record_manifest_successor(
            run_id="run", predecessor_manifest_id="old", successor_manifest_id="new"
        )
    assert pointer.read_text(encoding="utf-8") == "other"


def test_run_index_cannot_move_between_unrelated_manifest_chains(tmp_path):
    index = tmp_path / "_by_run_id" / "run.txt"
    index.parent.mkdir()
    index.write_text("foreign", encoding="utf-8")
    store = ledger_store.FileRunLedgerStore(tmp_path)
    with pytest.raises(ledger.RunLedgerCorruptionError, match="different manifest_id"):
        store.record_manifest_successor(
            run_id="run", predecessor_manifest_id="old", successor_manifest_id="new"
        )
    assert index.read_text(encoding="utf-8") == "foreign"


def test_multiple_successors_and_cycles_fail_closed(tmp_path):
    pointers = tmp_path / "_predecessors"
    pointers.mkdir()
    (pointers / "first.txt").write_text("old", encoding="utf-8")
    (pointers / "second.txt").write_text("old", encoding="utf-8")
    store = ledger_store.FileRunLedgerStore(tmp_path)
    with pytest.raises(ledger.RunLedgerCorruptionError, match="multiple successor"):
        store._direct_successor_id("old")
    (pointers / "second.txt").unlink()
    (pointers / "old.txt").write_text("first", encoding="utf-8")
    (tmp_path / "old.jsonl").touch()
    (tmp_path / "first.jsonl").touch()
    with pytest.raises(ledger.RunLedgerCorruptionError, match="cycle"):
        store._ledger_chain_entries("old")


@pytest.mark.parametrize("text", ["not-json", "[]", '{"manifest_id":"successor"}\n'])
def test_unbindable_or_already_bound_sidecar_bytes_are_preserved(text):
    assert manifests._rebind_contract_evidence_identity(text, "successor") == text


def test_missing_object_verifier_does_not_certify_saved_objects(tmp_path):
    assert FileRunManifestStore(tmp_path).verify_replay_objects(Mock()) == {}


def test_explicit_degraded_flush_does_not_call_os_fsync(monkeypatch):
    fsync = Mock()
    monkeypatch.setattr(
        ledger_store, "_should_fsync_control_plane_writes", lambda: False
    )
    monkeypatch.setattr(ledger_store.os, "fsync", fsync)
    ledger_store._flush_file_descriptor(123)
    fsync.assert_not_called()


@pytest.mark.parametrize("payload", [[], {"schema_version": "unsupported"}])
def test_unsupported_health_evidence_is_not_loaded(tmp_path, payload):
    import json

    store = FileProviderHealthEvidenceStore(tmp_path)
    store.path_for("chembl").write_text(json.dumps(payload), encoding="utf-8")
    assert store.load("chembl") is None


def test_invalid_health_timestamp_is_never_fresh():
    record = ProviderHealthEvidenceRecord("chembl", 0, "invalid", "/health")
    assert not record.is_fresh(now=datetime(2026, 10, 21, tzinfo=UTC))


@pytest.mark.parametrize("changes", [{"provider": " "}, {"observed_at": None}])
def test_incomplete_health_identity_is_rejected(tmp_path, changes):
    import json

    record = ProviderHealthEvidenceRecord(
        "chembl", 0, "2026-10-21T00:00:00+00:00", "/health"
    )
    store = FileProviderHealthEvidenceStore(tmp_path)
    payload = {**record.to_dict(), **changes}
    store.path_for("chembl").write_text(json.dumps(payload), encoding="utf-8")
    assert store.load("chembl") is None


def test_missing_checkpoint_has_no_rehydrated_timestamp(tmp_path):
    assert checkpoints._newest_verified_payload(tmp_path, "chembl_assay") is None


def test_unreadable_checkpoint_invalidates_the_metric(tmp_path, monkeypatch):
    (tmp_path / "chembl_assay.json").write_text("corrupt", encoding="utf-8")
    metrics = Mock()
    assert (
        checkpoints.rehydrate_checkpoint_metrics(
            metrics, tmp_path, now=datetime(2026, 10, 21, tzinfo=UTC)
        )
        == 0
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_checkpoint_saved_at_seconds", 0.0, {"pipeline": "chembl_assay"}
    )


def test_unvalidated_metadata_cannot_be_used_as_a_checkpoint_time(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        checkpoints, "_newest_verified_payload", lambda *args: {"metadata": []}
    )
    assert (
        checkpoints._restored_pipeline_value(
            tmp_path, "chembl_assay", now=datetime(2026, 10, 21, tzinfo=UTC)
        )
        == 0.0
    )
