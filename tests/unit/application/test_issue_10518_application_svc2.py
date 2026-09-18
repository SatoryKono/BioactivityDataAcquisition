"""Behavior-focused unit tests closing #10518 application-layer residuals (svc2)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 1. export_lineage/debug_export_service_recording_mixin
# ---------------------------------------------------------------------------

from bioetl.application.services.export_lineage.debug_export_service_recording_mixin import (
    DebugExportServiceRecordingMixin,
)


class _RecordingHost(DebugExportServiceRecordingMixin):
    def __init__(self, enabled: bool) -> None:
        self._is_enabled = enabled
        self._collector = MagicMock()
        self._created_at_factory = lambda: _NOW

    @property
    def enabled(self) -> bool:
        return self._is_enabled


def _bronze(i: int = 0) -> dict:
    return {"id": i, "payload": "x"}


def test_debug_mixin_disabled_bronze_batch_noop() -> None:
    host = _RecordingHost(False)
    host.record_bronze_batch(records=[_bronze()], batch_id="b", start_index=0)
    host._collector.record_bronze_batch.assert_not_called()


def test_debug_mixin_disabled_transform_success_noop() -> None:
    host = _RecordingHost(False)
    host.record_transform_success(raw_record=_bronze(), record_index=0, silver_record=_bronze())
    host._collector.record_transform_success.assert_not_called()


def test_debug_mixin_disabled_transform_failure_noop() -> None:
    host = _RecordingHost(False)
    host.record_transform_failure(raw_record=_bronze(), record_index=1)
    host._collector.record_transform_failure.assert_not_called()


def test_debug_mixin_enabled_transform_failure_delegates() -> None:
    host = _RecordingHost(True)
    host.record_transform_failure(
        raw_record=_bronze(), record_index=2, error_type=None, details="bad", policy="p"
    )
    kwargs = host._collector.record_transform_failure.call_args.kwargs
    assert kwargs["record_index"] == 2
    assert kwargs["details"] == "bad"
    assert kwargs["created_at"] is _NOW


def test_debug_mixin_disabled_filtered_out_noop() -> None:
    host = _RecordingHost(False)
    host.record_filtered_out(
        raw_record=_bronze(), record_index=0, reason="r", details=None, policy=None
    )
    host._collector.record_transform_failure.assert_not_called()


def test_debug_mixin_enabled_filtered_out_with_details() -> None:
    host = _RecordingHost(True)
    host.record_filtered_out(
        raw_record=_bronze(), record_index=0, reason="skip", details={"k": "v"}, policy="p"
    )
    kwargs = host._collector.record_transform_failure.call_args.kwargs
    assert kwargs["details"].startswith("skip: ")


def test_debug_mixin_disabled_data_quality_failure_noop() -> None:
    host = _RecordingHost(False)
    host.record_data_quality_failure(
        raw_record=_bronze(), record_index=0, error_type=None,
        error_details="e", policy="p",
    )
    host._collector.record_transform_failure.assert_not_called()


def test_debug_mixin_disabled_gold_filter_noop() -> None:
    host = _RecordingHost(False)
    host.record_gold_filter(records=[], reason_code="rc")
    host._collector.record_gold_filter.assert_not_called()


def test_debug_mixin_disabled_gold_validation_failure_noop() -> None:
    host = _RecordingHost(False)
    host.record_gold_validation_failure(records=[], errors={})
    host._collector.record_gold_validation_failure.assert_not_called()


def test_debug_mixin_disabled_lineage_noop() -> None:
    host = _RecordingHost(False)
    host.record_lineage(fragment_id="f", edge_type="e", node_id="n", raw_record=_bronze())
    host._collector.record_lineage.assert_not_called()


def test_debug_mixin_enabled_bronze_batch_delegates() -> None:
    host = _RecordingHost(True)
    host.record_bronze_batch(records=[_bronze()], batch_id="b", start_index=3)
    kwargs = host._collector.record_bronze_batch.call_args.kwargs
    assert kwargs["start_index"] == 3
    assert kwargs["created_at"] is _NOW


# ---------------------------------------------------------------------------
# 2. run_reports/control_plane_snapshot
# ---------------------------------------------------------------------------

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.application.services.run_reports import observations as _obs
from bioetl.application.services.run_reports.control_plane_snapshot import (
    CaptureControlPlaneSnapshot,
    capture_run_completion,
)
from bioetl.domain.control_plane import RunManifest


def _manifest(pipeline: str = "pipe") -> RunManifest:
    return RunManifest(
        manifest_id="m-1",
        execution_fingerprint="fp",
        pipeline_name=pipeline,
        provider="prov",
        entity="ent",
    )


def test_snapshot_manifest_missing_records_incomplete() -> None:
    manifests = MagicMock()
    manifests.get_by_run_id.return_value = None
    evidence = MagicMock()
    capture = CaptureControlPlaneSnapshot(manifests=manifests, evidence=evidence)
    token = _obs.bind_run_observations()
    try:
        capture("pipe", str(UUID(int=1001)), _NOW)
        entry = _obs.run_observations()["Control Plane"]
    finally:
        _obs.reset_run_observations(token)
    assert entry["verdict"] == "INCOMPLETE"
    assert entry["reason"] == "manifest_not_found"
    evidence.trust_summary.assert_not_called()


def test_snapshot_pipeline_mismatch_records_incomplete() -> None:
    manifests = MagicMock()
    manifests.get_by_run_id.return_value = _manifest("other")
    evidence = MagicMock()
    CaptureControlPlaneSnapshot(manifests=manifests, evidence=evidence)(
        "pipe", str(UUID(int=1002)), _NOW
    )
    evidence.trust_summary.assert_not_called()


def test_snapshot_success_maps_warning_to_warn() -> None:
    run_id = str(UUID(int=1003))
    manifests = MagicMock()
    manifests.get_by_run_id.return_value = _manifest("pipe")
    evidence = MagicMock()
    evidence.trust_summary.return_value = {"trust_status": "WARNING", "checks": 1}
    token = _obs.bind_run_observations()
    try:
        CaptureControlPlaneSnapshot(manifests=manifests, evidence=evidence)(
            "pipe", run_id, _NOW
        )
        entry = _obs.run_observations()["Control Plane"]
    finally:
        _obs.reset_run_observations(token)
    assert entry["verdict"] == "WARN"
    assert entry["reason"] == "run_completion_trust_assessment"


def test_capture_run_completion_noops() -> None:
    result = SimpleNamespace(pipeline_name="p", run_id="r", completed_at=_NOW)
    capture_run_completion(None, result, None)
    capture_run_completion(MagicMock(), result, RunOptions(dry_run=True))
    result_pending = SimpleNamespace(pipeline_name="p", run_id="r", completed_at=None)
    capture = MagicMock()
    capture_run_completion(capture, result_pending, None)
    capture.assert_not_called()


def test_capture_run_completion_failure_records_incomplete() -> None:
    def _boom(pipeline: str, run_id: str, completed_at: datetime) -> None:
        raise OSError("store down")

    result = SimpleNamespace(pipeline_name="p", run_id="r", completed_at=_NOW)
    token = _obs.bind_run_observations()
    try:
        capture_run_completion(_boom, result, None)
        entry = _obs.run_observations()["Control Plane"]
    finally:
        _obs.reset_run_observations(token)
    assert entry["reason"] == "completion_assessment_failed"


def test_capture_run_completion_success_delegates() -> None:
    capture = MagicMock()
    result = SimpleNamespace(pipeline_name="p", run_id="r", completed_at=_NOW)
    capture_run_completion(capture, result, RunOptions())
    capture.assert_called_once_with("p", "r", _NOW)


# ---------------------------------------------------------------------------
# 3. workflow/_observability_workflow_evidence_support
# ---------------------------------------------------------------------------

from bioetl.application.services.checkpoint.checkpoint_models import CheckpointInfo
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
)
from bioetl.application.services.workflow._observability_workflow_evidence_support import (
    classify_checkpoint_status,
    classify_evidence_status,
    collect_traceability_degradation,
    has_composite_correlation_policy_gap,
    has_correlation_anchor_gaps,
    requires_critical_dossier_evidence,
    resolve_required_evidence_profile,
)


def _inspect_result(diagnostics: dict) -> RunManifestInspectionResult:
    return RunManifestInspectionResult(manifest=_manifest(), diagnostics=diagnostics)


def test_requires_critical_none_is_false() -> None:
    assert requires_critical_dossier_evidence(None) is False


def test_requires_critical_flag() -> None:
    assert requires_critical_dossier_evidence(_inspect_result({"critical_pipeline": True})) is True


def test_requires_critical_via_profile() -> None:
    result = _inspect_result({"required_persistence_profile": "forensic_grade"})
    assert requires_critical_dossier_evidence(result) is True
    assert requires_critical_dossier_evidence(_inspect_result({})) is False


def test_resolve_profile_from_persistence_dict() -> None:
    assert (
        resolve_required_evidence_profile(
            {"persistence_profile": {"required_profile": "forensic_grade"}}
        )
        == "forensic_grade"
    )
    assert (
        resolve_required_evidence_profile(
            {"persistence_profile": {"required_profile": ""}}
        )
        is None
    )
    assert (
        resolve_required_evidence_profile({"required_persistence_profile": "x"}) == "x"
    )
    assert resolve_required_evidence_profile({}) is None


def test_classify_checkpoint_mismatched() -> None:
    info = CheckpointInfo(
        pipeline_name="p", run_id="r", metadata={"status": "mismatched_run_context"}
    )
    assert classify_checkpoint_status(info) == ["checkpoint_mismatched_run"]
    assert classify_checkpoint_status(None) == ["checkpoint"]
    assert classify_checkpoint_status(
        CheckpointInfo(pipeline_name="p", run_id="r", metadata={})
    ) == []


def test_traceability_gaps() -> None:
    degraded = collect_traceability_degradation(
        {
            "persistence_profile": {
                "attained_profile": "partial",
                "required_profile_missing_requirements": ["a"],
                "replay_ready_missing_requirements": [],
                "forensic_grade_missing_requirements": "nope",
            },
            "correlation_anchor_gaps": {"anchor": 2},
            "composite_projection": {"composite_run_id_consistent": False},
        }
    )
    assert "correlation_anchor_gaps" in degraded
    assert "composite_correlation_policy_gap" in degraded
    assert "trace_identifiers_unavailable" in degraded
    assert "persistence_profile:partial" in degraded
    assert has_correlation_anchor_gaps({"correlation_anchor_gaps": {"a": 0}}) is False


def test_composite_policy_gap_branches() -> None:
    assert has_composite_correlation_policy_gap({}) is False
    assert (
        has_composite_correlation_policy_gap(
            {"composite_projection": {"composite_run_id_consistent": False}}
        )
        is True
    )
    assert (
        has_composite_correlation_policy_gap(
            {
                "composite_projection": {
                    "composite_run_id_consistent": True,
                    "correlation_policy": {"status": "violated"},
                }
            }
        )
        is True
    )
    assert (
        has_composite_correlation_policy_gap(
            {
                "composite_projection": {
                    "correlation_policy": {"status": "satisfied"},
                }
            }
        )
        is False
    )


def test_classify_evidence_status_all_missing() -> None:
    missing, degraded = classify_evidence_status(
        run_manifest=None,
        checkpoint=None,
        lineage=None,
        quarantine_summary=None,
        traceability={},
    )
    assert missing == ("run_manifest",)
    assert "checkpoint" in degraded
    assert "lineage" in degraded
    assert "quarantine_summary" in degraded


# ---------------------------------------------------------------------------
# 4. control_plane/manifest/diagnostics/source_refs
# ---------------------------------------------------------------------------

from bioetl.domain.control_plane import RunInputSnapshotRef, RunSourceRef
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)
from bioetl.application.services.control_plane.manifest.diagnostics.source_refs import (
    _attach_rich_composite_replay_support,
    _build_effective_source_refs,
)


def _src_manifest() -> RunManifest:
    return RunManifest(
        manifest_id="m",
        execution_fingerprint="fp",
        pipeline_name="pl",
        provider="p",
        entity="e",
        source_refs=(RunSourceRef(provider="p", entity="e", pipeline_name="pl", query="q"),),
    )


def test_effective_refs_empty_snapshots_returns_declared() -> None:
    manifest = _src_manifest()
    assert _build_effective_source_refs(manifest=manifest, input_snapshots=[]) == (
        manifest.source_refs
    )


def test_effective_refs_skips_non_dict_snapshots() -> None:
    manifest = _src_manifest()
    out = _build_effective_source_refs(manifest=manifest, input_snapshots=["nope", 42, None])
    assert out == manifest.source_refs


def test_effective_refs_merges_matching_snapshot() -> None:
    manifest = _src_manifest()
    out = _build_effective_source_refs(
        manifest=manifest,
        input_snapshots=[
            {
                "provider": "p",
                "entity": "e",
                "pipeline_name": "pl",
                "query": "q",
                "snapshot_id": "s1",
                "content_hash": "h1",
                "captured_at": "not-a-date",
            }
        ],
    )
    assert len(out) == 1
    assert len(out[0].input_snapshots) == 1
    assert isinstance(out[0].input_snapshots[0], RunInputSnapshotRef)


def test_effective_refs_queryless_manifest_matches_any_query() -> None:
    manifest = RunManifest(
        manifest_id="m",
        execution_fingerprint="fp",
        pipeline_name="pl",
        provider="p",
        entity="e",
        source_refs=(RunSourceRef(provider="p", entity="e", pipeline_name="pl"),),
    )
    out = _build_effective_source_refs(
        manifest=manifest,
        input_snapshots=[
            {"provider": "p", "entity": "e", "pipeline_name": "pl",
             "query": "q1", "snapshot_id": "s", "content_hash": "h"},
            {"provider": "other", "entity": "e", "pipeline_name": "pl",
             "snapshot_id": "s2", "content_hash": "h2"},
        ],
    )
    assert len(out) == 2
    assert len(out[0].input_snapshots) == 1


def _ledger_entry(event_type: str):
    from bioetl.domain.control_plane import RunLedgerEntry
    from bioetl.domain.types import RunID

    return RunLedgerEntry(
        entry_id=f"e-{event_type}",
        manifest_id="m",
        run_id=RunID(UUID(int=1004)),
        event_type=event_type,
        occurred_at=_NOW,
    )


def test_rich_composite_replay_supported_when_all_events() -> None:
    summary: dict[str, object] = {"a": 1}
    out = _attach_rich_composite_replay_support(
        summary,
        (
            _ledger_entry(COMPOSITE_DEPENDENCY_COMPLETED_EVENT),
            _ledger_entry(COMPOSITE_ENRICHER_COMPLETED_EVENT),
            _ledger_entry(COMPOSITE_MERGE_COMPLETED_EVENT),
        ),
    )
    assert out["composite_resume_rich_replay_supported"] is True


def test_rich_composite_replay_unchanged_when_partial() -> None:
    summary: dict[str, object] = {"a": 1}
    out = _attach_rich_composite_replay_support(
        summary, (_ledger_entry(COMPOSITE_DEPENDENCY_COMPLETED_EVENT),)
    )
    assert out is summary
    assert "composite_resume_rich_replay_supported" not in out


# ---------------------------------------------------------------------------
# 5. control_plane/manifest/inspection_service
# ---------------------------------------------------------------------------

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionCorruptionError,
    RunManifestInspectionService,
)


def _inspection_svc(**kwargs) -> RunManifestInspectionService:
    return RunManifestInspectionService(manifest_port=MagicMock(), **kwargs)


def test_inspection_historical_claim_loader_not_dict() -> None:
    svc = _inspection_svc(
        historical_replay_universe_report_loader=MagicMock(
            load_latest_report=MagicMock(return_value=["not-a-dict"])
        )
    )
    diagnostics: dict[str, object] = {}
    svc._attach_historical_replay_universe_claim(diagnostics)
    assert diagnostics == {}


def test_inspection_historical_claim_missing_claim_dicts() -> None:
    svc = _inspection_svc(
        historical_replay_universe_report_loader=MagicMock(
            load_latest_report=MagicMock(return_value={"universal_claim": "x"})
        )
    )
    diagnostics: dict[str, object] = {}
    svc._attach_historical_replay_universe_claim(diagnostics)
    assert "historical_replay_universe_claim" not in diagnostics


def test_inspection_historical_claim_attaches() -> None:
    svc = _inspection_svc(
        historical_replay_universe_report_loader=MagicMock(
            load_latest_report=MagicMock(
                return_value={
                    "universal_claim": {"u": 1},
                    "durable_evidence_coverage_claim": {"claimed": True},
                    "_artifact_path": "/artifacts/report.json",
                    "governed_full_corpus_gate": {"g": 1},
                }
            )
        )
    )
    diagnostics: dict[str, object] = {}
    svc._attach_historical_replay_universe_claim(diagnostics)
    assert diagnostics["historical_replay_universe_claim"] == {"u": 1}
    assert diagnostics["historical_replay_universe_claim_source"] == "/artifacts/report.json"
    assert diagnostics["historical_replay_universe_durable_evidence_claimed"] is True


def test_inspection_reproducibility_views_not_dict() -> None:
    svc = _inspection_svc()
    diagnostics: dict[str, object] = {"other": 1}
    svc._attach_reproducibility_claim_views(diagnostics)
    assert diagnostics == {"other": 1}


def test_inspection_reproducibility_views_attach() -> None:
    svc = _inspection_svc()
    diagnostics: dict[str, object] = {
        "reproducibility_audit_score": {
            "historical_replay_universe_exact_replay_claim": {"c": 1},
            "executable_run_contract_claim": {"k": 2},
        }
    }
    svc._attach_reproducibility_claim_views(diagnostics)
    assert diagnostics["historical_replay_universe_exact_replay_claim"] == {"c": 1}
    assert diagnostics["executable_run_contract_claim"] == {"k": 2}


def test_resolve_artifacts_trace_not_dict() -> None:
    svc = _inspection_svc()
    with patch.object(
        svc, "show",
        return_value=SimpleNamespace(diagnostics={"produced_artifact_trace": [1, 2]}),
    ):
        assert svc.resolve_produced_artifacts("m") == ()


def test_resolve_artifacts_list_not_list() -> None:
    svc = _inspection_svc()
    with patch.object(
        svc, "show",
        return_value=SimpleNamespace(
            diagnostics={"produced_artifact_trace": {"artifacts": "nope"}}
        ),
    ):
        assert svc.resolve_produced_artifacts("m") == ()


def test_resolve_artifacts_filters_non_dicts() -> None:
    svc = _inspection_svc()
    with patch.object(
        svc, "show",
        return_value=SimpleNamespace(
            diagnostics={"produced_artifact_trace": {"artifacts": [{"a": 1}, "x", 3]}}
        ),
    ):
        assert svc.resolve_produced_artifacts("m") == ({"a": 1},)


def test_inspection_no_loader_and_no_governed_gate() -> None:
    svc = _inspection_svc(historical_replay_universe_report_loader=None)
    diagnostics: dict[str, object] = {}
    svc._attach_historical_replay_universe_claim(diagnostics)
    assert diagnostics == {}
    svc2 = _inspection_svc(
        historical_replay_universe_report_loader=MagicMock(
            load_latest_report=MagicMock(
                return_value={
                    "universal_claim": {"u": 1},
                    "durable_evidence_coverage_claim": {"claimed": False},
                    "report_id": "r-1",
                }
            )
        )
    )
    diagnostics2: dict[str, object] = {}
    svc2._attach_historical_replay_universe_claim(diagnostics2)
    assert diagnostics2["historical_replay_universe_claim_source"] == "r-1"
    assert "historical_replay_universe_governed_full_corpus_gate" not in diagnostics2


def test_resolve_manifest_direct_hit() -> None:
    manifest = _manifest()
    port = MagicMock()
    port.get.return_value = manifest
    svc = RunManifestInspectionService(manifest_port=port)
    assert svc._resolve_manifest("m-1") is manifest
    port.get_by_run_id.assert_not_called()


def test_resolve_manifest_get_raises_corruption() -> None:
    port = MagicMock()
    port.get.side_effect = ValueError("bad row")
    svc = RunManifestInspectionService(manifest_port=port)
    with pytest.raises(RunManifestInspectionCorruptionError):
        svc._resolve_manifest("m-1")


def test_resolve_manifest_by_run_id_lookup_failure() -> None:
    port = MagicMock()
    port.get.return_value = None
    port.get_by_run_id.side_effect = ValueError("bad ledger row")
    svc = RunManifestInspectionService(manifest_port=port)
    with pytest.raises(RunManifestInspectionCorruptionError):
        svc._resolve_manifest(str(UUID(int=1005)))


def test_resolve_manifest_by_run_id_success() -> None:
    manifest = _manifest()
    port = MagicMock()
    port.get.return_value = None
    port.get_by_run_id.return_value = manifest
    svc = RunManifestInspectionService(manifest_port=port)
    assert svc._resolve_manifest(str(UUID(int=1006))) is manifest


def test_resolve_manifest_not_found() -> None:
    port = MagicMock()
    port.get.return_value = None
    port.get_by_run_id.return_value = None
    svc = RunManifestInspectionService(manifest_port=port)
    with pytest.raises(ValueError, match="not found"):
        svc._resolve_manifest(str(UUID(int=1007)))
    with pytest.raises(ValueError, match="not found"):
        svc._resolve_manifest("not-a-uuid-at-all")


# ---------------------------------------------------------------------------
# 6. control_plane/replay/_historical_certification_support
# ---------------------------------------------------------------------------

from bioetl.application.services.control_plane.replay._historical_certification_support import (
    HistoricalReplayCertificationValidator,
)
from bioetl.domain.types import RunID


def _validator(**kwargs) -> HistoricalReplayCertificationValidator:
    kwargs.setdefault("manifest_port", MagicMock())
    kwargs.setdefault("ledger_port", MagicMock())
    kwargs.setdefault("summary_builder", MagicMock())
    return HistoricalReplayCertificationValidator(**kwargs)


def _cert(**kwargs) -> SimpleNamespace:
    base = {
        "provider": "p", "entity": "e", "pipeline_name": "pl",
        "query": None, "upstream_run_id": None, "upstream_manifest_id": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _cert_manifest() -> RunManifest:
    return RunManifest(
        manifest_id="m",
        execution_fingerprint="fp",
        pipeline_name="pl",
        provider="p",
        entity="e",
        source_refs=(RunSourceRef(provider="p", entity="e", pipeline_name="pl", query="q1"),),
    )


def test_cert_load_manifest_requires_exactly_one() -> None:
    validator = _validator()
    with pytest.raises(ValueError, match="exactly one"):
        validator.load_manifest(manifest_id=None, run_id=None)
    with pytest.raises(ValueError, match="exactly one"):
        validator.load_manifest(manifest_id="m", run_id=RunID(UUID(int=1008)))


def test_cert_load_manifest_not_found() -> None:
    port = MagicMock()
    port.get.return_value = None
    with pytest.raises(ValueError, match="not found"):
        _validator(manifest_port=port).load_manifest(manifest_id="m", run_id=None)


def test_cert_load_manifest_ok_both_paths() -> None:
    manifest = _manifest()
    port = MagicMock()
    port.get.return_value = manifest
    port.get_by_run_id.return_value = manifest
    validator = _validator(manifest_port=port)
    assert validator.load_manifest(manifest_id="m", run_id=None) is manifest
    assert validator.load_manifest(manifest_id=None, run_id=RunID(UUID(int=1009))) is manifest


def test_cert_validate_source_context() -> None:
    validator = _validator()
    composite_ctx = RunManifest(
        manifest_id="m", execution_fingerprint="f", pipeline_name="p",
        provider="p", entity="e", launch_context={"execution_context": "composite"},
    )
    with pytest.raises(ValueError, match="source context"):
        validator.validate_source_context(composite_ctx)
    composite_provider = RunManifest(
        manifest_id="m", execution_fingerprint="f", pipeline_name="p",
        provider="composite", entity="e",
    )
    with pytest.raises(ValueError, match="source context"):
        validator.validate_source_context(composite_provider)
    validator.validate_source_context(_manifest())


def test_cert_validate_composite_context() -> None:
    validator = _validator()
    with pytest.raises(ValueError, match="composite context"):
        validator.validate_composite_context(_manifest())
    composite_ctx = RunManifest(
        manifest_id="m", execution_fingerprint="f", pipeline_name="p",
        provider="p", entity="e", launch_context={"execution_context": "composite"},
    )
    validator.validate_composite_context(composite_ctx)


def test_cert_coverage_requires_snapshots() -> None:
    with pytest.raises(ValueError, match="At least one"):
        _validator().validate_certification_coverage(manifest=_manifest(), certifications=())


def test_cert_coverage_missing_sources() -> None:
    with pytest.raises(ValueError, match="missing sources"):
        _validator().validate_certification_coverage(
            manifest=_cert_manifest(), certifications=(_cert(query="other-query"),)
        )


def test_cert_coverage_satisfied() -> None:
    _validator().validate_certification_coverage(
        manifest=_cert_manifest(), certifications=(_cert(query="q1"),)
    )


def test_cert_resolve_query_direct() -> None:
    out = _validator().resolve_certification_query(
        manifest=_cert_manifest(), certification=_cert(query="  explicit  ")
    )
    assert out == "explicit"


def test_cert_resolve_query_single_match() -> None:
    out = _validator().resolve_certification_query(
        manifest=_cert_manifest(), certification=_cert(query=None)
    )
    assert out == "q1"


def test_cert_resolve_query_ambiguous() -> None:
    manifest = RunManifest(
        manifest_id="m", execution_fingerprint="fp", pipeline_name="pl",
        provider="p", entity="e",
        source_refs=(
            RunSourceRef(provider="p", entity="e", pipeline_name="pl", query="qa"),
            RunSourceRef(provider="p", entity="e", pipeline_name="pl", query="qb"),
        ),
    )
    with pytest.raises(ValueError, match="ambiguous"):
        _validator().resolve_certification_query(
            manifest=manifest, certification=_cert(query=None)
        )


def test_cert_resolve_query_none() -> None:
    manifest = RunManifest(
        manifest_id="m", execution_fingerprint="fp", pipeline_name="pl",
        provider="p", entity="e",
    )
    assert (
        _validator().resolve_certification_query(
            manifest=manifest, certification=_cert(query=None)
        )
        is None
    )


# ---------------------------------------------------------------------------
# 7. execution/_pipeline_runner_support
# ---------------------------------------------------------------------------

from bioetl.application.services.execution import _pipeline_runner_support as _prs
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)


def _run_result(**kwargs) -> RunResult:
    base = {
        "status": PipelineRunResult.SUCCESS,
        "pipeline_name": "prov_ent",
        "run_id": str(UUID(int=1010)),
        "run_type": "incremental",
        "started_at": _NOW,
        "completed_at": _NOW,
    }
    base.update(kwargs)
    return RunResult(**base)


def test_result_duration_exception_returns_none() -> None:
    class _Boom:
        @property
        def duration_seconds(self) -> float:
            raise RuntimeError("boom")

    assert _prs._result_duration_seconds(_Boom()) is None  # type: ignore[arg-type]
    assert _prs._result_duration_seconds(_run_result()) == 0.0


def test_require_run_result_rejects_other_types() -> None:
    with pytest.raises(TypeError):
        _prs._require_run_result(object())
    result = _run_result()
    assert _prs._require_run_result(result) is result


def test_finalize_report_failure_sets_error() -> None:
    with patch.object(
        _prs, "build_pipeline_run_report", side_effect=RuntimeError("writer down")
    ):
        out = _prs.finalize_pipeline_run_report(result=_run_result(), store=MagicMock())
    assert out.run_report_error == "RuntimeError: writer down"


def test_package_version_none_on_broken_dunder() -> None:
    class _BadStr:
        def __str__(self) -> str:
            raise RuntimeError("boom")

    import bioetl

    with patch.object(bioetl, "__version__", _BadStr(), create=True):
        assert _prs._package_version() is None


def test_build_run_result_write_report_branches() -> None:
    outcome = SimpleNamespace(
        status="success", metrics={}, completed_at=_NOW,
        error_message=None, error_type=None,
    )
    runner = SimpleNamespace(manifest_id="m", debug_export_uri=None, debug_export_hash=None)
    with patch.object(
        _prs, "finalize_pipeline_run_report",
        side_effect=lambda *, result, options=None, **_: result,
    ) as finalize:
        out = _prs.build_pipeline_run_result(
            outcome=outcome, runner=runner, pipeline_name="p",
            run_id=RunID(UUID(int=1011)), run_type="incremental",
            started_at=_NOW, write_report=True, store=MagicMock(),
        )
        finalize.assert_called_once()
    with patch.object(_prs, "finalize_pipeline_run_report") as finalize2:
        out2 = _prs.build_pipeline_run_result(
            outcome=outcome, runner=runner, pipeline_name="p",
            run_id=RunID(UUID(int=1012)), run_type="incremental",
            started_at=_NOW, write_report=False, store=MagicMock(),
        )
        finalize2.assert_not_called()
    assert out.manifest_id == "m"
    assert out2.status == PipelineRunResult.SUCCESS


# ---------------------------------------------------------------------------
# 8. ops/config_service
# ---------------------------------------------------------------------------

from bioetl.application.services.ops.config_service import ConfigService


def _config_svc(**kwargs) -> ConfigService:
    kwargs.setdefault("logger", MagicMock())
    kwargs.setdefault("_settings_loader", MagicMock())
    kwargs.setdefault("_pipeline_config_loader", MagicMock())
    kwargs.setdefault("_domain_config_mapper", MagicMock())
    kwargs.setdefault("_registry_accessor", MagicMock())
    return ConfigService(**kwargs)


def test_config_dq_missing_raises() -> None:
    svc = _config_svc(_dq_service=None)
    with pytest.raises(ValueError, match="not configured"):
        svc.get_dq_config("pipe")


def test_config_yaml_mapping_and_model_dump() -> None:
    svc = _config_svc(_pipeline_config_loader=MagicMock(return_value={"a": 1}))
    assert svc.get_pipeline_yaml_config("pipe") == {"a": 1}
    loader = MagicMock(return_value=SimpleNamespace(model_dump=lambda: {"b": 2}))
    assert _config_svc(_pipeline_config_loader=loader).get_pipeline_yaml_config("p") == {"b": 2}


def test_config_yaml_bad_type_raises() -> None:
    svc = _config_svc(_pipeline_config_loader=MagicMock(return_value=42))
    with pytest.raises(TypeError):
        svc.get_pipeline_yaml_config("pipe")


def test_config_dq_delegation() -> None:
    dq = MagicMock()
    dq.get_dq_config.return_value = {"dq": 1}
    dq.validate_dq_config.return_value = True
    dq.get_effective_config_artifact.return_value = {"eff": 1}
    dq.check_config_compatibility.return_value = False
    svc = _config_svc(_dq_service=dq)
    assert svc.get_dq_config("p") == {"dq": 1}
    assert svc.validate_dq_config("p", {"x": 1}) is True
    assert svc.get_effective_config_artifact("p", None) == {"eff": 1}
    assert svc.check_config_compatibility({"a": 1}, {"b": 2}) is False


# ---------------------------------------------------------------------------
# 9. quality/_quarantine_service_async_mixin
# ---------------------------------------------------------------------------

from bioetl.application.services.quality._quarantine_service_async_mixin import (
    QuarantineServiceAsyncMixin,
)


class _QuarantineHost(QuarantineServiceAsyncMixin):
    TRACER_NAME = "test-quarantine"

    def __init__(self, port, tracer=None) -> None:
        self.logger = MagicMock()
        self.quarantine_port = port
        self.tracer = tracer
        self.metric_calls: list[tuple[str, str]] = []

    def _record_operator_metrics(self, *, operation, status, duration_seconds) -> None:
        self.metric_calls.append((operation, status))

    def _trace_attributes(self, *, operation, pipeline=None, **extra):
        return {"operation": operation}

    def _set_trace_result(self, span, *, success, **extra) -> None:
        return None


def _quarantine_port(rows=None, error=None):
    async def inspect(*, pipeline, limit, error_code):
        if error is not None:
            raise error
        return rows or []

    async def get_stats(pipeline, error_code):
        if error is not None:
            raise error
        return {"total": 1}

    return SimpleNamespace(inspect=inspect, get_stats=get_stats)


async def test_quarantine_inspect_no_tracer_success() -> None:
    host = _QuarantineHost(
        _quarantine_port(rows=[{
            "error_code": "E1", "payload": {"a": 1}, "bronze_batch_id": "b",
            "ingestion_ts": "t", "metadata": {"m": 1},
        }])
    )
    records = await host.inspect("pipe")
    assert len(records) == 1
    assert records[0].error_code == "E1"
    assert records[0].pipeline == "pipe"
    assert ("inspect", "success") in host.metric_calls


async def test_quarantine_inspect_failure_metrics() -> None:
    host = _QuarantineHost(_quarantine_port(error=OSError("down")))
    with pytest.raises(OSError):
        await host.inspect("pipe")
    assert ("inspect", "failed") in host.metric_calls


async def test_quarantine_stats_no_tracer_success() -> None:
    host = _QuarantineHost(_quarantine_port())
    assert await host.get_stats("pipe") == {"total": 1}
    assert ("stats", "success") in host.metric_calls


async def test_quarantine_stats_failure_metrics() -> None:
    host = _QuarantineHost(_quarantine_port(error=RuntimeError("down")))
    with pytest.raises(RuntimeError):
        await host.get_stats("pipe", error_code="E1")
    assert ("stats", "failed") in host.metric_calls


# ---------------------------------------------------------------------------
# 10. workflow/control_plane/_execution_resume_support
# ---------------------------------------------------------------------------

from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState
from bioetl.application.services.workflow.control_plane._execution_resume_support import (
    coerce_resume_run_id,
    load_resume_manifest,
    load_resume_state,
    normalize_resume_state,
    resolve_completed_transform_fingerprints,
    resolve_skipped_step_ids,
    validate_resume_state,
)


def _wf_state(**kwargs) -> WorkflowExecutionState:
    base = {
        "workflow_run_id": RunID(UUID(int=1013)),
        "manifest_id": "wf-manifest",
        "workflow_name": "wf",
        "execution_fingerprint": "fp",
        "status": "incomplete",
        "started_at": _NOW,
        "updated_at": _NOW,
        "completed_at": None,
        "selected_step_ids": ("s1",),
        "steps": (WorkflowStepState(step_id="s1", step_kind="extract", status="success"),),
        "completed_transform_fingerprints": {"s1": "h1"},
    }
    base.update(kwargs)
    return WorkflowExecutionState(**base)


def test_load_resume_state_run_id_missing() -> None:
    port = MagicMock()
    port.get_by_run_id.return_value = None
    with pytest.raises(RuntimeError, match="no persisted execution state"):
        load_resume_state(
            workflow_state_port=port, workflow_name="wf",
            resume_manifest_id=None, resume_run_id=str(UUID(int=1014)),
        )


def test_load_resume_state_paths() -> None:
    state = _wf_state()
    port = MagicMock()
    port.get_by_run_id.return_value = state
    port.get_by_manifest_id.return_value = state
    port.get_latest.return_value = state
    assert load_resume_state(
        workflow_state_port=port, workflow_name="wf",
        resume_manifest_id=None, resume_run_id=str(UUID(int=1015)),
    ) is state
    assert load_resume_state(
        workflow_state_port=port, workflow_name="wf",
        resume_manifest_id="m", resume_run_id=None,
    ) is state
    assert load_resume_state(
        workflow_state_port=port, workflow_name="wf",
        resume_manifest_id=None, resume_run_id=None,
    ) is state


def test_load_resume_state_manifest_and_latest_missing() -> None:
    port = MagicMock()
    port.get_by_manifest_id.return_value = None
    port.get_latest.return_value = None
    with pytest.raises(RuntimeError, match="resume-manifest-id"):
        load_resume_state(
            workflow_state_port=port, workflow_name="wf",
            resume_manifest_id="m", resume_run_id=None,
        )
    with pytest.raises(RuntimeError, match="resume-last"):
        load_resume_state(
            workflow_state_port=port, workflow_name="wf",
            resume_manifest_id=None, resume_run_id=None,
        )


def test_coerce_resume_run_id() -> None:
    rid = UUID(int=1016)
    assert coerce_resume_run_id(RunID(rid)) == RunID(rid)
    assert coerce_resume_run_id(str(rid)) == RunID(rid)


def _valid_resume_kwargs(**overrides):
    kwargs = {
        "latest_state": _wf_state(),
        "workflow_name": "wf",
        "current_fingerprint": "fp",
        "force_steps": (),
        "repair_steps": (),
    }
    kwargs.update(overrides)
    return kwargs


def test_validate_resume_name_mismatch() -> None:
    with pytest.raises(RuntimeError, match="different workflow"):
        validate_resume_state(**_valid_resume_kwargs(workflow_name="other"))


def test_validate_resume_identity_fields() -> None:
    with pytest.raises(RuntimeError, match="identity fields"):
        validate_resume_state(**_valid_resume_kwargs(latest_state=_wf_state(manifest_id=" ")))


def test_validate_resume_step_integrity() -> None:
    bad = _wf_state(steps=(
        WorkflowStepState(step_id="s1", step_kind="k", status="success"),
        WorkflowStepState(step_id="s1", step_kind="k", status="success"),
    ))
    with pytest.raises(RuntimeError, match="step identities"):
        validate_resume_state(**_valid_resume_kwargs(latest_state=bad))


def test_validate_resume_step_references() -> None:
    bad = _wf_state(selected_step_ids=("ghost",))
    with pytest.raises(RuntimeError, match="step references"):
        validate_resume_state(**_valid_resume_kwargs(latest_state=bad))


def test_validate_resume_lifecycle_and_fingerprint() -> None:
    bad = _wf_state(status="weird")
    with pytest.raises(RuntimeError, match="lifecycle"):
        validate_resume_state(**_valid_resume_kwargs(latest_state=bad))
    with pytest.raises(RuntimeError, match="fingerprint"):
        validate_resume_state(**_valid_resume_kwargs(current_fingerprint="other"))


def test_validate_resume_completed_and_repair() -> None:
    with pytest.raises(RuntimeError, match="already completed"):
        validate_resume_state(**_valid_resume_kwargs(latest_state=_wf_state(status="success")))
    repair = _wf_state(repair_required=True, repair_hint="fix s1")
    with pytest.raises(RuntimeError, match="fix s1"):
        validate_resume_state(**_valid_resume_kwargs(latest_state=repair))
    validate_resume_state(**_valid_resume_kwargs(latest_state=repair, repair_steps=("s1",)))
    validate_resume_state(**_valid_resume_kwargs())


def test_load_resume_manifest() -> None:
    port = MagicMock()
    port.get.return_value = None
    svc = SimpleNamespace(manifest_port=port)
    with pytest.raises(RuntimeError, match="could not be loaded"):
        load_resume_manifest(manifest_service=svc, latest_state=_wf_state())
    sentinel = object()
    port2 = MagicMock()
    port2.get.return_value = sentinel
    svc2 = SimpleNamespace(manifest_port=port2)
    assert load_resume_manifest(manifest_service=svc2, latest_state=_wf_state()) is sentinel


def test_normalize_and_resolvers() -> None:
    state = _wf_state()
    assert normalize_resume_state(state, workflow_state_port=MagicMock(),
                                  now_factory=lambda: _NOW) is state
    running = _wf_state(status="running")
    port = MagicMock()
    out = normalize_resume_state(running, workflow_state_port=port,
                                 now_factory=lambda: _NOW)
    assert out.status == "incomplete"
    port.save.assert_called_once()
    assert resolve_skipped_step_ids(state=state, force_steps=("s1",), repair_steps=()) == frozenset()
    assert resolve_skipped_step_ids(state=state, force_steps=(), repair_steps=()) == frozenset({"s1"})
    assert resolve_completed_transform_fingerprints(
        state=state, force_steps=(), repair_steps=("s1",)) == {}


# ---------------------------------------------------------------------------
# 11. checkpoint/_checkpoint_service_runtime
# ---------------------------------------------------------------------------

from bioetl.application.services.checkpoint._checkpoint_service_runtime import (
    _resolve_checkpoint_owner_pipeline,
    get_checkpoint_for_manifest_id_impl,
    get_checkpoint_for_run_impl,
)


def _rt_host(port=None, info=None):
    host = SimpleNamespace(
        checkpoint_port=port or MagicMock(),
        logger=MagicMock(),
        metric_calls=[],
        _info=info or CheckpointInfo(pipeline_name="p", run_id="r", metadata={}),
    )
    host._record_operator_metrics = lambda **kw: host.metric_calls.append(kw["status"])
    host._checkpoint_info_from_data = lambda **kw: host._info
    return host


def test_resolve_owner_from_run_context() -> None:
    assert _resolve_checkpoint_owner_pipeline(
        caller_pipeline_name="owner", metadata={"run_context": {"pipeline_name": "owner"}}
    ) == "owner"
    assert _resolve_checkpoint_owner_pipeline(
        caller_pipeline_name="caller", metadata={"pipeline_name": "caller"}
    ) == "caller"
    assert _resolve_checkpoint_owner_pipeline(
        caller_pipeline_name="caller", metadata={}
    ) == "caller"
    with pytest.raises(ValueError, match="owner mismatch"):
        _resolve_checkpoint_owner_pipeline(
            caller_pipeline_name="a", metadata={"pipeline_name": "b"}
        )


async def test_get_for_run_operator_error() -> None:
    port = MagicMock()
    port.load_for_run = AsyncMock(side_effect=OSError("down"))
    host = _rt_host(port=port)
    with pytest.raises(OSError):
        await get_checkpoint_for_run_impl(
            host, pipeline_name="p", run_id=str(UUID(int=1017)), start_time=0.0
        )
    assert "failed" in host.metric_calls


async def test_get_for_run_success_and_missing() -> None:
    run_id = RunID(UUID(int=1018))
    port = MagicMock()
    port.load_for_run = AsyncMock(return_value=(run_id, {"k": 1}))
    host = _rt_host(port=port)
    assert await get_checkpoint_for_run_impl(
        host, pipeline_name="p", run_id=str(run_id), start_time=0.0
    ) is host._info
    port2 = MagicMock()
    port2.load_for_run = AsyncMock(return_value=None)
    host2 = _rt_host(port=port2)
    assert await get_checkpoint_for_run_impl(
        host2, pipeline_name="p", run_id=str(UUID(int=1019)), start_time=0.0
    ) is None
    assert "missing" in host2.metric_calls


async def test_get_for_manifest_missing_and_error() -> None:
    port = MagicMock()
    port.load_for_manifest_id = AsyncMock(return_value=None)
    host = _rt_host(port=port)
    assert await get_checkpoint_for_manifest_id_impl(
        host, pipeline_name="p", manifest_id="m", start_time=0.0
    ) is None
    assert "missing" in host.metric_calls
    port_err = MagicMock()
    port_err.load_for_manifest_id = AsyncMock(side_effect=ValueError("bad"))
    host_err = _rt_host(port=port_err)
    with pytest.raises(ValueError):
        await get_checkpoint_for_manifest_id_impl(
            host_err, pipeline_name="p", manifest_id="m", start_time=0.0
        )
    assert "failed" in host_err.metric_calls


# ---------------------------------------------------------------------------
# 12. control_plane/manifest/diagnostics/artifact_support
# ---------------------------------------------------------------------------

from bioetl.application.services.control_plane.manifest.diagnostics.artifact_support import (
    apply_artifact_publication_closure_policy,
    artifact_ref_sort_key,
    build_produced_artifact_trace,
    build_trace_artifact_ref,
    sorted_text_items,
)


def test_sorted_text_items_non_collection() -> None:
    assert sorted_text_items("nope") == []
    assert sorted_text_items(None) == []
    assert sorted_text_items(["b", "a", "b", "  "]) == ["a", "b"]


def test_trace_artifact_ref_filters_and_sorts() -> None:
    ref = {"stage": "gold", "artifact_id": "a", "unknown": 1, "record_count": None}
    assert build_trace_artifact_ref(ref) == {"stage": "gold", "artifact_id": "a"}
    assert artifact_ref_sort_key({"stage": "b"})[0] == "b"


def test_produced_trace_closure_failed() -> None:
    manifest = RunManifest(manifest_id="m", execution_fingerprint="f",
                           pipeline_name="p", provider="p", entity="e")
    trace = build_produced_artifact_trace(
        manifest=manifest, ledger_entries_present=True,
        artifact_refs=[{"stage": "gold", "publication_status": "FAILED"}],
    )
    assert trace["artifact_publication_closure"] == "failed"


def test_produced_trace_closure_partial_and_disabled() -> None:
    manifest = RunManifest(manifest_id="m", execution_fingerprint="f",
                           pipeline_name="p", provider="p", entity="e")
    partial = build_produced_artifact_trace(
        manifest=manifest, ledger_entries_present=False,
        artifact_refs=[{"stage": "gold", "artifact_id": "a"}],
    )
    assert partial["artifact_publication_closure"] == "partial"
    assert "run_ledger_history" in partial["missing_requirements"]
    disabled = build_produced_artifact_trace(
        manifest=manifest, ledger_entries_present=True, artifact_refs=[]
    )
    assert disabled["artifact_publication_closure"] == "disabled"


def test_produced_trace_closure_planned_count_partial() -> None:
    from bioetl.domain.control_plane import RunArtifactRef

    manifest = RunManifest(
        manifest_id="m", execution_fingerprint="f", pipeline_name="p",
        provider="p", entity="e",
        planned_artifacts=(
            RunArtifactRef(layer="gold", path="/a"),
            RunArtifactRef(layer="gold", path="/b"),
        ),
    )
    trace = build_produced_artifact_trace(
        manifest=manifest, ledger_entries_present=True,
        artifact_refs=[{"stage": "gold", "artifact_id": "a"}],
    )
    assert trace["artifact_publication_closure"] == "partial"


def test_produced_trace_closure_closed() -> None:
    manifest = RunManifest(manifest_id="m", execution_fingerprint="f",
                           pipeline_name="p", provider="p", entity="e")
    trace = build_produced_artifact_trace(
        manifest=manifest, ledger_entries_present=True,
        artifact_refs=[{"stage": "gold", "artifact_id": "a"}],
    )
    assert trace["artifact_publication_closure"] == "closed"
    assert trace["complete"] is True


def test_apply_closure_policy_branches() -> None:
    assert apply_artifact_publication_closure_policy(
        {"produced_artifact_trace": {"artifact_publication_closure": "partial"}}
    )["artifact_publication_closure"] == "partial"
    assert apply_artifact_publication_closure_policy(
        {"artifact_publication_closure": "closed"}
    )["artifact_publication_closure"] == "closed"
    assert apply_artifact_publication_closure_policy({})["artifact_publication_closure"] == "disabled"


# ---------------------------------------------------------------------------
# 13. checkpoint/checkpoint_service
# ---------------------------------------------------------------------------

from bioetl.application.services.checkpoint.checkpoint_service import CheckpointService


def _ckpt_svc(port=None, **kwargs) -> CheckpointService:
    kwargs.setdefault("checkpoint_port", port or MagicMock())
    kwargs.setdefault("logger", MagicMock())
    kwargs.setdefault("metrics", None)
    kwargs.setdefault("tracer", None)
    return CheckpointService(**kwargs)


def test_checkpoint_record_metrics_noop_without_sink() -> None:
    _ckpt_svc()._record_operator_metrics(
        operation="list", status="success", duration_seconds=0.1
    )


def test_checkpoint_record_metrics_with_sink() -> None:
    metrics = MagicMock()
    _ckpt_svc(metrics=metrics)._record_operator_metrics(
        operation="get", status="success", duration_seconds=0.5
    )
    metrics.increment_counter.assert_called_once()
    metrics.observe_histogram.assert_called_once()


async def test_checkpoint_list_no_tracer() -> None:
    run_id = RunID(UUID(int=1020))
    port = MagicMock()
    port.list_all = AsyncMock(return_value=["p1", "p2"])
    port.load = AsyncMock(side_effect=[None, (run_id, {"k": 1})])
    out = await _ckpt_svc(port=port).list_checkpoints()
    assert len(out) == 2
    assert out[0].run_id is None
    assert out[1].run_id == str(run_id)


async def test_checkpoint_get_no_tracer() -> None:
    run_id = RunID(UUID(int=1021))
    port = MagicMock()
    port.load = AsyncMock(return_value=(run_id, {"k": 1}))
    assert (await _ckpt_svc(port=port).get_checkpoint("p")).run_id == str(run_id)
    port2 = MagicMock()
    port2.load = AsyncMock(return_value=None)
    assert await _ckpt_svc(port=port2).get_checkpoint("p") is None


async def test_checkpoint_get_for_run_no_tracer() -> None:
    run_id = RunID(UUID(int=1022))
    port = MagicMock()
    port.load_for_run = AsyncMock(return_value=(run_id, {"k": 1}))
    out = await _ckpt_svc(port=port).get_checkpoint_for_run("p", str(run_id))
    assert out is not None and out.run_id == str(run_id)


async def test_checkpoint_get_for_manifest_no_tracer() -> None:
    run_id = RunID(UUID(int=1023))
    port = MagicMock()
    port.load_for_manifest_id = AsyncMock(return_value=(run_id, {"pipeline_name": "p"}))
    out = await _ckpt_svc(port=port).get_checkpoint_for_manifest_id("p", "m-1")
    assert out is not None and out.pipeline_name == "p"


async def test_checkpoint_delete_no_tracer() -> None:
    port = MagicMock()
    port.load = AsyncMock(return_value=None)
    assert await _ckpt_svc(port=port).delete_checkpoint("p") is False
    port2 = MagicMock()
    port2.load = AsyncMock(return_value=(RunID(UUID(int=1024)), {}))
    port2.delete = AsyncMock(return_value=None)
    assert await _ckpt_svc(port=port2).delete_checkpoint("p") is True

