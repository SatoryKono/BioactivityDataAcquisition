"""Unit tests for RunManifestService."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from itertools import permutations
from uuid import UUID

import pytest

import bioetl.infrastructure.control_plane.file_run_manifest_store as manifest_store_module
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec as RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.exceptions import StorageError
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunManifestStore
from bioetl.infrastructure.control_plane import FileRunManifestStore
from tests.helpers.clock import FixedClock


pytestmark = pytest.mark.unit


_InMemoryRunManifestStore = InMemoryRunManifestStore


class _MissingLookupRunManifestStore(_InMemoryRunManifestStore):
    def get(self, manifest_id: str) -> RunManifest | None:
        return None


class _FastAssertionRunManifestStore(_InMemoryRunManifestStore):
    def __init__(self) -> None:
        super().__init__()
        self.asserted_manifest: RunManifest | None = None

    def assert_saved(self, manifest: RunManifest) -> None:
        self.asserted_manifest = manifest

    def get(self, manifest_id: str) -> RunManifest | None:
        raise AssertionError("fallback manifest_id lookup should not run")

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        raise AssertionError("fallback run_id lookup should not run")


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
        dependency_lock_hash="sha256:test-lock",
        config_hash="a" * 64,
        resolved_config_hash="b" * 64,
        effective_config_hash="c" * 64,
        source_fingerprint="s" * 64,
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        contract_schema_hash="abc123",
        dq_policy_ref="chembl.dq.v1",
        rule_bundle_version="dq-rules.v1.0",
        normalization_profile_ref="chembl.activity",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="d" * 64,
        effective_config_artifact_id="effective-config-artifact-001",
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    )


def test_create_manifest_persists_and_links_run_id() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-1",
    )

    manifest = service.create_manifest(
        replace(
            _make_request(),
            workflow_run_id="workflow-run-42",
            workflow_name="chembl_baseline",
            workflow_step_id="run_chembl_activity",
        )
    )

    assert manifest.manifest_id == "manifest-1"
    assert manifest.code_provenance.git_commit == "abc1234"
    assert manifest.code_provenance.source_revision_state == "clean"
    assert manifest.code_provenance.contract_ref == "chembl.activity"
    assert manifest.code_provenance.contract_version == "1.0.0"
    assert manifest.code_provenance.contract_schema_hash == "abc123"
    assert manifest.code_provenance.dq_policy_ref == "chembl.dq.v1"
    assert manifest.code_provenance.rule_bundle_version == "dq-rules.v1.0"
    assert manifest.code_provenance.normalization_profile_ref == "chembl.activity"
    assert manifest.code_provenance.normalization_profile_version == "1.0.0"
    assert manifest.code_provenance.normalization_profile_hash == "d" * 64
    assert manifest.workflow_run_id == "workflow-run-42"
    assert manifest.workflow_name == "chembl_baseline"
    assert manifest.workflow_step_id == "run_chembl_activity"
    assert store.get("manifest-1") == manifest
    assert store.get_by_run_id(manifest.run_id) == manifest


def test_create_manifest_uses_injected_clock_for_created_at() -> None:
    fixed_time = datetime(2026, 4, 23, 12, 15, tzinfo=UTC)
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        clock=FixedClock(fixed_time),
        _manifest_id_factory=lambda: "manifest-clock",
    )

    manifest = service.create_manifest(_make_request())

    assert manifest.created_at == fixed_time


def test_create_manifest_uses_created_at_factory_when_clock_not_provided() -> None:
    fixed_time = datetime(2026, 4, 23, 12, 30, tzinfo=UTC)
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        created_at_factory=lambda: fixed_time,
        _manifest_id_factory=lambda: "manifest-factory",
    )

    manifest = service.create_manifest(_make_request())

    assert manifest.created_at == fixed_time


def test_create_manifest_without_time_seam_uses_deterministic_sentinel() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-sentinel",
    )

    manifest = service.create_manifest(_make_request())

    assert manifest.created_at == MISSING_RUNTIME_TIMESTAMP


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
        source_fingerprint="d" * 64,
    )

    manifest = service.create_manifest(request)

    provenance = manifest.code_provenance
    assert provenance.config_hash == "c" * 64
    assert provenance.resolved_config_hash == "a" * 64
    assert provenance.effective_config_hash == "b" * 64
    assert provenance.source_fingerprint == "d" * 64
    assert manifest.to_dict()["code_provenance"]["resolved_config_hash"] == "a" * 64
    assert manifest.to_dict()["code_provenance"]["effective_config_hash"] == "b" * 64
    assert manifest.to_dict()["code_provenance"]["source_fingerprint"] == "d" * 64


def test_create_manifest_does_not_alias_missing_effective_hash() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-effective-hash",
    )
    request = replace(
        _make_request(),
        config_hash="c" * 64,
        resolved_config_hash="a" * 64,
        effective_config_hash=None,
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )

    with pytest.raises(RuntimeError, match="requires effective_config_hash"):
        service.create_manifest(request)

    assert store.get("manifest-missing-effective-hash") is None


def test_create_manifest_requires_resolved_config_hash() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-resolved-hash",
    )
    request = replace(
        _make_request(),
        config_hash="c" * 64,
        resolved_config_hash=None,
        effective_config_hash="a" * 64,
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )

    with pytest.raises(RuntimeError, match="requires resolved_config_hash"):
        service.create_manifest(request)

    assert store.get("manifest-missing-resolved-hash") is None


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


def test_create_manifest_requires_git_commit_even_for_degraded_profile() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-capability-only",
    )

    with pytest.raises(RuntimeError, match="requires git_commit code provenance"):
        service.create_manifest(
            replace(
                _make_request(),
                git_commit=None,
                provider="openalex",
                entity="works",
                pipeline_name="openalex_works",
                contract_ref="openalex.works",
                source_revision_state="dirty_state_unknown",
                replay_capability=ReplayCapability.REBUILD_ONLY,
                launch_context={
                    "limit": 100,
                    "resume": False,
                    "required_persistence_profile": "degraded_observable",
                },
            )
        )
    assert store.get("manifest-capability-only") is None


def test_create_manifest_requires_dependency_lock_even_for_degraded_profile() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-lock-degraded",
    )

    with pytest.raises(RuntimeError, match="requires dependency_lock_hash"):
        service.create_manifest(
            replace(
                _make_request(),
                dependency_lock_hash=None,
                provider="openalex",
                entity="works",
                pipeline_name="openalex_works",
                contract_ref="openalex.works",
                replay_capability=ReplayCapability.REBUILD_ONLY,
                launch_context={
                    "limit": 100,
                    "resume": False,
                    "required_persistence_profile": "degraded_observable",
                },
            )
        )

    assert store.get("manifest-missing-lock-degraded") is None


def test_create_manifest_rejects_degraded_profile_for_replay_capable_family() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-degraded-replay-capable-family",
    )

    with pytest.raises(
        RuntimeError,
        match="cannot persist required_persistence_profile='degraded_observable'",
    ):
        service.create_manifest(
            replace(
                _make_request(),
                replay_capability=ReplayCapability.REBUILD_ONLY,
                launch_context={
                    "limit": 100,
                    "resume": False,
                    "required_persistence_profile": "degraded_observable",
                },
            )
        )

    assert store.get("manifest-degraded-replay-capable-family") is None


def test_create_manifest_allows_explicit_degraded_opt_down_for_replay_capable_family() -> (
    None
):
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-degraded-opt-down",
    )

    manifest = service.create_manifest(
        replace(
            _make_request(),
            source_revision_state="dirty",
            replay_capability=ReplayCapability.REBUILD_ONLY,
            launch_context={
                "limit": 100,
                "resume": False,
                "configured_required_persistence_profile": "degraded_observable",
                "required_persistence_profile": "degraded_observable",
                "required_persistence_profile_opt_down": True,
            },
        )
    )

    assert manifest.code_provenance.source_revision_state == "dirty"
    assert manifest.launch_context["required_persistence_profile"] == (
        "degraded_observable"
    )
    assert manifest.launch_context["required_persistence_profile_opt_down"] is True
    assert store.get("manifest-degraded-opt-down") == manifest


def test_create_manifest_rejects_exact_capability_claim_without_snapshot_envelope() -> (
    None
):
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-exact-claim-missing-snapshot",
    )

    with pytest.raises(RuntimeError, match="cannot claim exact_replay_supported"):
        service.create_manifest(
            replace(
                _make_request(),
                source_refs=(),
                launch_context={"limit": 100, "resume": False},
                replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
            )
        )

    assert store.get("manifest-exact-claim-missing-snapshot") is None


def test_create_manifest_requires_git_commit_for_explicit_exact_replay() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-git",
    )

    with pytest.raises(RuntimeError, match="requires git_commit code provenance"):
        service.create_manifest(
            replace(
                _make_request(),
                git_commit=None,
                launch_context={"limit": 100, "resume": False, "exact_replay": True},
            )
        )

    assert store.get("manifest-missing-git") is None


def test_create_manifest_requires_dependency_lock_for_explicit_exact_replay() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-lock",
    )

    with pytest.raises(RuntimeError, match="requires dependency_lock_hash"):
        service.create_manifest(
            replace(
                _make_request(),
                dependency_lock_hash=None,
                launch_context={"limit": 100, "resume": False, "exact_replay": True},
            )
        )

    assert store.get("manifest-missing-lock") is None


def test_create_manifest_requires_contract_identity_for_explicit_exact_replay() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-contract-identity",
    )

    with pytest.raises(RuntimeError, match="contract_ref, contract_version"):
        service.create_manifest(
            replace(
                _make_request(),
                contract_ref=None,
                contract_version=None,
                launch_context={"limit": 100, "resume": False, "exact_replay": True},
            )
        )

    assert store.get("manifest-missing-contract-identity") is None


def test_create_manifest_requires_effective_config_artifact_for_replay_ready() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-effective-config-artifact",
    )

    with pytest.raises(RuntimeError, match="effective_config_artifact_id"):
        service.create_manifest(
            replace(
                _make_request(),
                effective_config_artifact_id=None,
                launch_context={
                    "limit": 100,
                    "resume": False,
                    "required_persistence_profile": "replay_ready",
                },
            )
        )

    assert store.get("manifest-missing-effective-config-artifact") is None


def test_create_manifest_rejects_undocumented_source_revision_state() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-undocumented-state",
    )

    with pytest.raises(RuntimeError, match="documented source_revision_state"):
        service.create_manifest(
            replace(
                _make_request(),
                source_revision_state="some_new_unknown_state",
            )
        )

    assert store.get("manifest-undocumented-state") is None


def test_create_manifest_rejects_missing_git_commit_with_clean_state() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-git-clean",
    )

    with pytest.raises(RuntimeError, match="requires git_commit code provenance"):
        service.create_manifest(
            replace(
                _make_request(),
                git_commit=None,
                source_revision_state="clean",
            )
        )

    assert store.get("manifest-missing-git-clean") is None


def test_create_manifest_requires_input_snapshots_for_explicit_exact_replay() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-missing-snapshots",
    )

    with pytest.raises(
        RuntimeError,
        match="immutable input snapshot envelope",
    ):
        service.create_manifest(
            replace(
                _make_request(),
                source_refs=(),
                launch_context={"limit": 100, "resume": False, "exact_replay": True},
            )
        )

    assert store.get("manifest-missing-snapshots") is None


def test_create_manifest_rejects_replay_ready_profile_without_launch_snapshots() -> (
    None
):
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-replay-ready-missing-snapshots",
    )

    with pytest.raises(
        RuntimeError,
        match="requires immutable input snapshots",
    ):
        service.create_manifest(
            replace(
                _make_request(),
                source_refs=(
                    RunSourceRef(
                        provider="chembl",
                        entity="activity",
                        pipeline_name="chembl_activity",
                        query="assay_type=B",
                        input_snapshots=(),
                    ),
                ),
                replay_capability=ReplayCapability.REBUILD_ONLY,
                launch_context={
                    "limit": 100,
                    "resume": False,
                    "required_persistence_profile": "replay_ready",
                },
            )
        )

    assert store.get("manifest-replay-ready-missing-snapshots") is None


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


def test_create_manifest_uses_store_specific_post_save_assertion() -> None:
    store = _FastAssertionRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-fast-assertion",
    )

    manifest = service.create_manifest(_make_request())

    assert store.asserted_manifest == manifest


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
    request = _make_request()

    manifest = service.create_manifest(request)
    identity_payload = service._build_execution_identity_payload(
        request=request,
        code_provenance=service._build_code_provenance(request),
        run_type=service._normalize_run_type(request.run_type),
    )

    assert identity_payload["silver_filter_compatibility_mode"] == (
        "structural_only_compat"
    )
    assert (
        manifest.execution_fingerprint
        == "fd1efe74f82712f4f3d74db19f16007e324eba548ab6610a7942f16bbaf07673"
    )


def test_execution_fingerprint_changes_when_git_commit_changes() -> None:
    service = RunManifestService(
        manifest_port=_InMemoryRunManifestStore(),
        _manifest_id_factory=lambda: "manifest-git-commit",
    )

    manifest = service.create_manifest(_make_request())
    manifest_git_drifted = service.create_manifest(
        replace(_make_request(), git_commit="def5678")
    )

    assert manifest.code_provenance.git_commit == "abc1234"
    assert manifest_git_drifted.code_provenance.git_commit == "def5678"
    assert manifest.execution_fingerprint != manifest_git_drifted.execution_fingerprint


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


def test_create_manifest_requires_clean_source_revision_state_for_strict_replay() -> (
    None
):
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-dirty-source",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "requires clean source_revision_state for exact replay, "
            "replay_ready, and forensic_grade contexts"
        ),
    ):
        service.create_manifest(
            replace(
                _make_request(),
                source_revision_state="dirty",
                launch_context={"limit": 100, "resume": False, "exact_replay": True},
            )
        )

    assert store.get("manifest-dirty-source") is None


def test_create_manifest_reports_promoted_profile_on_dirty_source_state() -> None:
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-promoted-dirty-source",
    )

    with pytest.raises(RuntimeError) as exc_info:
        service.create_manifest(
            replace(
                _make_request(),
                source_revision_state="dirty",
                launch_context={
                    "limit": 100,
                    "resume": False,
                    "configured_required_persistence_profile": "degraded_observable",
                    "required_persistence_profile": "replay_ready",
                },
            )
        )

    message = str(exc_info.value)
    assert "configured_required_persistence_profile=degraded_observable" in message
    assert "required_persistence_profile=replay_ready" in message
    assert "profile_was_promoted=true" in message
    assert "pipeline=chembl_activity" in message
    assert store.get("manifest-promoted-dirty-source") is None


def test_create_manifest_allows_dirty_source_revision_state_for_degraded_context() -> (
    None
):
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-dirty-degraded",
    )

    manifest = service.create_manifest(
        replace(
            _make_request(),
            provider="openalex",
            entity="works",
            pipeline_name="openalex_works",
            contract_ref="openalex.works",
            source_revision_state="dirty",
            replay_capability=ReplayCapability.REBUILD_ONLY,
            launch_context={
                "limit": 100,
                "resume": False,
                "required_persistence_profile": "degraded_observable",
            },
        )
    )

    assert manifest.code_provenance.source_revision_state == "dirty"
    assert store.get("manifest-dirty-degraded") == manifest


def test_create_manifest_reports_snapshot_gap_before_dirty_source_state_in_strict_context() -> (
    None
):
    store = _InMemoryRunManifestStore()
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-strict-snapshot-gap",
    )

    with pytest.raises(RuntimeError, match="requires immutable input snapshots"):
        service.create_manifest(
            replace(
                _make_request(),
                source_revision_state="dirty",
                source_refs=(),
                replay_capability=ReplayCapability.REBUILD_ONLY,
                launch_context={
                    "limit": 100,
                    "resume": False,
                    "required_persistence_profile": "replay_ready",
                },
            )
        )

    assert store.get("manifest-strict-snapshot-gap") is None
