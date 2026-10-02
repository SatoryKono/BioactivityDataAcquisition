"""Replay evidence must be checked from original bytes on every read."""

from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.domain.normalization.json import stable_json_hash
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)


pytestmark = pytest.mark.unit


def evidence(tmp_path):
    verifier = ReplayObjectVerifier(
        tmp_path / "config", tmp_path / "locks", tmp_path / "bronze"
    )
    run_id = UUID("11111111-1111-4111-8111-111111111111")
    config = {"identity_version": "effective-config-v1", "config_data": {"limit": 100}}
    config_hash = stable_json_hash(config)
    FileEffectiveConfigArtifactStore(verifier.config_root).save(
        artifact_id="saved-config",
        run_id=run_id,
        payload={
            "artifact_id": "saved-config",
            "semantic_artifact": {"effective_execution_config": config},
        },
    )
    batch = verifier.bronze_root / "chembl" / "activity" / "batch.jsonl"
    batch.parent.mkdir(parents=True)
    batch.write_bytes(b"original input")
    lock = tmp_path / "uv.lock"
    lock.write_bytes(b"original lock\r\n")
    lock_hash = sha256(lock.read_bytes()).hexdigest()
    verifier.archive_lock("sha256:" + lock_hash, tmp_path)
    manifest = SimpleNamespace(
        run_id=run_id,
        code_provenance=SimpleNamespace(
            effective_config_hash=config_hash,
            effective_config_artifact_id="saved-config",
            dependency_lock_hash="sha256:" + lock_hash,
        ),
        source_refs=(
            SimpleNamespace(
                provider="chembl",
                entity="activity",
                input_snapshots=(
                    SimpleNamespace(
                        immutable_uri="bronze://batch.jsonl",
                        content_hash=sha256(batch.read_bytes()).hexdigest(),
                    ),
                ),
            ),
        ),
        objects={
            "effective_config_hash": True,
            "dependency_lock_hash": True,
            "input_snapshot_fingerprint": True,
        },
    )
    return verifier, manifest, batch, lock


def test_original_objects_pass_and_current_lock_is_irrelevant(tmp_path):
    verifier, manifest, batch, lock = evidence(tmp_path)
    lock.write_bytes(b"new environment")
    assert verifier.verify(manifest) == dict.fromkeys(manifest.objects, True)


@pytest.mark.parametrize("kind", ["batch", "lock", "config"])
def test_modified_bytes_fail_even_with_saved_true_flags(tmp_path, kind):
    verifier, manifest, batch, lock = evidence(tmp_path)
    paths = {
        "batch": batch,
        "lock": verifier.lock_root
        / manifest.code_provenance.dependency_lock_hash.removeprefix("sha256:"),
        "config": verifier.config_root / "saved-config.json",
    }
    path = paths[kind]
    if kind == "config":
        path.write_text(path.read_text().replace("100", "101"))
    else:
        path.write_bytes(b"tampered")
    key = {
        "batch": "input_snapshot_fingerprint",
        "lock": "dependency_lock_hash",
        "config": "effective_config_hash",
    }[kind]
    assert verifier.verify(manifest)[key] is False


def test_missing_lock_is_unknown_and_never_recreated_by_read(tmp_path):
    verifier, manifest, batch, lock = evidence(tmp_path)
    archived = (
        verifier.lock_root
        / manifest.code_provenance.dependency_lock_hash.removeprefix("sha256:")
    )
    archived.unlink()
    assert "dependency_lock_hash" not in verifier.verify(manifest)
    assert not archived.exists()


def test_changed_current_lock_cannot_be_archived_as_original(tmp_path):
    verifier, manifest, batch, lock = evidence(tmp_path)
    archived = (
        verifier.lock_root
        / manifest.code_provenance.dependency_lock_hash.removeprefix("sha256:")
    )
    archived.unlink()
    lock.write_bytes(b"different lock")
    verifier.archive_lock(manifest.code_provenance.dependency_lock_hash, tmp_path)
    assert not archived.exists()


def test_missing_snapshot_cannot_pass_from_recorded_flag(tmp_path):
    verifier, manifest, batch, lock = evidence(tmp_path)
    batch.unlink()
    assert "input_snapshot_fingerprint" not in verifier.verify(manifest)


def test_all_snapshots_must_be_verified(tmp_path):
    verifier, manifest, batch, lock = evidence(tmp_path)
    manifest.source_refs[0].input_snapshots += (
        SimpleNamespace(
            immutable_uri="https://example.invalid/object", content_hash="a" * 64
        ),
    )
    assert "input_snapshot_fingerprint" not in verifier.verify(manifest)


def test_bronze_path_cannot_escape_root(tmp_path):
    verifier, manifest, batch, lock = evidence(tmp_path)
    assert verifier._snapshot_path("bronze://../uv.lock") is None


def test_corrupt_config_is_not_verified(tmp_path):
    verifier, manifest, batch, lock = evidence(tmp_path)
    (verifier.config_root / "saved-config.json").write_text("{")
    assert "effective_config_hash" not in verifier.verify(manifest)
