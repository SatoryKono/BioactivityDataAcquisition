"""Unit tests for RunManifestService."""

from __future__ import annotations

from itertools import permutations
from datetime import UTC, datetime
from dataclasses import replace
from uuid import UUID

import pytest

import bioetl.infrastructure.control_plane.file_run_manifest_store as manifest_store_module
from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.exceptions import StorageError
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import FileRunManifestStore


class _InMemoryRunManifestStore(RunManifestPort):
    def __init__(self) -> None:
        self._items: dict[str, RunManifest] = {}
        self._by_run_id: dict[str, str] = {}

    def save(self, manifest: RunManifest) -> None:
        self._items[manifest.manifest_id] = manifest
        self._by_run_id[str(manifest.run_id)] = manifest.manifest_id

    def get(self, manifest_id: str) -> RunManifest | None:
        return self._items.get(manifest_id)

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        manifest_id = self._by_run_id.get(str(run_id))
        return None if manifest_id is None else self._items.get(manifest_id)


class _MissingLookupRunManifestStore(_InMemoryRunManifestStore):
    def get(self, manifest_id: str) -> RunManifest | None:
        return None


def _make_request() -> RunManifestCreateRequest:
    return RunManifestCreateRequest(
        run_id=RunID(UUID("11111111-1111-1111-1111-111111111111")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 100, "resume": False},
        runtime_config={"run_type": "incremental", "limit": 100},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="assay_type=B",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-b",
                        content_hash="hash-b",
                        immutable_uri="file:///snapshots/b.jsonl",
                        query_fingerprint="query-b",
                        captured_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
                    ),
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-b-2",
                        content_hash="hash-b-2",
                        immutable_uri="file:///snapshots/b-2.jsonl",
                        query_fingerprint="query-b-2",
                        captured_at=datetime(2026, 4, 9, 10, 5, tzinfo=UTC),
                    ),
                ),
            ),
        ),
        planned_artifacts=(
            RunArtifactRef(layer="bronze", path="data/output/bronze/chembl/activity"),
        ),
        pipeline_version="1.2.3",
        git_commit="abc1234",
        source_revision_state="clean",
        config_hash="a" * 64,
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        contract_schema_hash="abc123",
        dq_policy_ref="chembl.dq.v1",
        rule_bundle_version="dq-rules.v1.0",
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    )


def test_create_manifest_persists_and_links_run_id() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-1",
    )

    manifest = service.create_manifest(_make_request())

    assert manifest.manifest_id == "manifest-1"
    assert manifest.code_provenance.git_commit == "abc1234"
    assert manifest.code_provenance.source_revision_state == "clean"
    assert manifest.code_provenance.contract_ref == "chembl.activity"
    assert manifest.code_provenance.contract_version == "1.0.0"
    assert manifest.code_provenance.contract_schema_hash == "abc123"
    assert manifest.code_provenance.dq_policy_ref == "chembl.dq.v1"
    assert manifest.code_provenance.rule_bundle_version == "dq-rules.v1.0"
    assert store.get("manifest-1") == manifest
    assert store.get_by_run_id(manifest.run_id) == manifest


def test_create_manifest_preserves_distinct_config_hash_surfaces() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-config-hashes",
    )
    request = replace(
        _make_request(),
        config_hash="c" * 64,
        resolved_config_hash="a" * 64,
        effective_config_hash="b" * 64,
    )

    manifest = service.create_manifest(request)

    provenance = manifest.code_provenance
    assert provenance.config_hash == "c" * 64
    assert provenance.resolved_config_hash == "a" * 64
    assert provenance.effective_config_hash == "b" * 64
    assert manifest.to_dict()["code_provenance"]["resolved_config_hash"] == "a" * 64
    assert manifest.to_dict()["code_provenance"]["effective_config_hash"] == "b" * 64


def test_create_manifest_preserves_resume_only_replay_capability() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-resume-only",
    )

    manifest = service.create_manifest(
        replace(
            _make_request(),
            replay_capability=ReplayCapability.RESUME_ONLY,
        )
    )

    assert manifest.replay_capability == ReplayCapability.RESUME_ONLY
    assert manifest.to_dict()["replay_capability"] == "resume_only"


def test_create_manifest_requires_git_commit_for_exact_replay_capability() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-git",
    )

    with pytest.raises(RuntimeError, match="requires git_commit code provenance"):
        service.create_manifest(replace(_make_request(), git_commit=None))

    assert store.get("manifest-missing-git") is None


def test_create_manifest_persists_explicit_replay_parentage() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-replay-child",
    )

    manifest = service.create_manifest(
        replace(
            _make_request(),
            replay_of_run_id="00000000-0000-0000-0000-000000000999",
            replay_of_manifest_id="manifest-parent",
        )
    )

    assert manifest.replay_of_run_id == "00000000-0000-0000-0000-000000000999"
    assert manifest.replay_of_manifest_id == "manifest-parent"
    assert manifest.to_dict()["replay_of_run_id"] == (
        "00000000-0000-0000-0000-000000000999"
    )
    assert manifest.to_dict()["replay_of_manifest_id"] == "manifest-parent"


def test_create_manifest_fails_closed_when_persisted_manifest_is_not_resolvable() -> (
    None
):
    store = _MissingLookupRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing",
    )

    with pytest.raises(
        RuntimeError,
        match="manifest is not resolvable by manifest_id",
    ):
        service.create_manifest(_make_request())


def test_create_manifest_aborts_when_atomic_persistence_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-storage-failure",
    )
    original_atomic_write_text = manifest_store_module.atomic_write_text
    call_count = {"value": 0}

    def _fail_on_index_write(path, text, encoding="utf-8") -> None:
        call_count["value"] += 1
        if call_count["value"] == 1:
            original_atomic_write_text(path, text, encoding=encoding)
            return
        raise OSError("run index write failed")

    monkeypatch.setattr(
        "bioetl.infrastructure.control_plane.file_run_manifest_store.atomic_write_text",
        _fail_on_index_write,
    )

    with pytest.raises(StorageError, match="Run manifest save failed"):
        service.create_manifest(_make_request())

    assert store.get("manifest-storage-failure") is None


def test_execution_fingerprint_is_stable_for_equivalent_requests() -> None:
    request = _make_request()
    service_a = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-a",
    )
    service_b = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-b",
    )

    manifest_a = service_a.create_manifest(request)
    manifest_b = service_b.create_manifest(request)

    assert manifest_a.manifest_id != manifest_b.manifest_id
    assert manifest_a.execution_fingerprint == manifest_b.execution_fingerprint


def test_execution_fingerprint_ignores_run_occurrence_drift() -> None:
    request = _make_request()
    drifted_request = replace(
        request,
        run_id=RunID(UUID("22222222-2222-2222-2222-222222222222")),
    )
    service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-a",
    )

    manifest = service.create_manifest(request)
    manifest_drifted = service.create_manifest(drifted_request)

    assert manifest.run_id != manifest_drifted.run_id
    assert manifest.execution_fingerprint == manifest_drifted.execution_fingerprint


def test_execution_fingerprint_ignores_source_ref_and_artifact_order() -> None:
    request = _make_request()
    request_reordered = replace(
        request,
        launch_context={"resume": False, "limit": 100},
        runtime_config={"limit": 100, "run_type": "incremental"},
        resolved_config={"entity_type": "activity", "provider": "chembl"},
        source_refs=tuple(reversed(request.source_refs)),
        planned_artifacts=tuple(reversed(request.planned_artifacts)),
    )
    service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-a",
    )

    manifest = service.create_manifest(request)
    manifest_reordered = service.create_manifest(request_reordered)

    assert manifest.execution_fingerprint == manifest_reordered.execution_fingerprint


def test_execution_fingerprint_matches_golden_value() -> None:
    service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-golden",
    )

    manifest = service.create_manifest(_make_request())

    assert (
        manifest.execution_fingerprint
        == "5bc0cc26f2bd6ef5223410aa8b818d60398ac76f46f2b5853f59818dc310ede2"
    )


def test_execution_fingerprint_rejects_non_finite_numeric_payloads() -> None:
    service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-non-finite",
    )

    with pytest.raises(
        ValueError,
        match="Canonical JSON serialization does not allow NaN or Infinity",
    ):
        service.create_manifest(
            replace(
                _make_request(),
                launch_context={"limit": float("nan"), "resume": False},
            )
        )


_PERMUTATION_SOURCE_REFS = (
    RunSourceRef(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        query="assay_type=B",
        input_snapshots=(
            RunInputSnapshotRef(
                snapshot_id="snapshot-b",
                content_hash="hash-b",
            ),
        ),
    ),
    RunSourceRef(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        query="assay_type=F",
        input_snapshots=(
            RunInputSnapshotRef(
                snapshot_id="snapshot-f",
                content_hash="hash-f",
            ),
        ),
    ),
    RunSourceRef(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        query="assay_type=T",
        input_snapshots=(
            RunInputSnapshotRef(
                snapshot_id="snapshot-t",
                content_hash="hash-t",
            ),
        ),
    ),
)

_PERMUTATION_ARTIFACTS = (
    RunArtifactRef(layer="bronze", path="data/output/bronze/chembl/activity"),
    RunArtifactRef(layer="silver", path="data/output/silver/chembl/activity"),
    RunArtifactRef(layer="gold", path="data/output/gold/chembl/activity"),
)


@pytest.mark.parametrize(
    ("source_refs", "planned_artifacts"),
    [
        (source_refs, planned_artifacts)
        for source_refs in permutations(_PERMUTATION_SOURCE_REFS)
        for planned_artifacts in permutations(_PERMUTATION_ARTIFACTS)
    ],
)
def test_execution_fingerprint_is_permutation_invariant_for_set_like_manifest_fields(
    source_refs: tuple[RunSourceRef, ...],
    planned_artifacts: tuple[RunArtifactRef, ...],
) -> None:
    service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-a",
    )
    canonical_request = replace(
        _make_request(),
        source_refs=_PERMUTATION_SOURCE_REFS,
        planned_artifacts=_PERMUTATION_ARTIFACTS,
        launch_context={"resume": False, "limit": 100},
        runtime_config={"limit": 100, "run_type": "incremental"},
        resolved_config={"entity_type": "activity", "provider": "chembl"},
    )
    request = replace(
        canonical_request,
        source_refs=source_refs,
        planned_artifacts=planned_artifacts,
    )

    manifest = service.create_manifest(canonical_request)
    manifest_permuted = service.create_manifest(request)

    assert manifest.execution_fingerprint == manifest_permuted.execution_fingerprint


def test_execution_fingerprint_ignores_nested_input_snapshot_order() -> None:
    service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-snapshots",
    )
    request = _make_request()
    reordered = replace(
        request,
        source_refs=(
            replace(
                request.source_refs[0],
                input_snapshots=tuple(reversed(request.source_refs[0].input_snapshots)),
            ),
        ),
    )

    manifest = service.create_manifest(request)
    manifest_reordered = service.create_manifest(reordered)

    assert manifest.execution_fingerprint == manifest_reordered.execution_fingerprint
