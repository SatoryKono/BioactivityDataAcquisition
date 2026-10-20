"""File-store successor contract for run manifests (#12014, variant A).

A persisted manifest is immutable: attaching snapshots persists a
successor under a new ``manifest_id`` whose ``predecessor_manifest_id``
points at the previous manifest. The run index (current) moves to the
successor, the predecessor stays readable by ID, and a failed save
rolls the whole transaction back.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit

from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.exceptions import StorageError
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import file_run_manifest_store
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)

_RUN_ID = RunID(UUID(int=12014))
_SNAPSHOT = RunInputSnapshotRef(
    snapshot_id="snap-1",
    content_hash="sha256:snap-1",
    immutable_uri="file:///bronze/chembl/activity/batch_1.jsonl.zst",
)


def _original() -> RunManifest:
    return RunManifest(
        manifest_id="m1",
        execution_fingerprint="fp-pre-merge",
        run_id=_RUN_ID,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
            ),
        ),
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )


def _successor(original: RunManifest) -> RunManifest:
    return replace(
        original,
        manifest_id="m2",
        predecessor_manifest_id="m1",
        execution_fingerprint="fp-post-merge",
        source_refs=(
            replace(
                original.source_refs[0],
                input_snapshots=(_SNAPSHOT,),
            ),
        ),
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    )


def test_successor_save_keeps_predecessor_by_id_and_moves_current(
    tmp_path: Path,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path)
    original = _original()
    store.save(original)
    original_bytes = (tmp_path / "m1.json").read_bytes()

    store.save(_successor(original))

    assert (tmp_path / "m1.json").read_bytes() == original_bytes
    by_id = store.get("m1")
    assert by_id == original
    successor = store.get("m2")
    assert successor is not None
    assert successor.predecessor_manifest_id == "m1"
    assert successor.execution_fingerprint == "fp-post-merge"
    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m2"
    assert (tmp_path / "_by_run_id" / f"{_RUN_ID}.txt").read_text() == "m2"
    latest = store.get_latest_for_scope("chembl_activity")
    assert latest is not None
    assert latest.manifest_id == "m2"
    assert {item.manifest_id for item in store.list_all()} == {"m1", "m2"}


def test_unlinked_manifest_id_for_same_run_is_rejected(
    tmp_path: Path,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path)
    original = _original()
    store.save(original)

    unlinked = replace(original, manifest_id="mX", execution_fingerprint="fp-x")
    with pytest.raises(StorageError, match="already mapped"):
        store.save(unlinked)

    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m1"
    assert store.get("mX") is None


def test_successor_with_wrong_predecessor_is_rejected(
    tmp_path: Path,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path)
    original = _original()
    store.save(original)

    impostor = replace(
        _successor(original),
        predecessor_manifest_id="someone-else",
    )
    with pytest.raises(StorageError, match="already mapped"):
        store.save(impostor)

    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m1"
    assert store.get("m2") is None


def test_failed_successor_save_rolls_back_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path)
    original = _original()
    store.save(original)
    original_bytes = (tmp_path / "m1.json").read_bytes()
    real_writer = file_run_manifest_store.atomic_write_text

    def _failing_writer(path: Path, text: str) -> None:
        if path.parent.name == "_by_run_id":
            raise OSError("injected index write failure")
        real_writer(path, text)

    monkeypatch.setattr(
        file_run_manifest_store,
        "atomic_write_text",
        _failing_writer,
    )
    with pytest.raises(StorageError, match="injected index write failure"):
        store.save(_successor(original))

    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m1"
    assert current == original
    assert store.get("m2") is None
    assert (tmp_path / "m1.json").read_bytes() == original_bytes
    latest = store.get_latest_for_scope("chembl_activity")
    assert latest is not None
    assert latest.manifest_id == "m1"
