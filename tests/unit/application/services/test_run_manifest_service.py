"""Unit tests for RunManifestService."""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.domain.control_plane import RunArtifactRef, RunManifest, RunSourceRef
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


def _make_request() -> RunManifestCreateRequest:
    return RunManifestCreateRequest(
        run_id=RunID(uuid4()),
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
