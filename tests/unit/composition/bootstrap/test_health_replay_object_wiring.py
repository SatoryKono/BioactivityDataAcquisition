"""The production health bootstrap must verify saved replay bytes."""

from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.composition.bootstrap.assembly import health_server
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("explicit_root", [True, False])
@pytest.mark.parametrize("damage", ["none", "missing", "changed"])
@pytest.mark.parametrize("kind", ["config", "lock", "bronze"])
def test_bootstrap_verifies_original_objects(
    tmp_path, monkeypatch, explicit_root, damage, kind
):
    """Missing wiring, wrong roots and stale positive flags cannot pass."""
    data_root = tmp_path / "data"
    monkeypatch.setattr(
        health_server,
        "get_settings",
        lambda: SimpleNamespace(
            data_dir=str(data_root), archive_root=None, report_root=tmp_path / "reports"
        ),
    )
    deps = health_server.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: MagicMock(),
        data_root=data_root if explicit_root else None,
    )
    control = data_root / "output" / "control"
    run_id = UUID("11111111-1111-4111-8111-111111111111")
    config = {"identity_version": "effective-config-v1", "config_data": {"limit": 1000}}
    FileEffectiveConfigArtifactStore(control / "effective_config").save(
        artifact_id="saved-config",
        run_id=run_id,
        payload={
            "artifact_id": "saved-config",
            "semantic_artifact": {"effective_execution_config": config},
        },
    )
    lock_bytes = b"original dependency lock\r\n"
    lock_hash = sha256(lock_bytes).hexdigest()
    paths = {
        "config": control / "effective_config" / "saved-config.json",
        "lock": control / "dependency_locks" / lock_hash,
        "bronze": data_root
        / "output"
        / "bronze"
        / "chembl"
        / "activity"
        / "batch.jsonl",
    }
    for kind_name, content in (("lock", lock_bytes), ("bronze", b"original input")):
        paths[kind_name].parent.mkdir(parents=True, exist_ok=True)
        paths[kind_name].write_bytes(content)
    keys = {
        "config": "effective_config_hash",
        "lock": "dependency_lock_hash",
        "bronze": "input_snapshot_fingerprint",
    }
    manifest = SimpleNamespace(
        run_id=run_id,
        code_provenance=SimpleNamespace(
            effective_config_hash=stable_json_hash(config),
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
                        content_hash=sha256(b"original input").hexdigest(),
                    ),
                ),
            ),
        ),
    )
    port = deps.run_manifest_port
    assert port.verify_replay_objects(manifest) == dict.fromkeys(keys.values(), True)
    if damage == "missing":
        paths[kind].unlink()
    elif damage == "changed":
        if kind == "config":
            paths[kind].write_text(paths[kind].read_text().replace("1000", "1001"))
        else:
            paths[kind].write_bytes(b"tampered bytes")
    before = {name: path.read_bytes() for name, path in paths.items() if path.exists()}
    expected = dict.fromkeys(keys.values(), True)
    if damage == "missing":
        del expected[keys[kind]]
    elif damage == "changed":
        expected[keys[kind]] = False
    assert port.verify_replay_objects(manifest) == expected
    assert {
        name: path.read_bytes() for name, path in paths.items() if path.exists()
    } == before


def test_isolated_root_verifier_ready_while_default_root_misses(tmp_path, monkeypatch):
    """RF-001 control: ReplayObjectVerifier passes only on the owning data root."""
    default_data = tmp_path / "data"
    isolated = default_data / "workflow-limit100-20261102T144403Z" / "chembl_assay"
    monkeypatch.setattr(
        health_server,
        "get_settings",
        lambda: SimpleNamespace(
            data_dir=str(default_data),
            archive_root=None,
            report_root=tmp_path / "reports",
        ),
    )
    isolated_deps = health_server.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: MagicMock(),
        data_root=isolated,
    )
    default_deps = health_server.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: MagicMock(),
        data_root=default_data,
    )
    run_id = UUID("ac0b4e22-6a6e-5b7e-818e-106aeaf41390")
    control = isolated / "output" / "control"
    config = {"identity_version": "effective-config-v1", "config_data": {"limit": 100}}
    FileEffectiveConfigArtifactStore(control / "effective_config").save(
        artifact_id="saved-config",
        run_id=run_id,
        payload={
            "artifact_id": "saved-config",
            "semantic_artifact": {"effective_execution_config": config},
        },
    )
    lock_bytes = b"isolated lock bytes\n"
    lock_hash = sha256(lock_bytes).hexdigest()
    bronze_bytes = b'{"assay_id":"CHEMBL1"}\n'
    (control / "dependency_locks" / lock_hash).parent.mkdir(parents=True, exist_ok=True)
    (control / "dependency_locks" / lock_hash).write_bytes(lock_bytes)
    bronze = isolated / "output" / "bronze" / "chembl" / "assay" / "batch.jsonl"
    bronze.parent.mkdir(parents=True, exist_ok=True)
    bronze.write_bytes(bronze_bytes)
    manifest = SimpleNamespace(
        run_id=run_id,
        code_provenance=SimpleNamespace(
            effective_config_hash=stable_json_hash(config),
            effective_config_artifact_id="saved-config",
            dependency_lock_hash="sha256:" + lock_hash,
        ),
        source_refs=(
            SimpleNamespace(
                provider="chembl",
                entity="assay",
                input_snapshots=(
                    SimpleNamespace(
                        immutable_uri="bronze://chembl/assay/batch.jsonl",
                        content_hash=sha256(bronze_bytes).hexdigest(),
                    ),
                ),
            ),
        ),
    )
    before = {
        "config": (control / "effective_config" / "saved-config.json").read_bytes(),
        "lock": (control / "dependency_locks" / lock_hash).read_bytes(),
        "bronze": bronze.read_bytes(),
    }
    assert isolated_deps.run_manifest_port.verify_replay_objects(manifest) == {
        "effective_config_hash": True,
        "dependency_lock_hash": True,
        "input_snapshot_fingerprint": True,
    }
    assert default_deps.run_manifest_port.verify_replay_objects(manifest) == {}
    assert (control / "effective_config" / "saved-config.json").read_bytes() == before[
        "config"
    ]
    assert (control / "dependency_locks" / lock_hash).read_bytes() == before["lock"]
    assert bronze.read_bytes() == before["bronze"]
