"""Resolver/isolation coverage for selected-run status (split from oversized module)."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.evidence_location.resolver import (
    EvidenceLocationLegacyRootPolicy,
    EvidenceLocationResolveResult,
    EvidenceLocationResolver,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
)
from bioetl.domain.run_reports.pipeline_report_assembly import build_pipeline_run_report
from bioetl.domain.run_reports.selected_status import DOMAINS
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.interfaces.http._selected_run_unavailable import bind_runtime_source_id
from bioetl.interfaces.http.selected_run_status import load_selected_run_status
from tests.unit.interfaces.http.test_selected_run_status import persist

pytestmark = pytest.mark.unit


def test_isolated_manifest_not_visible_through_default_port(tmp_path, monkeypatch):
    """RF-001 unit surface: report COMPLETE, default manifest port → INSUFFICIENT.

    Change boundary for later RF work: evidence lookup/presentation only.
    Persistence, resume, and report bytes stay untouched by selected-run reads.
    """
    from hashlib import sha256
    from types import SimpleNamespace
    from uuid import UUID

    from bioetl.composition.bootstrap.assembly import health_server as assembly
    from bioetl.domain.control_plane import (
        ReplayCapability,
        RunInputSnapshotRef,
        RunSourceRef,
    )
    from bioetl.domain.normalization.json import stable_json_hash
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
        FileEffectiveConfigArtifactStore,
    )
    from bioetl.interfaces.http._recent_run_presentation import _replay_status
    from tests.unit.application.services.run_manifest_test_support import (
        RunManifestOverrides,
        make_run_manifest,
    )

    run_id = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
    manifest_id = "0f77f009-8565-539a-8c79-5e75a5039546"
    foreign_run = "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"
    reports = tmp_path / "reports"
    default_data = tmp_path / "data"
    isolated = default_data / "workflow-limit100-20261102T144403Z" / "chembl_assay"
    foreign = default_data / "workflow-foreign" / "chembl_assay"
    reports.mkdir()
    default_data.mkdir()

    def materialize(root, rid: str, mid: str, payload: bytes):
        control = root / "output" / "control"
        config = {
            "identity_version": "effective-config-v1",
            "config_data": {"limit": 100},
        }
        FileEffectiveConfigArtifactStore(control / "effective_config").save(
            artifact_id=f"cfg-{rid[:8]}",
            run_id=RunID(UUID(rid)),
            payload={
                "artifact_id": f"cfg-{rid[:8]}",
                "semantic_artifact": {"effective_execution_config": config},
            },
        )
        lock_hash = sha256(payload).hexdigest()
        lock_path = control / "dependency_locks" / lock_hash
        bronze = root / "output" / "bronze" / "chembl" / "assay" / "batch.jsonl"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        bronze.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_bytes(payload)
        bronze.write_bytes(payload)
        return replace(
            make_run_manifest(
                manifest_id=mid,
                run_id=RunID(UUID(rid)),
                replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
                source_refs=(
                    RunSourceRef(
                        provider="chembl",
                        entity="assay",
                        pipeline_name="chembl_assay",
                        input_snapshots=(
                            RunInputSnapshotRef(
                                snapshot_id="batch",
                                content_hash=sha256(payload).hexdigest(),
                                immutable_uri="bronze://chembl/assay/batch.jsonl",
                            ),
                        ),
                    ),
                ),
                overrides=RunManifestOverrides(
                    pipeline_name="chembl_assay",
                    provider="chembl",
                    entity="assay",
                    effective_config_hash=stable_json_hash(config),
                    effective_config_artifact_id=f"cfg-{rid[:8]}",
                    dependency_lock_hash="sha256:" + lock_hash,
                    launch_context={
                        "limit": 100,
                        "strict_exact_replay_supported": True,
                    },
                    contract_ref="chembl.assay",
                    dq_policy_ref="chembl_assay.gold",
                ),
            ),
            objects={
                "effective_config_hash": True,
                "dependency_lock_hash": True,
                "input_snapshot_fingerprint": True,
            },
        )

    settings = SimpleNamespace(
        data_dir=str(default_data),
        report_root=reports,
        archive_root=None,
        prometheus_url=None,
        runtime_source_id=None,
    )
    monkeypatch.setattr(assembly, "get_settings", lambda: settings)
    isolated_deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: MagicMock(),
        data_root=isolated,
    )
    foreign_deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: MagicMock(),
        data_root=foreign,
    )
    default_deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: MagicMock(),
        data_root=default_data,
    )
    isolated_deps.run_manifest_port.save(
        materialize(isolated, run_id, manifest_id, b"target-bytes")
    )
    foreign_deps.run_manifest_port.save(
        materialize(
            foreign,
            foreign_run,
            "ffffffff-ffff-4fff-8fff-ffffffffffff",
            b"foreign-bytes",
        )
    )
    draft = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_assay",
            "run_id": run_id,
            "status": "success",
            "run_type": "incremental",
            "started_at": "2026-11-02T14:44:03+00:00",
            "completed_at": "2026-11-02T14:45:03+00:00",
        },
        metrics={},
    )
    value = replace(
        draft,
        observations={
            name: {"verdict": "OK", "reason": "checked", "facts": {}}
            for name in DOMAINS[1:]
        },
    )
    written = write_pipeline_run_report(
        value, root=reports, store=FileRunReportStoreAdapter()
    )
    before = written.json_path.read_bytes()

    lost = load_selected_run_status(
        pipeline="chembl_assay",
        run_id=run_id,
        root=reports,
        manifest_port=default_deps.run_manifest_port,
    )
    assert lost["execution_state"] == "SUCCESS"
    assert lost["evidence_completeness"] == "COMPLETE"
    assert lost["replay_readiness_now"] == "INSUFFICIENT"
    assert {c["code"] for c in lost["replay_checks"]} >= {"manifest_not_recorded"}
    assert _replay_status(lost) == "INCOMPLETE"

    recovered = load_selected_run_status(
        pipeline="chembl_assay",
        run_id=run_id,
        root=reports,
        manifest_port=isolated_deps.run_manifest_port,
    )
    assert recovered["replay_readiness_now"] == "READY"
    assert _replay_status(recovered) == "OK"

    foreign_view = load_selected_run_status(
        pipeline="chembl_assay",
        run_id=run_id,
        root=reports,
        manifest_port=foreign_deps.run_manifest_port,
    )
    assert foreign_view["replay_readiness_now"] == "INSUFFICIENT"
    assert written.json_path.read_bytes() == before
    assert lost["revision"] == recovered["revision"] == foreign_view["revision"]


class _RecordingResolver:
    def __init__(self, result: EvidenceLocationResolveResult) -> None:
        self.result = result
        self.kwargs: dict[str, object] = {}

    def resolve(self, **kwargs: object) -> EvidenceLocationResolveResult:
        self.kwargs = kwargs
        return self.result


def test_location_missing_without_context_does_not_read_legacy_root(tmp_path):
    persist(tmp_path)
    resolver = _RecordingResolver(
        EvidenceLocationResolveResult(
            lookup=EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_MISSING
            )
        )
    )
    result = load_selected_run_status(
        pipeline="chembl_activity",
        run_id="run-a",
        root=tmp_path,
        resolver=resolver,
        expected_runtime_source_id="src-1",
    )
    assert result["verdict"] == "ERROR"
    assert result["reason"] == "location_missing"
    assert resolver.kwargs["expected_runtime_source_id"] == "src-1"


def test_open_legacy_context_still_reads_saved_report(tmp_path):
    persist(tmp_path)
    resolver = _RecordingResolver(
        EvidenceLocationResolveResult(
            lookup=EvidenceLocationLookupResult(
                code=EvidenceLocationLookupCode.LOCATION_MISSING
            ),
            context=SimpleNamespace(data_root=tmp_path),
            data_root=tmp_path,
        )
    )
    result = load_selected_run_status(
        pipeline="chembl_activity",
        run_id="run-a",
        root=tmp_path,
        resolver=resolver,
    )
    assert result["verdict"] == "OK"
    assert result["evidence_availability"] == "AVAILABLE"


def test_bound_resolver_supplies_omitted_runtime_source_id() -> None:
    locations = MagicMock()
    locations.lookup.return_value = EvidenceLocationLookupResult(
        code=EvidenceLocationLookupCode.IDENTITY_CONFLICT
    )
    resolver = EvidenceLocationResolver(
        locations=locations,
        aliases=MagicMock(),
        opener=MagicMock(),
        legacy_root_policy=EvidenceLocationLegacyRootPolicy.REQUIRE_EXPLICIT_RECORD,
    )
    bound = bind_runtime_source_id(resolver, "src-1")
    assert bound is not None
    bound.resolve(kind="pipeline", owner="chembl_activity", run_id="run-a")
    assert locations.lookup.call_args.kwargs["expected_runtime_source_id"] == "src-1"
