"""Composite replay consumes verified child bytes and fails closed on drift."""

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import pytest

from bioetl.composition.bootstrap.runtime.composite_replay_capture import (
    bind_composite_replay_children,
)
from bioetl.composition.bootstrap.runtime.composite_replay_inputs import (
    load_composite_replay_inputs,
    load_runtime_composite_replay,
)
from bioetl.composition.snapshot_serialization import to_serializable_mapping
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def captured(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        data_dir=str(tmp_path), bronze_path=str(tmp_path / "bronze")
    )
    control = tmp_path / "output" / "control"
    store = FileRunManifestStore(base_path=control / "run_manifest")
    config = SimpleNamespace(
        name="composite_assay",
        seed=SimpleNamespace(pipeline="chembl_assay"),
        dependencies=(),
        enrichers=(),
    )
    lock = b"captured dependency lock"
    lock_hash = sha256(lock).hexdigest()
    (control / "dependency_locks").mkdir(parents=True)
    (control / "dependency_locks" / lock_hash).write_bytes(lock)
    batch = tmp_path / "bronze" / "chembl" / "assay" / "batch_saved.jsonl.zst"
    batch.parent.mkdir(parents=True)
    batch.write_bytes(b"captured bytes")
    source = RunSourceRef(
        "chembl",
        "assay",
        "chembl_assay",
        input_snapshots=(
            RunInputSnapshotRef(
                "saved",
                sha256(batch.read_bytes()).hexdigest(),
                "bronze://batch_saved.jsonl.zst",
            ),
        ),
    )

    def manifest(name, provider, sources, resolved):
        run_id = uuid5(NAMESPACE_URL, f"replay-fixture:{name}")
        identity = str(run_id)
        effective = {"identity_version": "effective-config-v1", "config_data": resolved}
        FileEffectiveConfigArtifactStore(control / "effective_config").save(
            artifact_id=identity,
            run_id=run_id,
            payload={
                "artifact_id": identity,
                "semantic_artifact": {"effective_execution_config": effective},
            },
        )
        value = RunManifest(
            manifest_id=identity,
            run_id=run_id,
            pipeline_name=name,
            provider=provider,
            launch_context={
                "execution_context": "composite"
                if provider == "composite"
                else "isolated"
            },
            entity="assay",
            resolved_config=resolved,
            code_provenance=RunCodeProvenance(
                git_commit="a" * 40,
                source_revision_state="clean",
                dependency_lock_hash=lock_hash,
                effective_config_hash=stable_json_hash(effective),
                effective_config_artifact_id=identity,
            ),
            source_refs=sources,
        )
        store.save(value)
        return value

    parent = manifest(config.name, "composite", (), to_serializable_mapping(config))
    child = manifest("chembl_assay", "chembl", (source,), {"pipeline": "chembl_assay"})
    result = SimpleNamespace(
        is_success=True,
        manifest_id=child.manifest_id,
        run_id=str(child.run_id),
        pipeline_name=child.pipeline_name,
    )
    bind_composite_replay_children(parent.manifest_id, [result], settings)
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_replay_inputs.get_code_revision_provenance",
        lambda: parent.code_provenance,
    )
    return SimpleNamespace(
        settings=settings,
        store=store,
        config=config,
        parent=store.get(parent.manifest_id),
        child=child,
        batch=batch,
        result=result,
        control=control,
    )


def test_replay_stages_only_bound_batches(captured):
    unrelated = captured.batch.with_name("batch_unrelated.jsonl.zst")
    unrelated.write_bytes(b"must not be replayed")
    plan = load_composite_replay_inputs(
        captured.config, captured.parent.manifest_id, captured.settings
    )
    options = plan.prepare_options("chembl_assay", {"limit": 1000})
    files = list(plan.output_root.rglob("*.jsonl.zst"))
    assert len(files) == 1
    assert files[0].read_bytes() == captured.batch.read_bytes()
    assert options["replay_of_manifest_id"] == captured.child.manifest_id
    assert options["limit"] == 1000
    assert options["exact_replay"] is True
    assert options["use_cached_bronze"] is True


@pytest.mark.parametrize("kind", ["batch", "lock", "config"])
def test_replay_rejects_modified_saved_objects(captured, kind):
    paths = {
        "batch": captured.batch,
        "lock": captured.control
        / "dependency_locks"
        / captured.parent.code_provenance.dependency_lock_hash,
        "config": captured.control
        / "effective_config"
        / f"{captured.parent.code_provenance.effective_config_artifact_id}.json",
    }
    paths[kind].write_bytes(b"tampered")
    with pytest.raises(ValueError, match="verification"):
        load_composite_replay_inputs(
            captured.config, captured.parent.manifest_id, captured.settings
        )


def test_replay_rechecks_bytes_before_copy(captured):
    plan = load_composite_replay_inputs(
        captured.config, captured.parent.manifest_id, captured.settings
    )
    captured.batch.write_bytes(b"tampered after planning")
    with pytest.raises(ValueError, match="unavailable"):
        plan.prepare_options("chembl_assay", {})
    assert not plan.output_root.exists()


@pytest.mark.parametrize(
    "change", ["config", "missing_seed", "foreign_child", "lineage", "revision"]
)
def test_replay_rejects_inconsistent_parent(captured, change):
    parent = captured.parent
    if change == "config":
        parent = replace(parent, resolved_config={"changed": True})
    elif change == "missing_seed":
        parent = replace(parent, launch_context={"child_replay_manifests": {}})
    elif change == "foreign_child":
        parent = replace(
            parent,
            launch_context={
                "child_replay_manifests": {
                    "chembl_assay": captured.child.manifest_id,
                    "../escape": captured.child.manifest_id,
                }
            },
        )
    elif change == "lineage":
        parent = replace(parent, source_refs=())
    else:
        parent = replace(
            parent, code_provenance=replace(parent.code_provenance, git_commit="b" * 40)
        )
    captured.store.save(parent)
    with pytest.raises(ValueError):
        load_composite_replay_inputs(
            captured.config, parent.manifest_id, captured.settings
        )


def test_failed_child_cannot_promote_parent(captured):
    captured.result.is_success = False
    with pytest.raises(ValueError, match="completion mismatch"):
        bind_composite_replay_children(
            captured.parent.manifest_id, [captured.result], captured.settings
        )


def test_unbound_child_cannot_fall_back_to_live_provider(captured):
    plan = load_composite_replay_inputs(
        captured.config, captured.parent.manifest_id, captured.settings
    )
    with pytest.raises(ValueError, match="missing"):
        plan.prepare_options("chembl_target", {})


def test_missing_saved_child_cannot_verify_parent(captured):
    plan = load_composite_replay_inputs(
        captured.config, captured.parent.manifest_id, captured.settings
    )
    (captured.control / "run_manifest" / f"{captured.child.manifest_id}.json").unlink()
    assert "input_snapshot_fingerprint" not in plan.verifier.verify(captured.parent)


def test_family_support_requires_per_run_bindings(captured):
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
        build_replay_family_context,
    )

    assert (
        build_replay_family_context(captured.parent).strict_exact_replay_supported
        is True
    )
    old = replace(captured.parent, launch_context={"execution_context": "composite"})
    assert build_replay_family_context(old).strict_exact_replay_supported is False


def test_partial_stage_selection_cannot_be_promoted(captured):
    parent = replace(
        captured.parent,
        launch_context={**captured.parent.launch_context, "required_only": True},
    )
    captured.store.save(parent)
    with pytest.raises(ValueError, match="lineage"):
        bind_composite_replay_children(
            parent.manifest_id, [captured.result], captured.settings
        )


@pytest.mark.parametrize("drift", [None, "config", "runtime"])
def test_runtime_child_config_must_match_capture(captured, drift):
    plan = load_composite_replay_inputs(
        captured.config, captured.parent.manifest_id, captured.settings
    )
    child = replace(
        captured.child,
        manifest_id=str(uuid5(NAMESPACE_URL, "runtime-child-manifest")),
        run_id=uuid5(NAMESPACE_URL, "runtime-child-run"),
        runtime_config={"exact_replay": True},
    )
    if drift == "config":
        child = replace(child, resolved_config={"changed": True})
    if drift == "runtime":
        child = replace(child, runtime_config={"exact_replay": True, "limit": 17})
    captured.store.save(child)
    if drift:
        with pytest.raises(ValueError, match="changed"):
            plan.validate_runtime_manifest(child.pipeline_name, child.run_id)
    else:
        plan.validate_runtime_manifest(child.pipeline_name, child.run_id)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"git_commit": "b" * 40}, "child code revision mismatch"),
        ({"source_revision_state": "dirty"}, "child requires captured clean code"),
        ({"dependency_lock_hash": "b" * 64}, "child dependency lock mismatch"),
    ],
)
def test_replay_rejects_child_provenance_drift_before_staging(
    captured, changes, message
):
    child = replace(
        captured.child,
        code_provenance=replace(captured.child.code_provenance, **changes),
    )
    captured.store.save(child)
    with pytest.raises(ValueError, match=message):
        load_composite_replay_inputs(
            captured.config, captured.parent.manifest_id, captured.settings
        )
    assert not (captured.control / "composite_replay_inputs").exists()


@pytest.mark.parametrize("seed_limit", [None, 7])
def test_runtime_replay_preserves_captured_seed_limit(
    captured, monkeypatch, seed_limit
):
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_replay_inputs.get_settings",
        lambda: captured.settings,
    )
    runtime = SimpleNamespace(
        replay_of_manifest_id=captured.parent.manifest_id, seed_limit=seed_limit
    )
    if seed_limit is not None:
        with pytest.raises(ValueError, match="preserve the captured seed limit"):
            load_runtime_composite_replay(captured.config, runtime)
    else:
        replay = load_runtime_composite_replay(captured.config, runtime)
        assert replay.parent.manifest_id == captured.parent.manifest_id
        assert not replay.output_root.exists()
