# pyright: reportArgumentType=false
"""Composition factory for evidence read contexts (RF-003)."""

from __future__ import annotations

import errno
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.composition.factories.evidence_read_context_factory import (
    FileEvidenceReadContextFactory,
)
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationInvalidError,
)
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)

pytestmark = pytest.mark.unit

_RUN_A = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"


def _seed_replay_objects(data_root: Path, *, run_id: UUID) -> SimpleNamespace:
    output = data_root / "output" / "control"
    verifier = ReplayObjectVerifier(
        config_root=output / "effective_config",
        lock_root=output / "dependency_locks",
        bronze_root=data_root / "output" / "bronze",
    )
    config = {
        "identity_version": "effective-config-v1",
        "config_data": {"limit": 100},
    }
    config_hash = stable_json_hash(config)
    FileEffectiveConfigArtifactStore(verifier.config_root).save(
        artifact_id="saved-config",
        run_id=run_id,
        payload={
            "artifact_id": "saved-config",
            "semantic_artifact": {"effective_execution_config": config},
        },
    )
    batch = verifier.bronze_root / "chembl" / "assay" / "batch.jsonl"
    batch.parent.mkdir(parents=True)
    batch.write_bytes(b"original input")
    lock = data_root / "uv.lock"
    lock.write_bytes(b"original lock\n")
    lock_hash = sha256(lock.read_bytes()).hexdigest()
    verifier.archive_lock("sha256:" + lock_hash, data_root)
    return SimpleNamespace(
        run_id=run_id,
        code_provenance=SimpleNamespace(
            effective_config_hash=config_hash,
            effective_config_artifact_id="saved-config",
            dependency_lock_hash="sha256:" + lock_hash,
        ),
        source_refs=(
            SimpleNamespace(
                provider="chembl",
                entity="assay",
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
        batch=batch,
        lock_digest=lock_hash,
    )


def test_factory_opens_context_and_verifies_real_bytes(tmp_path: Path) -> None:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    evidence = _seed_replay_objects(data_root, run_id=UUID(_RUN_A))
    context = FileEvidenceReadContextFactory().open(
        data_root,
        trusted_alias_base=data_root,
    )
    checks = context.verify_replay_objects(evidence)
    assert checks == dict.fromkeys(evidence.objects, True)
    evidence.batch.write_bytes(b"tampered")
    assert context.verify_replay_objects(evidence)["input_snapshot_fingerprint"] is False


def test_context_rechecks_child_paths_before_manifest_read(tmp_path: Path) -> None:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    context = FileEvidenceReadContextFactory().open(
        data_root,
        trusted_alias_base=data_root,
    )
    outside = tmp_path / "outside-output"
    outside.mkdir()
    try:
        (data_root / "output").symlink_to(outside, target_is_directory=True)
    except NotImplementedError as exc:
        pytest.skip(f"symlinks are not implemented: {exc}")
    except OSError as exc:
        unsupported_errors = {errno.EPERM, errno.ENOSYS}
        if hasattr(errno, "EOPNOTSUPP"):
            unsupported_errors.add(errno.EOPNOTSUPP)
        if exc.errno in unsupported_errors or getattr(exc, "winerror", None) == 1314:
            pytest.skip(f"symlinks are unavailable: {exc}")
        raise

    with pytest.raises(EvidenceLocationInvalidError, match="escapes|symlink"):
        context.get_manifest_by_run_id(UUID(_RUN_A))
