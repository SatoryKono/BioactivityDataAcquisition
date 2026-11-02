# pyright: reportArgumentType=false
"""Bounded evidence-location resolver (RF-003)."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.evidence_location import (
    EvidenceLocationLegacyRootPolicy,
    EvidenceLocationResolver,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
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
from bioetl.infrastructure.control_plane.file_evidence_read_context import (
    FileEvidenceReadContextFactory,
)
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)

pytestmark = pytest.mark.unit

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
