# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from datetime import UTC, datetime
from unittest import mock
from types import SimpleNamespace

import pytest

from bioetl.application.services.export_lineage.audit_inspection_service import (
    AuditInspectionResult,
)
from bioetl.application.services.checkpoint.checkpoint_service import CheckpointInfo
from bioetl.application.services.workflow.observability_workflow_service import (
    ObservabilityWorkflowService,
)
from bioetl.application.services.workflow._observability_workflow_lookup_support import (
    resolve_checkpoint_for_run,
    resolve_lineage_for_run,
    resolve_pipeline_name,
    resolve_run_manifest,
)
from bioetl.domain.ports.noop import NoOpTracing


def _make_mock_tracer() -> mock.MagicMock:
    """Create a tracing port mock with an inspectable span context."""
    mock_span = mock.MagicMock()
    mock_span.__enter__ = mock.MagicMock(return_value=mock_span)
    mock_span.__exit__ = mock.MagicMock(return_value=None)
    mock_span.set_attribute = mock.MagicMock()
    mock_span.record_exception = mock.MagicMock()

    mock_otel_tracer = mock.MagicMock()
    mock_otel_tracer.start_as_current_span = mock.MagicMock(return_value=mock_span)

    mock_tracer = mock.MagicMock()
    mock_tracer.get_tracer = mock.MagicMock(return_value=mock_otel_tracer)
    mock_tracer.flush = mock.MagicMock()
    return mock_tracer


def _make_manifest_result(
    *,
    pipeline_name: str = "chembl_activity",
    bronze_records: int = 10,
    persistence_profile: dict[str, object] | None = None,
    extra_diagnostics: dict[str, object] | None = None,
) -> SimpleNamespace:
    """Create a lightweight run-manifest result stub for workflow tests."""
    profile = persistence_profile or {
        "attained_profile": "forensic_grade",
        "required_profile": "forensic_grade",
        "required_profile_satisfied": True,
    }
    diagnostics = {
        "latest_status": "success",
        "latest_event_type": "run_finished",
        "correlation_anchor_gaps": {"run_id": 0, "manifest_id": 0},
        "artifact_refs": ["manifest://manifest-1", "ledger://manifest-1"],
        "lineage_fragment_ids": ["fragment-1"],
        "persistence_profile": profile,
        "next_steps": ["review dossier output"],
    }
    if extra_diagnostics:
        diagnostics.update(extra_diagnostics)
    return SimpleNamespace(
        manifest=SimpleNamespace(
            pipeline_name=pipeline_name,
            provider="chembl",
            run_type="incremental",
            created_at=datetime(2026, 4, 10, 10, 0, tzinfo=UTC),
        ),
        ledger_entries=(
            SimpleNamespace(metrics_snapshot={"records_bronze": bronze_records}),
        ),
        diagnostics=diagnostics,
        identity_graph={"replay_capability": "exact_replay_supported"},
        to_dict=lambda: {"manifest": {"pipeline_name": pipeline_name}},
    )


def _make_checkpoint_manifest_result(
    *,
    execution_fingerprint: str = "fingerprint-1",
    effective_config_hash: str = "effective-hash-1",
    requested_exact_replay: bool = True,
    replay_capability: str = "exact_replay_supported",
    replay_mode: str = "exact_replay",
    continuation_mode: str = "exact_replay",
    operator_replay_mode: str = "Exact Replay",
    replay_readiness_verdict: str = "exact_replay_ready",
) -> SimpleNamespace:
    """Create a manifest stub with checkpoint compatibility anchors."""
    return SimpleNamespace(
        manifest=SimpleNamespace(
            pipeline_name="chembl_activity",
            provider="chembl",
            run_type="incremental",
            run_id="run-123",
            manifest_id="manifest-1",
            execution_fingerprint=execution_fingerprint,
            launch_context={"exact_replay": requested_exact_replay},
            code_provenance=SimpleNamespace(
                effective_config_hash=effective_config_hash,
                effective_config_artifact_id="effective-artifact-1",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                dq_contract_compatibility_hash="dq-hash-1",
            ),
        ),
        ledger_entries=(),
        diagnostics={
            "requested_exact_replay": requested_exact_replay,
            "replay_capability": replay_capability,
            "replay_mode": replay_mode,
            "continuation_mode": continuation_mode,
            "operator_replay_mode": operator_replay_mode,
            "replay_readiness_verdict": replay_readiness_verdict,
            "input_snapshot_identity_fingerprint": "snapshot-fingerprint-1",
        },
        identity_graph={
            "replay_capability": replay_capability,
            "replay_mode": replay_mode,
            "continuation_mode": continuation_mode,
            "operator_replay_mode": operator_replay_mode,
            "replay_readiness_verdict": replay_readiness_verdict,
        },
        to_dict=lambda: {"manifest": {"pipeline_name": "chembl_activity"}},
    )


class _FailingLineageService:
    def explain_run(self, run_id: str) -> object:
        raise ValueError(run_id)


class _FailingManifestService:
    def show(self, identifier: str) -> object:
        raise ValueError(identifier)


@pytest.mark.asyncio
async def test_observability_lookup_support_fail_closed_paths() -> None:
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint_for_run.return_value = None
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="other-run",
        metadata=object(),
    )

    assert resolve_pipeline_name(None) is None
    assert (
        await resolve_checkpoint_for_run(
            checkpoint_service=checkpoint_service,
            run_id="run-123",
            pipeline_name=None,
        )
        is None
    )

    checkpoint = await resolve_checkpoint_for_run(
        checkpoint_service=checkpoint_service,
        run_id="run-123",
        pipeline_name="chembl_activity",
    )

    assert checkpoint is not None
    assert checkpoint.run_id == "other-run"
    assert checkpoint.metadata == {"status": "mismatched_run_context"}
    assert resolve_lineage_for_run(None, "run-123") is None
    assert resolve_lineage_for_run(_FailingLineageService(), "run-123") is None
    assert resolve_run_manifest(None, "manifest-1") is None
    assert resolve_run_manifest(_FailingManifestService(), "manifest-1") is None


@pytest.mark.asyncio
async def test_inspect_audit_run_returns_manifest_context() -> None:
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = manifest = mock.Mock()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=mock.AsyncMock(),
        run_manifest_service=run_manifest_service,
        tracer=_make_mock_tracer(),
    )

    result = await service.inspect_audit_run("abc", limit=7)

    assert result.run_id == "abc"
    assert result.audit is audit_result
    assert result.run_manifest is manifest
    audit_service.inspect_run.assert_awaited_once_with("abc", limit=7)
    run_manifest_service.show.assert_called_once_with("abc")


@pytest.mark.asyncio
async def test_inspect_manifest_dossier_resolves_run_id_from_manifest() -> None:
    audit_result = AuditInspectionResult(query={"run_id": "run-123"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint_for_run.return_value = None
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = manifest = _make_manifest_result()
    manifest.manifest.run_id = "run-123"

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_manifest_dossier("manifest-1", audit_limit=11)

    assert result.run_id == "run-123"
    assert result.run_manifest is manifest
    run_manifest_service.show.assert_called_once_with("manifest-1")
    audit_service.inspect_run.assert_awaited_once_with("run-123", limit=11)


@pytest.mark.asyncio
async def test_checkpoint_workflow_derives_run_id_from_checkpoint() -> None:
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-123",
        metadata={"records_processed": 5},
    )
    audit_result = AuditInspectionResult(query={"run_id": "run-123"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = manifest = mock.Mock()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
        tracer=_make_mock_tracer(),
    )

    result = await service.inspect_checkpoint_workflow("chembl_activity", audit_limit=9)

    assert result.pipeline_name == "chembl_activity"
    assert result.audit is audit_result
    assert result.run_manifest is manifest
    audit_service.inspect_run.assert_awaited_once_with("run-123", limit=9)
    run_manifest_service.show.assert_called_once_with("run-123")


@pytest.mark.asyncio
async def test_checkpoint_workflow_to_dict_includes_compatibility_taxonomy() -> None:
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-123",
        metadata={
            "records_processed": 5,
            "manifest_id": "manifest-1",
            "execution_fingerprint": "fingerprint-1",
            "effective_config_hash": "effective-hash-1",
            "effective_config_artifact_id": "effective-artifact-1",
            "contract_ref": "chembl.activity",
            "contract_version": "1.0.0",
            "dq_contract_compatibility_hash": "dq-hash-1",
            "exact_replay": True,
            "input_snapshot_fingerprint": "snapshot-fingerprint-1",
        },
    )
    audit_result = AuditInspectionResult(query={"run_id": "run-123"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = _make_checkpoint_manifest_result()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_checkpoint_workflow("chembl_activity")
    compatibility = result.to_dict()["compatibility"]

    assert compatibility["status"] == "compatible"
    assert compatibility["taxonomy"] == "exact_replay"
    assert compatibility["replay_capability"] == "exact_replay_supported"
    assert compatibility["continuation_mode"] == "exact_replay"
    assert compatibility["replay_readiness_verdict"] == "exact_replay_ready"
    assert compatibility["replay_resume_rebuild_verdict"] == "exact_replay_ready"
    assert compatibility["mismatched_anchors"] == []
    assert "execution_fingerprint" in compatibility["matched_anchors"]


@pytest.mark.asyncio
async def test_checkpoint_workflow_blocks_exact_replay_when_taxonomy_is_resume() -> (
    None
):
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-123",
        metadata={
            "records_processed": 5,
            "manifest_id": "manifest-1",
            "execution_fingerprint": "fingerprint-1",
            "effective_config_hash": "effective-hash-1",
            "effective_config_artifact_id": "effective-artifact-1",
            "contract_ref": "chembl.activity",
            "contract_version": "1.0.0",
            "dq_contract_compatibility_hash": "dq-hash-1",
            "exact_replay": True,
            "input_snapshot_fingerprint": "snapshot-fingerprint-1",
        },
    )
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = AuditInspectionResult(
        query={"run_id": "run-123"},
        entries=(),
    )
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = _make_checkpoint_manifest_result(
        replay_capability="resume_only",
        replay_mode="resume",
        continuation_mode="checkpoint_snapshot_only_resume",
        operator_replay_mode="Resume",
        replay_readiness_verdict="resume_compatible",
    )
    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_checkpoint_workflow("chembl_activity")
    compatibility = result.to_dict()["compatibility"]

    assert compatibility["compatible"] is False
    assert compatibility["status"] == "incompatible"
    assert compatibility["taxonomy"] == "exact_replay_blocked_resume_semantics"
    assert compatibility["replay_resume_rebuild_verdict"] == "resume_only"
    assert compatibility["mismatched_anchors"] == [
        {
            "anchor": "operator_replay_mode",
            "checkpoint": "checkpoint_snapshot_only_resume",
            "manifest": "checkpoint_snapshot_only_resume",
        }
    ]


@pytest.mark.asyncio
async def test_checkpoint_workflow_to_dict_preserves_composite_suffix_resume_taxonomy() -> (
    None
):
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="composite_publication",
        run_id="run-123",
        metadata={
            "records_processed": 5,
            "manifest_id": "manifest-1",
            "execution_fingerprint": "fingerprint-1",
            "effective_config_hash": "effective-hash-1",
            "effective_config_artifact_id": "effective-artifact-1",
            "contract_ref": "chembl.activity",
            "contract_version": "1.0.0",
            "dq_contract_compatibility_hash": "dq-hash-1",
            "exact_replay": False,
            "input_snapshot_fingerprint": "snapshot-fingerprint-1",
        },
    )
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = AuditInspectionResult(
        query={"run_id": "run-123"},
        entries=(),
    )
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = _make_checkpoint_manifest_result(
        requested_exact_replay=False,
        replay_capability="resume_only",
        replay_mode="resume",
        continuation_mode="checkpoint_snapshot_plus_ledger_suffix_resume",
        operator_replay_mode="Lifecycle Projection",
        replay_readiness_verdict="lifecycle_projection_only",
    )

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_checkpoint_workflow("composite_publication")
    compatibility = result.to_dict()["compatibility"]

    assert compatibility["status"] == "compatible"
    assert compatibility["taxonomy"] == (
        "checkpoint_snapshot_plus_ledger_suffix_resume"
    )
    assert compatibility["replay_capability"] == "resume_only"
    assert compatibility["replay_mode"] == "resume"
    assert compatibility["continuation_mode"] == (
        "checkpoint_snapshot_plus_ledger_suffix_resume"
    )
    assert compatibility["operator_replay_mode"] == "Lifecycle Projection"
    assert compatibility["replay_readiness_verdict"] == "lifecycle_projection_only"
    assert compatibility["replay_resume_rebuild_verdict"] == "resume_only"


@pytest.mark.asyncio
async def test_checkpoint_workflow_to_dict_blocks_identity_mismatch() -> None:
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-123",
        metadata={
            "records_processed": 5,
            "manifest_id": "manifest-1",
            "execution_fingerprint": "fingerprint-stale",
            "effective_config_hash": "effective-hash-1",
        },
    )
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = AuditInspectionResult(
        query={"run_id": "run-123"},
        entries=(),
    )
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = _make_checkpoint_manifest_result()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_checkpoint_workflow("chembl_activity")
    compatibility = result.to_dict()["compatibility"]

    assert compatibility["status"] == "incompatible"
    assert compatibility["taxonomy"] == "blocked_resume"
    assert {
        "anchor": "execution_fingerprint",
        "checkpoint": "fingerprint-stale",
        "manifest": "fingerprint-1",
    } in compatibility["mismatched_anchors"]


@pytest.mark.asyncio
async def test_checkpoint_workflow_returns_empty_audit_without_run_context() -> None:
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id=None,
        metadata={},
    )
    audit_service = mock.AsyncMock()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=None,
        tracer=_make_mock_tracer(),
    )

    result = await service.inspect_checkpoint_workflow(
        "chembl_activity", audit_limit=11
    )

    assert result.audit.entries == ()
    assert result.run_manifest is None
    audit_service.inspect_run.assert_not_called()


@pytest.mark.asyncio
async def test_inspect_audit_run_creates_trace_span() -> None:
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    tracer = _make_mock_tracer()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=mock.AsyncMock(),
        run_manifest_service=None,
        tracer=tracer,
    )

    await service.inspect_audit_run("abc")

    tracer.get_tracer.assert_called_once_with("bioetl.diagnostics")
    args = tracer.get_tracer.return_value.start_as_current_span.call_args
    assert args[0][0] == "diagnostics.inspect_audit_run"


@pytest.mark.asyncio
async def test_inspect_run_dossier_aggregates_forensic_sections() -> None:
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result

    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="abc",
        metadata={"records_processed": 5},
    )

    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = manifest = _make_manifest_result()

    lineage_result = mock.Mock()
    lineage_result.fragment_ids = ("fragment-1",)
    lineage_result.to_dict.return_value = {"fragment_ids": ["fragment-1"]}
    lineage_service = mock.Mock()
    lineage_service.explain_run.return_value = lineage_result

    quarantine_service = mock.AsyncMock()
    quarantine_service.get_filtered_stats.return_value = {
        "total": 3,
        "silver_filter_rejects": {"total_count": 2},
    }

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
        lineage_service=lineage_service,
        quarantine_service=quarantine_service,
        tracer=_make_mock_tracer(),
    )

    result = await service.inspect_run_dossier("abc", audit_limit=7)

    assert result.run_id == "abc"
    assert result.pipeline_name == "chembl_activity"
    assert result.audit is audit_result
    assert result.run_manifest is manifest
    assert result.lineage is lineage_result
    assert result.status == {
        "forensic_profile": "forensic_grade",
        "latest_status": "success",
        "latest_event_type": "run_finished",
        "checkpoint_status": "present",
        "lineage_status": "present",
        "quarantine_status": "present",
        "missing_evidence_count": 0,
        "degraded_evidence_count": 0,
        "operational_success": True,
        "operational_success_criteria": {
            "critical_pipeline": True,
            "runtime_terminal_success": True,
            "required_evidence_profile": "forensic_grade",
            "attained_evidence_profile": "forensic_grade",
            "required_profile_satisfied": True,
            "dossier_evidence_satisfied": True,
            "operational_success": True,
        },
    }
    assert result.traceability == {
        "audit_entries_count": 0,
        "identity_graph_complete": None,
        "correlation_anchor_gaps": {"run_id": 0, "manifest_id": 0},
        "lineage_fragment_ids": ["fragment-1"],
        "artifact_refs": ["manifest://manifest-1", "ledger://manifest-1"],
        "trace_ids": ["abc"],
        "trace_identifiers_available": True,
        "persistence_profile": {
            "attained_profile": "forensic_grade",
            "required_profile": "forensic_grade",
            "required_profile_satisfied": True,
        },
        "replay_capability": "exact_replay_supported",
    }
    assert result.quarantine_summary == {
        "total": 3,
        "silver_filter_rejects": {
            "total_count": 2,
            "bronze_records": 10,
            "bronze_ratio": 0.2,
            "bronze_ratio_pct": 20.0,
        },
        "run_scope": {"run_id": "abc"},
    }
    assert result.missing_evidence == ()
    assert result.degraded_evidence == ()
    assert result.next_steps == ("review dossier output",)
    assert result.to_dict()["checkpoint"] == {
        "pipeline_name": "chembl_activity",
        "run_id": "abc",
        "metadata": {"records_processed": 5},
    }
    audit_service.inspect_run.assert_awaited_once_with("abc", limit=7)
    checkpoint_service.get_checkpoint.assert_awaited_once_with("chembl_activity")
    run_manifest_service.show.assert_called_once_with("abc")
    lineage_service.explain_run.assert_called_once_with("abc")
    quarantine_service.get_filtered_stats.assert_awaited_once_with(
        pipeline="chembl_activity",
        run_id="abc",
    )


@pytest.mark.asyncio
async def test_inspect_run_dossier_degrades_traceability_when_tracing_is_noop() -> None:
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result

    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="abc",
        metadata={"records_processed": 5},
    )

    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = _make_manifest_result()

    lineage_result = mock.Mock()
    lineage_result.fragment_ids = ("fragment-1",)
    lineage_result.to_dict.return_value = {"fragment_ids": ["fragment-1"]}
    lineage_service = mock.Mock()
    lineage_service.explain_run.return_value = lineage_result

    quarantine_service = mock.AsyncMock()
    quarantine_service.get_filtered_stats.return_value = {
        "total": 3,
        "silver_filter_rejects": {"total_count": 2},
    }

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
        lineage_service=lineage_service,
        quarantine_service=quarantine_service,
        tracer=NoOpTracing(),
    )

    result = await service.inspect_run_dossier("abc", audit_limit=7)

    assert result.traceability["trace_ids"] == []
    assert result.traceability["trace_identifiers_available"] is False
    assert "trace_identifiers_unavailable" in result.degraded_evidence
    assert "critical_dossier_evidence_gap" in result.degraded_evidence
    assert result.status["operational_success"] is False
    assert result.status["operational_success_criteria"] == {
        "critical_pipeline": True,
        "runtime_terminal_success": True,
        "required_evidence_profile": "forensic_grade",
        "attained_evidence_profile": "forensic_grade",
        "required_profile_satisfied": True,
        "dossier_evidence_satisfied": False,
        "operational_success": False,
    }
    assert (
        "Resolve dossier evidence gaps before marking this critical run "
        "operationally successful." in result.next_steps
    )
    assert (
        "Use audit, manifest, and lineage sections as the current traceability fallback."
        in result.next_steps
    )


@pytest.mark.asyncio
async def test_inspect_run_dossier_blocks_operational_success_for_critical_profile_gap() -> (
    None
):
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result

    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="abc",
        metadata={"records_processed": 5},
    )

    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = _make_manifest_result(
        persistence_profile={
            "attained_profile": "replay_ready",
            "required_profile": "forensic_grade",
            "required_profile_satisfied": False,
            "required_profile_missing_requirements": ["lineage_closure_boundary"],
        }
    )

    lineage_result = mock.Mock()
    lineage_result.fragment_ids = ("fragment-1",)
    lineage_result.to_dict.return_value = {"fragment_ids": ["fragment-1"]}
    lineage_service = mock.Mock()
    lineage_service.explain_run.return_value = lineage_result

    quarantine_service = mock.AsyncMock()
    quarantine_service.get_filtered_stats.return_value = {
        "total": 0,
        "silver_filter_rejects": {"total_count": 0},
    }

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
        lineage_service=lineage_service,
        quarantine_service=quarantine_service,
        tracer=_make_mock_tracer(),
    )

    result = await service.inspect_run_dossier("abc")

    assert "persistence_profile:replay_ready" in result.degraded_evidence
    assert "required_profile_missing_requirements" in result.degraded_evidence
    assert "critical_dossier_evidence_gap" in result.degraded_evidence
    assert result.status["operational_success"] is False
    assert result.status["operational_success_criteria"] == {
        "critical_pipeline": True,
        "runtime_terminal_success": True,
        "required_evidence_profile": "forensic_grade",
        "attained_evidence_profile": "replay_ready",
        "required_profile_satisfied": False,
        "dossier_evidence_satisfied": False,
        "operational_success": False,
    }


@pytest.mark.asyncio
async def test_inspect_run_dossier_surfaces_composite_projection() -> None:
    projection = {
        "is_composite_run": True,
        "primary_composite_run_id": "composite-run-1",
        "composite_run_ids": ["composite-run-1"],
        "correlation_policy": {"required_anchor": "composite_run_id"},
    }
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result

    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = None

    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = _make_manifest_result(
        pipeline_name="composite_activity",
        extra_diagnostics={"composite_dossier_projection": projection},
    )

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
        lineage_service=None,
        quarantine_service=None,
        tracer=_make_mock_tracer(),
    )

    result = await service.inspect_run_dossier("abc")

    assert result.traceability["composite_projection"] == projection
    assert result.traceability["trace_ids"] == ["abc", "composite-run-1"]
    assert result.traceability["trace_identifiers_available"] is True
