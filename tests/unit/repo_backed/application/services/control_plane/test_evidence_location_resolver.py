# pyright: reportArgumentType=false
"""Bounded evidence-location resolver (RF-003)."""

from __future__ import annotations

import errno
import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.evidence_location import (
    EvidenceLocationLegacyRootPolicy,
    EvidenceLocationResolver,
)
from bioetl.composition.runtime_builders.evidence_location_registration import (
    FileEvidenceReadContextFactory,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    build_run_evidence_location,
)
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)


def _create_symlink_or_skip(
    link: Path, target: Path, *, target_is_directory: bool = False
) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except NotImplementedError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")
    except OSError as exc:
        unsupported = {
            errno.EPERM,
            errno.ENOSYS,
            getattr(errno, "EOPNOTSUPP", errno.EPERM),
        }
        if exc.errno in unsupported or getattr(exc, "winerror", None) == 1314:
            pytest.skip(f"symlink creation is not permitted: {exc}")
        raise


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

_SOURCE_A = "a" * 64
_SOURCE_B = "b" * 64
_RUN_A = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
_RUN_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
_WF = "3dc8ffe4-305b-5d4b-a945-fe8e78f03828"


def _location(**overrides: object):
    payload = {
        "kind": EvidenceLocationKind.PIPELINE,
        "owner": "chembl_assay",
        "run_id": _RUN_A,
        "workflow_run_id": _WF,
        "runtime_source_id": _SOURCE_A,
        "root_alias": DEFAULT_EVIDENCE_ROOT_ALIAS,
        "relative_data_root": "workflow-a/chembl_assay",
    }
    payload.update(overrides)
    return build_run_evidence_location(**payload)  # type: ignore[arg-type]


def _resolver(
    tmp_path: Path,
    *,
    legacy: EvidenceLocationLegacyRootPolicy = (
        EvidenceLocationLegacyRootPolicy.ALLOW_STANDARD_ALIAS_BASE
    ),
) -> tuple[EvidenceLocationResolver, FileEvidenceLocationStore, Path]:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    report_root = tmp_path / "run-reports"
    report_root.mkdir()
    store = FileEvidenceLocationStore(report_root=report_root)
    aliases = default_evidence_root_alias_registry(dashboard_data_root=data_root)
    resolver = EvidenceLocationResolver(
        locations=store,
        aliases=aliases,
        opener=FileEvidenceReadContextFactory(),
        legacy_root_policy=legacy,
    )
    return resolver, store, data_root


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


def test_two_data_roots_resolve_independently(tmp_path: Path) -> None:
    resolver, store, data_root = _resolver(tmp_path)
    root_a = data_root / "workflow-a" / "chembl_assay"
    root_b = data_root / "workflow-b" / "chembl_assay"
    root_a.mkdir(parents=True)
    root_b.mkdir(parents=True)
    (root_a / "marker.txt").write_text("A", encoding="utf-8")
    (root_b / "marker.txt").write_text("B", encoding="utf-8")

    loc_a = _location(run_id=_RUN_A, relative_data_root="workflow-a/chembl_assay")
    loc_b = _location(run_id=_RUN_B, relative_data_root="workflow-b/chembl_assay")
    store.register(loc_a)
    store.register(loc_b)

    resolved_a = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    resolved_b = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_B)
    assert resolved_a.code is EvidenceLocationLookupCode.FOUND
    assert resolved_b.code is EvidenceLocationLookupCode.FOUND
    assert resolved_a.data_root == root_a.resolve()
    assert resolved_b.data_root == root_b.resolve()
    assert (resolved_a.data_root / "marker.txt").read_text(encoding="utf-8") == "A"
    assert (resolved_b.data_root / "marker.txt").read_text(encoding="utf-8") == "B"


def test_identity_conflict_fails_closed_without_foreign_fallback(
    tmp_path: Path,
) -> None:
    resolver, store, data_root = _resolver(tmp_path)
    isolated = data_root / "workflow-a" / "chembl_assay"
    isolated.mkdir(parents=True)
    store.register(_location())
    foreign = data_root / "foreign" / "chembl_assay"
    foreign.mkdir(parents=True)
    (foreign / "steal.txt").write_text("nope", encoding="utf-8")

    result = resolver.resolve(
        kind="pipeline",
        owner="chembl_assay",
        run_id=_RUN_A,
        expected_runtime_source_id=_SOURCE_B,
    )
    assert result.code is EvidenceLocationLookupCode.IDENTITY_CONFLICT
    assert result.context is None
    assert result.data_root is None


def test_legacy_missing_opens_only_standard_alias_base(tmp_path: Path) -> None:
    resolver, _store, data_root = _resolver(tmp_path)
    isolated = data_root / "workflow-a" / "chembl_assay"
    isolated.mkdir(parents=True)
    (isolated / "secret.txt").write_text("isolated-only", encoding="utf-8")

    result = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert result.code is EvidenceLocationLookupCode.LOCATION_MISSING
    assert result.used_legacy_standard_root is True
    assert result.data_root == data_root
    # Context is bound to alias base, not auto-promoted to the isolated folder.
    assert result.context is not None
    assert result.context.data_root == data_root
    assert result.context.data_root != isolated.resolve()


def test_legacy_policy_require_explicit_record_stays_closed(tmp_path: Path) -> None:
    resolver, _store, _data_root = _resolver(
        tmp_path,
        legacy=EvidenceLocationLegacyRootPolicy.REQUIRE_EXPLICIT_RECORD,
    )
    result = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert result.code is EvidenceLocationLookupCode.LOCATION_MISSING
    assert result.context is None
    assert result.data_root is None


def test_resolve_does_not_write_or_repair_location_records(tmp_path: Path) -> None:
    resolver, store, _data_root = _resolver(tmp_path)
    catalog = tmp_path / "run-reports" / "_evidence-locations"
    before = list(catalog.rglob("*")) if catalog.exists() else []
    resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    after = list(catalog.rglob("*")) if catalog.exists() else []
    assert before == after
    assert (
        store.lookup(kind="pipeline", owner="chembl_assay", run_id=_RUN_A).code
        is EvidenceLocationLookupCode.LOCATION_MISSING
    )


def test_manifest_missing_stays_distinct_after_resolve(tmp_path: Path) -> None:
    resolver, store, data_root = _resolver(tmp_path)
    isolated = data_root / "workflow-a" / "chembl_assay"
    isolated.mkdir(parents=True)
    store.register(_location())
    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert resolved.is_open
    manifest_lookup = resolver.load_manifest(resolved, run_id=UUID(_RUN_A))
    assert manifest_lookup.code is EvidenceLocationLookupCode.MANIFEST_MISSING


def test_load_manifest_rejects_run_id_different_from_resolved_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, store, _data_root = _resolver(tmp_path)
    store.register(_location())
    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    calls: list[object] = []

    def get_manifest(_self: object, run_id: object) -> None:
        calls.append(run_id)
        return None

    monkeypatch.setattr(FileRunManifestStore, "get_by_run_id", get_manifest)

    lookup = resolver.load_manifest(resolved, run_id=UUID(_RUN_B))

    assert lookup.code is EvidenceLocationLookupCode.IDENTITY_CONFLICT
    assert lookup.detail == "manifest_run_id_mismatch"
    assert calls == []


def test_load_manifest_string_run_id_finds_saved_pipeline_manifest(
    tmp_path: Path,
) -> None:
    """String ownership keys must coerce to RunID before the file store."""
    from bioetl.domain.types import RunID
    from tests.unit.application.services.run_manifest_test_support import (
        RunManifestOverrides,
        make_run_manifest,
    )

    resolver, store, data_root = _resolver(tmp_path)
    isolated = data_root / "workflow-a" / "chembl_assay"
    isolated.mkdir(parents=True)
    store.register(_location())
    manifest_store = FileRunManifestStore(
        base_path=isolated / "output" / "control" / "run_manifest"
    )
    saved = make_run_manifest(
        manifest_id="manifest-string-run",
        run_id=RunID(UUID(_RUN_A)),
        overrides=RunManifestOverrides(pipeline_name="chembl_assay", entity="assay"),
    )
    manifest_store.save(saved)

    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    # Same string form accepted by resolve() must not yield location_invalid.
    lookup = resolver.load_manifest(resolved, run_id=_RUN_A)
    assert lookup.code is EvidenceLocationLookupCode.FOUND
    assert lookup.detail == "manifest_present"


def test_resolved_context_uses_standard_verifier_on_real_bytes(
    tmp_path: Path,
) -> None:
    resolver, store, data_root = _resolver(tmp_path)
    isolated = data_root / "workflow-a" / "chembl_assay"
    isolated.mkdir(parents=True)
    evidence = _seed_replay_objects(isolated, run_id=UUID(_RUN_A))
    store.register(_location())

    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert resolved.context is not None
    checks = resolved.context.verify_replay_objects(evidence)
    assert checks == dict.fromkeys(evidence.objects, True)

    # Mutating Bronze fails on re-read; locator presence is not READY proof.
    evidence.batch.write_bytes(b"tampered")
    assert (
        resolved.context.verify_replay_objects(evidence)["input_snapshot_fingerprint"]
        is False
    )


def test_explicit_dot_relative_uses_standard_root(tmp_path: Path) -> None:
    resolver, store, data_root = _resolver(
        tmp_path,
        legacy=EvidenceLocationLegacyRootPolicy.REQUIRE_EXPLICIT_RECORD,
    )
    store.register(_location(relative_data_root="."))
    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert resolved.code is EvidenceLocationLookupCode.FOUND
    assert resolved.data_root == data_root
    assert resolved.used_legacy_standard_root is True


def test_context_rechecks_child_paths_before_manifest_read(tmp_path: Path) -> None:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    context = FileEvidenceReadContextFactory().open(
        data_root,
        trusted_alias_base=data_root,
    )
    outside = tmp_path / "outside-output"
    outside.mkdir()
    _create_symlink_or_skip(data_root / "output", outside, target_is_directory=True)

    with pytest.raises(EvidenceLocationInvalidError, match="escapes|symlink"):
        context.get_manifest_by_run_id(UUID(_RUN_A))


@pytest.mark.parametrize("linked_path", ["index", "record"])
def test_context_rejects_symlinked_manifest_index_and_record(
    tmp_path: Path,
    linked_path: str,
) -> None:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    context = FileEvidenceReadContextFactory().open(
        data_root,
        trusted_alias_base=data_root,
    )
    store_base = data_root / "output" / "control" / "run_manifest"
    index = store_base / "_by_run_id" / f"{_RUN_A}.txt"
    index.parent.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("manifest-a", encoding="utf-8")

    if linked_path == "index":
        _create_symlink_or_skip(index, outside)
    else:
        index.write_text("manifest-a", encoding="utf-8")
        record = store_base / "manifest-a.json"
        _create_symlink_or_skip(record, outside)

    with pytest.raises(EvidenceLocationInvalidError, match="symlink|escapes"):
        context.get_manifest_by_run_id(UUID(_RUN_A))


@pytest.mark.parametrize("linked_path", ["index", "record"])
def test_context_rejects_symlinked_effective_config_index_and_record(
    tmp_path: Path,
    linked_path: str,
) -> None:
    """Outward effective-config symlinks must not verify as trusted evidence."""
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    context = FileEvidenceReadContextFactory().open(
        data_root,
        trusted_alias_base=data_root,
    )
    store_base = data_root / "output" / "control" / "effective_config"
    index = store_base / "_by_run_id" / f"{_RUN_A}.txt"
    index.parent.mkdir(parents=True)

    config = {
        "identity_version": "effective-config-v1",
        "config_data": {"limit": 100},
    }
    config_hash = stable_json_hash(config)
    outside_payload = {
        "artifact_id": "saved-config",
        "semantic_artifact": {"effective_execution_config": config},
    }
    outside = tmp_path / "outside-config.json"
    outside.write_text(
        json.dumps(outside_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if linked_path == "index":
        _create_symlink_or_skip(index, outside)
    else:
        index.write_text("saved-config", encoding="utf-8")
        record = store_base / "saved-config.json"
        _create_symlink_or_skip(record, outside)

    evidence = SimpleNamespace(
        run_id=UUID(_RUN_A),
        code_provenance=SimpleNamespace(
            effective_config_hash=config_hash,
            effective_config_artifact_id="saved-config",
            dependency_lock_hash=None,
        ),
        source_refs=(),
        objects={},
    )
    with pytest.raises(EvidenceLocationInvalidError, match="symlink|escapes"):
        context.verify_replay_objects(evidence)  # type: ignore[arg-type]


def test_workflow_location_reads_workflow_manifest_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, store, _data_root = _resolver(tmp_path)
    workflow_location = _location(
        kind=EvidenceLocationKind.WORKFLOW,
        owner="workflow-a",
        run_id=_WF,
        workflow_run_id=None,
    )
    store.register(workflow_location)
    workflow_manifest = SimpleNamespace(workflow_run_id=UUID(_WF))
    calls: list[UUID] = []

    def fail_pipeline_lookup(_self: object, _run_id: object) -> None:
        pytest.fail("workflow lookup must not use the pipeline manifest store")

    def get_workflow_manifest(_self: object, run_id: UUID) -> SimpleNamespace:
        calls.append(run_id)
        return workflow_manifest

    monkeypatch.setattr(FileRunManifestStore, "get_by_run_id", fail_pipeline_lookup)
    monkeypatch.setattr(
        FileWorkflowManifestStore,
        "get_by_run_id",
        get_workflow_manifest,
    )

    resolved = resolver.resolve(
        kind="workflow",
        owner="workflow-a",
        run_id=_WF,
    )
    manifest_lookup = resolver.load_manifest(resolved, run_id=UUID(_WF))

    assert manifest_lookup.code is EvidenceLocationLookupCode.FOUND
    assert calls == [UUID(_WF)]


def test_load_manifest_accepts_string_workflow_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """String kind ``\"workflow\"`` must use the workflow store (not enum-only)."""
    resolver, store, _data_root = _resolver(tmp_path)
    store.register(
        _location(
            kind=EvidenceLocationKind.WORKFLOW,
            owner="workflow-a",
            run_id=_WF,
            workflow_run_id=None,
        )
    )
    calls: list[UUID] = []

    def fail_pipeline_lookup(_self: object, _run_id: object) -> None:
        pytest.fail("string workflow kind must not use pipeline store")

    def get_workflow_manifest(_self: object, run_id: UUID) -> SimpleNamespace:
        calls.append(run_id)
        return SimpleNamespace(workflow_run_id=run_id)

    monkeypatch.setattr(FileRunManifestStore, "get_by_run_id", fail_pipeline_lookup)
    monkeypatch.setattr(
        FileWorkflowManifestStore,
        "get_by_run_id",
        get_workflow_manifest,
    )

    resolved = resolver.resolve(kind="workflow", owner="workflow-a", run_id=_WF)
    assert resolved.requested_kind == "workflow"
    lookup = resolver.load_manifest(resolved, run_id=UUID(_WF))
    assert lookup.code is EvidenceLocationLookupCode.FOUND
    assert calls == [UUID(_WF)]
