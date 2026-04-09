"""Unit tests for RunManifestService."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import replace
from uuid import UUID

from hypothesis import given
from hypothesis import strategies as st
import pytest

from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID, RunType


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
        config_hash="deadbeef",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        contract_schema_hash="abc123",
        dq_policy_ref="chembl.dq.v1",
        rule_bundle_version="dq-rules.v1.0",
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
    assert manifest.code_provenance.contract_ref == "chembl.activity"
    assert manifest.code_provenance.contract_version == "1.0.0"
    assert manifest.code_provenance.contract_schema_hash == "abc123"
    assert manifest.code_provenance.dq_policy_ref == "chembl.dq.v1"
    assert manifest.code_provenance.rule_bundle_version == "dq-rules.v1.0"
    assert store.get("manifest-1") == manifest
    assert store.get_by_run_id(manifest.run_id) == manifest


def test_create_manifest_fails_closed_when_persisted_manifest_is_not_resolvable() -> None:
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
        == "64f13976644204fa48aac79ff42dbd9c735e9b064c7f8f8fc76241dd0068eddf"
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


@given(
    source_refs=st.permutations(
        (
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
    ),
    planned_artifacts=st.permutations(
        (
            RunArtifactRef(layer="bronze", path="data/output/bronze/chembl/activity"),
            RunArtifactRef(layer="silver", path="data/output/silver/chembl/activity"),
            RunArtifactRef(layer="gold", path="data/output/gold/chembl/activity"),
        )
    ),
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
        ),
        planned_artifacts=(
            RunArtifactRef(layer="bronze", path="data/output/bronze/chembl/activity"),
            RunArtifactRef(layer="silver", path="data/output/silver/chembl/activity"),
            RunArtifactRef(layer="gold", path="data/output/gold/chembl/activity"),
        ),
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
