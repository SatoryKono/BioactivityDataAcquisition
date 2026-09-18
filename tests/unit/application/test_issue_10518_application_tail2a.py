"""Behavior-focused unit tests closing application-layer residuals for #10518.

Covers small missing-line residuals measured against ``tests/unit/application``
(batch tail2a: cross-reference extractors through manifest validation).
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit


def _run_id(label: str):
    from bioetl.domain.types import RunID

    namespace = UUID("11111111-1111-1111-1111-111111111111")
    return RunID(UUID(int=namespace.int ^ hash(label) % (2**32)))


def _manifest(run_id, manifest_id="manifest-1"):
    from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
    from bioetl.domain.types import RunType

    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint="fingerprint-1",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )


def _run_ledger_service(run_id, manifest_id="manifest-1"):
    from bioetl.application.services.control_plane import RunLedgerService
    from tests.helpers.control_plane import InMemoryRunLedgerStore

    return RunLedgerService(
        ledger_port=InMemoryRunLedgerStore(),
        manifest_id=manifest_id,
        run_id=run_id,
        _entry_id_factory=lambda: "entry-1",
        _occurred_at_factory=lambda: datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )


# --- _crossref_structured (100, 122, 149) ---


def test_build_interpro_entry_without_id_returns_none() -> None:
    from bioetl.application.pipelines.uniprot.extractors._crossref_structured import (
        build_interpro_entry,
    )

    assert build_interpro_entry({}) is None
    assert build_interpro_entry({"id": ""}) is None


def test_build_pfam_entry_without_id_returns_none() -> None:
    from bioetl.application.pipelines.uniprot.extractors._crossref_structured import (
        build_pfam_entry,
    )

    assert build_pfam_entry({}) is None
    assert build_pfam_entry({"id": None}) is None


def test_build_reactome_entry_without_id_returns_none() -> None:
    from bioetl.application.pipelines.uniprot.extractors._crossref_structured import (
        build_reactome_entry,
    )

    assert build_reactome_entry({}) is None
    assert build_reactome_entry({"id": ""}) is None


# --- _checkpoint_compatibility_runtime_identity_details (62, 85, 180) ---


def test_checkpoint_fallback_detail_matches_canonical_fingerprint() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_runtime_identity_details import (
        _checkpoint_execution_identity_fallback_detail,
    )
    from bioetl.domain.normalization import compute_execution_identity_fingerprint

    payload = {"effective_config_hash": "a" * 64}
    assert _checkpoint_execution_identity_fallback_detail(
        payload
    ) == compute_execution_identity_fingerprint(payload)
    assert _checkpoint_execution_identity_fallback_detail({}) == ""


def test_degraded_runtime_anchor_detail_empty_payload_returns_empty() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_runtime_identity_details import (
        _degraded_runtime_anchor_detail,
    )

    assert (
        _degraded_runtime_anchor_detail(
            manifest_id=None,
            contract_ref=None,
            contract_version=None,
            effective_config_hash=None,
            effective_config_artifact_id=None,
        )
        == ""
    )


def test_generate_details_assembles_compatibility_payload() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_runtime_identity_details import (
        generate_details,
    )

    details = generate_details(
        phase_result={"ok": True},
        config_result={"ok": True},
        execution_identity_result={"ok": True},
        schema_result={"ok": True},
        current_identity_details={"id": "current"},
        checkpoint_identity_details={"id": "checkpoint"},
        mode="strict",
        allow_policy_override=False,
        max_schema_version_delta=1,
    )
    assert details["phase_compatibility"] == {"ok": True}
    assert details["current_identity"] == {"id": "current"}
    assert details["checkpoint_identity"] == {"id": "checkpoint"}
    assert details["compatibility_mode"] == "strict"
    assert details["allow_policy_override"] is False
    assert details["max_schema_version_delta"] == 1


# --- contract_migration_models (27, 45, 74) ---


def test_contract_migration_action_record_payload() -> None:
    from bioetl.application.services.contracts.contract_migration_models import (
        ContractMigrationActionRecord,
    )

    payload = ContractMigrationActionRecord(
        code="REVIEW", title="Review", description="Operator review required"
    ).to_payload()
    assert payload == {
        "code": "REVIEW",
        "title": "Review",
        "description": "Operator review required",
    }


def test_contract_version_transition_record_payload() -> None:
    from bioetl.application.services.contracts.contract_migration_models import (
        ContractVersionTransitionRecord,
    )

    payload = ContractVersionTransitionRecord(
        from_version="v1",
        to_version="v2",
        migration_guide=None,
        affects_hash=True,
    ).to_payload()
    assert payload == {
        "from_version": "v1",
        "to_version": "v2",
        "migration_guide": None,
        "affects_hash": True,
    }


def test_contract_migration_plan_summary_payload() -> None:
    from bioetl.application.services.contracts.contract_migration_models import (
        ContractMigrationPlanSummary,
    )

    payload = ContractMigrationPlanSummary(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        contract_ref="chembl/activity",
        active_version="v1",
        rollout_mode="shadow",
        read_order=("v1",),
        write_versions=("v1",),
        shadow_versions=("v2",),
        affects_hash=False,
        supported_versions=("v1", "v2"),
        transitions=(),
        required_actions=(),
        notes=(),
    ).to_payload()
    assert payload["pipeline_name"] == "chembl_activity"
    assert payload["read_order"] == ["v1"]
    assert payload["shadow_versions"] == ["v2"]
    assert payload["transitions"] == []
    assert payload["notes"] == []


# --- ledger core_events (76, 142, 215) ---


def test_coalesce_missing_prefers_current_value() -> None:
    from bioetl.application.services.control_plane.ledger.core_events import (
        _coalesce_missing,
    )

    assert _coalesce_missing("current", "default") == "current"
    assert _coalesce_missing(None, "default") == "default"


def test_record_manifest_created_rejects_run_id_mismatch() -> None:
    from bioetl.application.services.control_plane.ledger import core_events

    service = _run_ledger_service(_run_id("core-a"))
    manifest = _manifest(_run_id("core-b"))
    with pytest.raises(ValueError, match="run_id must match"):
        core_events.record_manifest_created(service, manifest)


def test_record_dq_policy_applied_merges_detail_payload() -> None:
    from bioetl.application.services.control_plane.ledger import core_events

    run_id = _run_id("core-dq")
    service = _run_ledger_service(run_id)
    service.record_manifest_created(_manifest(run_id))
    entry = core_events.record_dq_policy_applied(
        service,
        stage="gold",
        status="failed",
        rule_id="rule-1",
        details={"custom": "trace"},
    )
    assert entry.details["rule_id"] == "rule-1"
    assert entry.details["custom"] == "trace"


# --- ledger rich_events (68, 80, 91) ---


def test_rich_event_mixin_delegates_dependency_recording() -> None:
    from bioetl.application.services.control_plane.ledger.rich_events import (
        RunLedgerRichEventRecordingMixin,
    )

    class _Fake(RunLedgerRichEventRecordingMixin):
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def _append(self, **kwargs):
            self.calls.append(kwargs)
            return {"entry": len(self.calls)}

    fake = _Fake()
    assert fake.record_composite_dependency_completed(
        dependency_name="dep", result={"ok": True}
    ) == {"entry": 1}
    assert fake.calls[0]["stage"] == "dependencies"
    assert fake.calls[0]["details"]["dependency_name"] == "dep"


def test_rich_event_mixin_delegates_enricher_recording() -> None:
    from bioetl.application.services.control_plane.ledger.rich_events import (
        RunLedgerRichEventRecordingMixin,
    )

    class _Fake(RunLedgerRichEventRecordingMixin):
        def _append(self, **kwargs):
            return kwargs

    recorded = _Fake().record_composite_enricher_completed(
        enricher_name="enr", result={"ok": True}
    )
    assert recorded["stage"] == "enrichment"
    assert recorded["details"]["enricher_name"] == "enr"


def test_rich_event_mixin_delegates_merge_recording() -> None:
    from bioetl.application.services.control_plane.ledger.rich_events import (
        RunLedgerRichEventRecordingMixin,
    )

    class _Fake(RunLedgerRichEventRecordingMixin):
        def _append(self, **kwargs):
            return kwargs

    recorded = _Fake().record_composite_merge_completed(result={"ok": True})
    assert recorded["stage"] == "merge"
    assert recorded["details"] == {"ok": True}


# --- manifest diagnostics __init__ (22, 23, 24) ---


def test_as_str_object_dict_accepts_non_dict_mapping() -> None:
    import bioetl.application.services.control_plane.manifest.diagnostics as diagnostics

    assert diagnostics._as_str_object_dict(MappingProxyType({"a": 1})) == {"a": 1}
    assert diagnostics._as_str_object_dict({"b": 2}) == {"b": 2}


def test_as_str_object_dict_rejects_non_mapping() -> None:
    import bioetl.application.services.control_plane.manifest.diagnostics as diagnostics

    with pytest.raises(TypeError, match="expected mapping"):
        diagnostics._as_str_object_dict(object())


# --- replay_blockers (46, 53, 80) ---


def test_collect_append_mode_sinks_prefers_declared_sinks() -> None:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants import (
        replay_blockers as blockers,
    )

    manifest = SimpleNamespace(
        launch_context={
            "append_mode_semantic_sinks": [" sink.x.mode=append ", "", 42]
        },
        runtime_config={},
        resolved_config={},
    )
    assert blockers._collect_append_mode_semantic_sinks(manifest) == [
        "sink.x.mode=append"
    ]


def test_is_append_enabled_sink_rejects_non_conforming_shapes() -> None:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants import (
        replay_blockers as blockers,
    )

    assert blockers._is_append_enabled_sink(42, {"mode": "append"}) is False
    assert blockers._is_append_enabled_sink("sink", ["not-a-dict"]) is False


# --- replay_refresh_support (149, 150, 151) ---


def test_build_refresh_summary_update_rewrites_lifecycle_projection() -> None:
    import bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support as refresh
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_types import (
        _ReplayRefreshProjection,
    )

    projection = _ReplayRefreshProjection(
        replay_payload={
            "replay_readiness_verdict": "lifecycle_projection_only",
            "operator_replay_mode": "Lifecycle Projection",
        },
        exact_replay_eligible=True,
        replay_mode="resume",
        continuation_mode="resume",
        snapshot_status="ok",
        resume_contract={"mode": "resume"},
    )
    with (
        patch.object(
            refresh, "_build_refresh_replay_projection", return_value=projection
        ),
        patch.object(
            refresh,
            "_refresh_replay_summary_update_snapshot_fields",
            side_effect=lambda **kwargs: kwargs["updated"],
        ),
    ):
        update = refresh._build_refresh_summary_update(
            summary={"composite_resume_rich_replay_supported": True},
            refresh_context=MagicMock(),
        )
    assert update.payload["replay_readiness_verdict"] == "resume_compatible"
    assert update.payload["operator_replay_mode"] == "Resume"


# --- snapshot_payloads (3, 5, 13) ---


def test_snapshot_payloads_facade_reexports_domain_builders() -> None:
    import bioetl.application.services.control_plane.manifest.snapshot_payloads as facade
    import bioetl.domain.control_plane.snapshot_payloads as domain

    assert set(facade.__all__) == {
        "input_snapshot_payload",
        "manifest_input_snapshot_trace_refs",
        "serialize_snapshot_captured_at",
        "source_ref_payload",
        "source_refs_payload",
    }
    assert facade.input_snapshot_payload is domain.input_snapshot_payload
    assert facade.source_refs_payload is domain.source_refs_payload


# --- validation_provenance (78, 79, 167) ---


def test_production_provenance_gate_wraps_value_error() -> None:
    from bioetl.application.services.control_plane.manifest.validation_provenance import (
        _validate_production_provenance_gate,
    )
    from bioetl.domain.control_plane import RunCodeProvenance

    with pytest.raises(RuntimeError, match="incomplete for production"):
        _validate_production_provenance_gate(
            SimpleNamespace(launch_context={"env": "production"}),
            RunCodeProvenance(),
        )


def test_documented_provenance_rejects_commit_with_git_unavailable() -> None:
    from bioetl.application.services.control_plane.manifest.validation_provenance import (
        _validate_documented_code_provenance,
    )
    from bioetl.domain.control_plane import RunCodeProvenance

    with pytest.raises(RuntimeError, match="git_unavailable"):
        _validate_documented_code_provenance(
            RunCodeProvenance(
                source_revision_state="git_unavailable", git_commit="abc123"
            )
        )


# --- _historical_certification_upstream (123, 134, 152) ---


def test_load_upstream_manifest_fails_when_missing() -> None:
    from bioetl.application.services.control_plane.replay import (
        _historical_certification_upstream as upstream,
    )

    with pytest.raises(ValueError, match="was not found"):
        upstream.load_upstream_manifest(
            manifest_port=SimpleNamespace(get=lambda manifest_id: None),
            certification=SimpleNamespace(upstream_manifest_id="m-x"),
        )


def test_validate_upstream_run_id_match_rejects_mismatch() -> None:
    from bioetl.application.services.control_plane.replay import (
        _historical_certification_upstream as upstream,
    )

    with pytest.raises(ValueError, match="does not match"):
        upstream.validate_upstream_run_id_match(
            certification=SimpleNamespace(upstream_run_id="run-a"),
            upstream_manifest=SimpleNamespace(run_id="run-b"),
        )


def test_validate_upstream_certification_state_requires_certified() -> None:
    from bioetl.application.services.control_plane.replay import (
        _historical_certification_upstream as upstream,
    )

    with pytest.raises(ValueError, match="historical_source_replay_certified"):
        upstream.validate_upstream_certification_state(
            ledger_port=SimpleNamespace(list_entries=lambda manifest_id: []),
            upstream_manifest=SimpleNamespace(manifest_id="m-1"),
            summary_builder=lambda manifest, entries: {
                "broader_historical_exact_replay_state": "uncertified"
            },
        )


# --- reproducibility_score_cards_category_scores (80, 81, 82) ---


def test_score_lineage_completeness_flags_unsupported_boundary() -> None:
    from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (
        score_lineage_completeness,
    )

    record = score_lineage_completeness(
        {
            "identity_graph_complete": True,
            "lineage_closure_boundary": {"supported": False},
            "missing_artifact_links": 0,
            "lineage_fragment_ids": ["fragment-1"],
        }
    )
    assert record.score == 8
    assert "lineage_closure_boundary_unsupported" in record.evidence
    assert "lineage_closure_boundary_unsupported" in record.blockers


# --- workflow ledger_service (49, 170, 196) ---


def test_missing_occurred_at_factory_fails_closed() -> None:
    from bioetl.application.services.control_plane.workflow import (
        ledger_service as workflow_ledger,
    )

    with pytest.raises(RuntimeError, match="occurred_at_factory"):
        workflow_ledger._missing_occurred_at_factory()


def _workflow_ledger_service():
    from bioetl.application.services.control_plane.workflow.ledger_service import (
        WorkflowLedgerService,
    )
    from bioetl.domain.types import RunID

    return WorkflowLedgerService(
        ledger_port=MagicMock(),
        manifest_id="workflow-manifest-1",
        workflow_run_id=RunID(UUID("33333333-3333-3333-3333-333333333333")),
        workflow_name="nightly",
        _entry_id_factory=lambda: "entry-1",
        _occurred_at_factory=lambda: datetime(2026, 2, 1, tzinfo=UTC),
    )


def test_record_workflow_failed_appends_failed_entry() -> None:
    service = _workflow_ledger_service()
    entry = service.record_workflow_failed(message="boom", error_type="RuntimeError")
    assert entry.status == "failed"
    assert entry.message == "boom"
    assert entry.error_type == "RuntimeError"


def test_record_force_requested_appends_step_ids() -> None:
    service = _workflow_ledger_service()
    entry = service.record_force_requested(step_ids=("step-1", "step-2"))
    assert entry.status == "requested"
    assert entry.details == {"step_ids": ["step-1", "step-2"]}


# --- audit_inspection_service (105, 118, 119) ---


def test_parse_run_id_returns_none_when_absent() -> None:
    from bioetl.application.services.export_lineage.audit_inspection_service import (
        AuditInspectionService,
    )

    assert AuditInspectionService._parse_run_id(None) is None


def test_resolve_layer_rejects_unknown_layer() -> None:
    from bioetl.application.services.export_lineage.audit_inspection_service import (
        AuditInspectionService,
    )

    with pytest.raises(ValueError, match="Invalid audit layer"):
        AuditInspectionService._resolve_layer("nope")


# --- export_execution (92, 318, 338) ---


async def test_export_existing_table_rejects_table_without_capabilities() -> None:
    from bioetl.application.services.export_lineage.export_execution import (
        export_existing_table,
    )
    from bioetl.application.services.export_lineage.export_models import ExportOptions
    from pathlib import Path

    reader = MagicMock()
    reader.read_table = AsyncMock(return_value=object())
    with pytest.raises(TypeError, match="without export capabilities"):
        await export_existing_table(
            reader=reader,
            writer=MagicMock(),
            logger=MagicMock(),
            export_path=Path("out"),
            table_name="table",
            layer="silver",
            options=ExportOptions(),
            table_path=Path("somewhere"),
        )


def test_should_not_redact_when_no_sensitive_columns() -> None:
    from bioetl.application.services.export_lineage.export_execution import (
        _should_redact_columns,
    )
    from bioetl.application.services.export_lineage.export_models import ExportOptions

    assert (
        _should_redact_columns((), options=ExportOptions(role="viewer")) is False
    )


def test_retained_columns_rejects_only_sensitive_table() -> None:
    from bioetl.application.services.export_lineage.export_execution import (
        _retained_export_columns,
    )

    with pytest.raises(PermissionError, match="only sensitive fields"):
        _retained_export_columns(
            column_names=("secret",),
            sensitive_columns=("secret",),
            role="viewer",
        )


# --- export_service (145, 154, 188) ---


def _export_service(reader) -> object:
    from bioetl.application.services.export_lineage.export_service import ExportService
    from pathlib import Path

    catalog = MagicMock()
    catalog.resolve_table_path = MagicMock(return_value="silver/table")
    return ExportService(
        reader=reader,
        catalog=catalog,
        writer=MagicMock(),
        logger=MagicMock(),
        silver_path=Path("silver"),
        gold_path=Path("gold"),
    )


async def test_preview_rejects_non_iterable_schema() -> None:
    reader = MagicMock()
    reader.get_schema = AsyncMock(return_value=object())
    with pytest.raises(TypeError, match="non-iterable preview schema"):
        await _export_service(reader).preview("table")


async def test_preview_rejects_table_without_preview_support() -> None:
    reader = MagicMock()

    class _Schema:
        def __iter__(self):
            return iter(
                [SimpleNamespace(name="a", type="string", nullable=True)]
            )

    reader.get_schema = AsyncMock(return_value=_Schema())
    reader.get_row_count = AsyncMock(return_value=3)
    reader.read_table = AsyncMock(return_value=object())
    with pytest.raises(TypeError, match="without preview support"):
        await _export_service(reader).preview("table")


async def test_export_returns_missing_table_result() -> None:
    reader = MagicMock()
    reader.table_exists = AsyncMock(return_value=False)
    result = await _export_service(reader).export("table", "silver")
    assert result.success is False


# --- lineage_inspection_results (32, 55, 82) ---


def _lineage_node():
    from bioetl.domain.lineage import LineageNodeRef, LineageNodeType

    return LineageNodeRef(
        node_type=LineageNodeType.DATASET, node_id="dataset-1", label="chembl.activity"
    )


def test_lineage_node_relation_result_payload() -> None:
    from bioetl.application.services.lineage.lineage_inspection_results import (
        LineageNodeRelationResult,
    )

    payload = LineageNodeRelationResult(
        fragment_id="f-1",
        stored_fragment_id=None,
        edge_type="upstream",
        node=_lineage_node(),
    ).to_dict()
    assert payload["fragment_id"] == "f-1"
    assert payload["stored_fragment_id"] is None
    assert payload["edge_type"] == "upstream"
    assert payload["node"]["node_id"] == "dataset-1"


def test_lineage_trace_result_payload() -> None:
    from bioetl.application.services.lineage.lineage_inspection_results import (
        LineageTraceResult,
    )

    payload = LineageTraceResult(
        dataset_ref="chembl.activity", fragment_ids=("f-1",)
    ).to_dict()
    assert payload["dataset_ref"] == "chembl.activity"
    assert payload["fragment_ids"] == ["f-1"]
    assert payload["stored_fragment_ids"] == []
    assert payload["upstream"] == []


def test_lineage_run_explanation_result_payload() -> None:
    from bioetl.application.services.lineage.lineage_inspection_results import (
        LineageRunExplanationResult,
    )

    payload = LineageRunExplanationResult(
        identifier="m-1", run_id=None, manifest_id="m-1", fragment_ids=()
    ).to_dict()
    assert payload["identifier"] == "m-1"
    assert payload["fragment_ids"] == []
    assert payload["produced_datasets"] == []


# --- lineage_inspection_service (156, 159, 179) ---


def _lineage_service():
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )

    store = MagicMock()
    store.list_by_manifest_id = MagicMock(return_value=[])
    store.list_by_run_id = MagicMock(return_value=[])
    manifest_port = MagicMock()
    manifest_port.get = MagicMock(return_value=None)
    manifest_port.get_by_run_id = MagicMock(return_value=None)
    return LineageInspectionService(
        lineage_store=store, manifest_port=manifest_port
    )


def test_resolve_via_manifest_returns_none_for_unknown_identifier() -> None:
    assert _lineage_service()._resolve_via_manifest("not-a-uuid") is None


def test_resolve_via_manifest_returns_none_for_unknown_run_id() -> None:
    assert (
        _lineage_service()._resolve_via_manifest(
            "11111111-1111-1111-1111-111111111111"
        )
        is None
    )


def test_resolve_via_direct_indexes_returns_none_without_fragments() -> None:
    assert (
        _lineage_service()._resolve_via_direct_indexes(
            "11111111-1111-1111-1111-111111111111"
        )
        is None
    )


# --- run_reports observations (55, 128, 129) ---


def test_record_run_observation_keeps_higher_severity_verdict() -> None:
    from bioetl.application.services.run_reports.observations import (
        bind_run_observations,
        record_run_observation,
        reset_run_observations,
        run_observations,
    )

    token = bind_run_observations()
    try:
        record_run_observation(
            "Data Validation", verdict="ERROR", reason="first", facts={}
        )
        record_run_observation(
            "Data Validation", verdict="OK", reason="second", facts={}
        )
        assert run_observations()["Data Validation"]["verdict"] == "ERROR"
    finally:
        reset_run_observations(token)


async def test_observe_gold_write_records_failure_and_reraises() -> None:
    from bioetl.application.services.run_reports.observations import (
        bind_run_observations,
        observe_gold_write,
        reset_run_observations,
        run_observations,
    )
    from bioetl.domain.types.gold_contracts_rejects import (
        GoldContractValidationError,
        GoldRejectReason,
        GoldRejectReasonCode,
    )

    reason = GoldRejectReason(
        reason_code=GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE,
        message="bad schema",
    )
    token = bind_run_observations()
    try:

        async def _failing():
            raise GoldContractValidationError(reason)

        with pytest.raises(GoldContractValidationError):
            await observe_gold_write(_failing(), 3)
        assert run_observations()["Data Validation"]["verdict"] == "ERROR"
    finally:
        reset_run_observations(token)


# --- execution_recording_payloads (53, 61, 130) ---


def test_step_completion_details_for_failed_step() -> None:
    from bioetl.application.services.workflow.control_plane.execution_recording_payloads import (
        build_step_completion_details,
    )
    from bioetl.application.services.workflow.workflow_runner_models import (
        WorkflowStepExecutionResult,
    )

    result = WorkflowStepExecutionResult(
        step_id="step-1", step_kind="transform", status="failed", payload=None
    )
    assert build_step_completion_details(result) is None


def test_step_completion_details_for_non_dict_output() -> None:
    from bioetl.application.services.workflow.control_plane.execution_recording_payloads import (
        build_step_completion_details,
    )
    from bioetl.application.services.workflow.workflow_runner_models import (
        WorkflowStepExecutionResult,
    )

    result = WorkflowStepExecutionResult(
        step_id="step-1",
        step_kind="transform",
        status="success",
        payload={"output": "not-a-dict"},
    )
    assert build_step_completion_details(result) is None


def test_artifact_refs_returns_none_for_non_list() -> None:
    from bioetl.application.services.workflow.control_plane.execution_recording_payloads import (
        _artifact_refs,
    )

    assert _artifact_refs({"artifact_refs": "not-a-list"}) is None


# --- workflow_runner_support (120, 121, 258) ---


def test_workflow_expected_provider_falls_back_to_unknown() -> None:
    from bioetl.application.services.workflow.workflow_runner_support import (
        _workflow_expected_provider,
    )
    from bioetl.domain.workflow import TransformStepConfig, WorkflowConfig

    config = WorkflowConfig(
        name="workflow",
        steps=(TransformStepConfig(step_id="s-1", transform_name="t-1"),),
    )
    assert config.pipeline_steps == ()
    assert _workflow_expected_provider(config) == "unknown"


def test_workflow_status_to_gauge_value_defaults_to_degraded() -> None:
    from bioetl.application.services.workflow.workflow_runner_support import (
        workflow_status_to_gauge_value,
    )

    assert workflow_status_to_gauge_value("cancelled") == 1.0
    assert workflow_status_to_gauge_value("success") == 0.0
    assert workflow_status_to_gauge_value("failed") == 2.0


# --- coordinator_execution (143, 149) ---


def test_handle_enricher_timeout_reraises_for_required_enricher() -> None:
    from bioetl.application.composite.helpers.coordinator_execution import (
        EnricherExecutionContext,
        handle_enricher_timeout,
    )
    from bioetl.domain.composite.config_models import EnricherConfig

    enricher = EnricherConfig(
        pipeline="chembl_activity",
        join_keys=("molecule_id",),
        required=True,
        timeout_seconds=5,
    )
    context = EnricherExecutionContext(
        enricher=enricher,
        records_input=3,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        started_monotonic_at=1.0,
    )
    host = SimpleNamespace(
        _logger=MagicMock(), _build_timeout_result=MagicMock()
    )
    with pytest.raises(TimeoutError, match="Required enricher timed out"):
        handle_enricher_timeout(host, context, TimeoutError("slow"))
    assert host._logger.error.called


# --- runner (121, 131) ---


def test_composite_runner_config_property_returns_wired_config() -> None:
    from bioetl.application.composite.runner_pkg.runner import CompositePipelineRunner

    runner = CompositePipelineRunner.__new__(CompositePipelineRunner)
    sentinel = SimpleNamespace(name="composite")
    runner._config = sentinel
    assert runner.config is sentinel


def test_composite_runner_emit_failed_run_delegates_to_helper() -> None:
    from bioetl.application.composite.runner_pkg import runner as runner_module

    runner = runner_module.CompositePipelineRunner.__new__(
        runner_module.CompositePipelineRunner
    )
    error = ValueError("boom")
    with patch.object(runner_module, "emit_failed_run") as emit:
        runner._emit_failed_run(error, reason_code="seed", stage="seed")
    assert emit.call_count == 1
    assert emit.call_args.kwargs["reason_code"] == "seed"
    assert emit.call_args.kwargs["stage"] == "seed"


# --- runner_control_plane_phase_completion (42, 95) ---


def test_record_dependency_completion_delegates_to_ledger() -> None:
    from bioetl.application.composite.runner_pkg.runner_control_plane_phase_completion import (
        _record_dependency_completion,
    )

    ledger = MagicMock()
    ledger.record_composite_dependency_completed = MagicMock(return_value="entry")
    assert (
        _record_dependency_completion(
            ledger, name="dep", data={"records": 2}
        )
        == "entry"
    )
    ledger.record_composite_dependency_completed.assert_called_once_with(
        dependency_name="dep", result={"records": 2}
    )


def test_record_seed_stage_completed_reports_resume_retry() -> None:
    from bioetl.application.composite.runner_pkg import (
        runner_control_plane_phase_completion as completion,
    )
    from bioetl.domain.composite.result_seed_dependency import SeedResult

    host = SimpleNamespace(
        _metrics=MagicMock(),
        _config=SimpleNamespace(name="composite"),
        _run_ledger_service=None,
    )
    seed = SeedResult(
        pipeline_name="seed", records_extracted=5, records_silver=3, resumed=True
    )
    with patch.object(completion, "PipelineMetricsRecorder") as recorder_cls:
        completion.record_seed_stage_completed(host, seed)
    recorder_cls.return_value.record_composite_phase_retries.assert_called_once_with(
        phase="seed", retry_kind="resume"
    )


# --- base_transformer_execution_mixin (60, 69) ---


def test_evaluate_semantic_shadow_decision_delegates_to_helper() -> None:
    from bioetl.application.core import base_transformer_execution_mixin as mixin

    with patch.object(
        mixin, "evaluate_semantic_shadow_decision", return_value="decision"
    ):
        assert (
            mixin._BaseTransformerExecutionMixin._evaluate_semantic_shadow_decision(
                object(), None
            )
            == "decision"
        )


def test_record_structural_policy_metrics_delegates_to_helper() -> None:
    from bioetl.application.core import base_transformer_execution_mixin as mixin

    host = SimpleNamespace()
    with patch.object(mixin, "record_structural_policy_metrics") as record:
        mixin._BaseTransformerExecutionMixin._record_structural_policy_metrics(
            host, action="kept", shadow_comparison="match"
        )
    record.assert_called_once_with(
        host, action="kept", shadow_comparison="match"
    )


# --- lock_lifecycle (58, 87) ---


def _lock_host(**overrides):
    token = SimpleNamespace(sequence=7)
    lock = MagicMock()
    lock.acquire = AsyncMock(return_value=token)
    lock.release = AsyncMock()
    host = SimpleNamespace(
        _lock=lock,
        _config=SimpleNamespace(
            lock_key="key",
            lock_ttl=30,
            wait_for_lock=True,
            wait_timeout=5,
            exclusive=True,
        ),
        _run_id=_run_id("lock"),
        get_context=lambda: SimpleNamespace(lock_key="key"),
        _context_holder=MagicMock(),
        _logger=MagicMock(),
        _heartbeat=None,
        _acquired_at=None,
        _fencing_token=None,
    )
    for key, value in overrides.items():
        setattr(host, key, value)
    return host


async def test_acquire_lock_publishes_context() -> None:
    from bioetl.application.core.lifecycle.lock_lifecycle import acquire_lock

    host = _lock_host()
    token = await acquire_lock(host)
    assert token.sequence == 7
    assert host._context_holder.set.called


async def test_release_lock_clears_context() -> None:
    from bioetl.application.core.lifecycle.lock_lifecycle import release_lock

    host = _lock_host()
    await release_lock(host)
    assert host._context_holder.clear.called
    assert host._logger.info.called


# --- compact_orchestrator (68, 69) ---


async def test_optimize_files_warns_and_continues_on_storage_error() -> None:
    from bioetl.application.core.postrun.compact_orchestrator import (
        PostrunCompactService,
    )

    storage = MagicMock()
    storage.optimize = AsyncMock(side_effect=OSError("disk pressure"))
    logger = MagicMock()
    service = PostrunCompactService(
        config=MagicMock(),
        storage=storage,
        logger=logger,
        warning_allowlist=(OSError,),
    )
    assert await service._optimize_files("silver_table") is None
    logger.warning.assert_called_once()


# --- retention_checks (144, 213) ---


def test_evidence_floor_check_passes_without_strict_profile() -> None:
    from bioetl.application.observability.control_plane_evidence.retention_checks import (
        _evidence_floor_check,
    )

    check = _evidence_floor_check(
        "degraded_observable", protected=False, profile_valid=True, stale=False
    )
    assert check.status == "OK"
    assert check.reason == "reproducibility_evidence_floor_satisfied"


def test_snapshot_evidence_check_passes_without_strict_profile() -> None:
    from bioetl.application.observability.control_plane_evidence.retention_checks import (
        _snapshot_evidence_check,
    )

    check = _snapshot_evidence_check(
        MagicMock(source_refs=[]),
        artifacts=(),
        required_profile="degraded_observable",
        profile_valid=True,
    )
    assert check.status == "OK"
    assert check.reason == "snapshot_evidence_not_required"


# --- target_component_transformer (76, 77) ---


def test_target_component_business_data_extracts_component_id() -> None:
    from bioetl.application.pipelines.chembl.target_component_transformer import (
        TargetComponentTransformer,
    )

    host = SimpleNamespace(
        serialize_json_fields=lambda record, fields: {},
        serialize_json_list=lambda values: None,
    )
    data = TargetComponentTransformer._extract_business_data(host, {}, 7)
    assert data["component_id"] == 7
    assert data["protein_classification_ids"] is None


# --- base_publication_transformer (156, 157) ---


async def test_transform_pre_silver_delegates_to_payload_helpers() -> None:
    from bioetl.application.pipelines.common import (
        base_publication_transformer as publication,
    )

    with (
        patch.object(
            publication, "prepare_publication_payload", return_value={"ready": True}
        ),
        patch.object(
            publication,
            "build_pre_silver_publication_record",
            return_value="pre-silver",
        ) as build,
    ):
        result = await publication.BasePublicationTransformer.transform_pre_silver(
            MagicMock(), MagicMock(), {"title": "paper"}, 0
        )
    assert result == "pre-silver"
    assert build.call_count == 1


# --- diagnostics seam markers (persistence 7/9, persistence_policy 7/9, replay_family 6/8) ---


def test_diagnostics_persistence_seam_exports_nothing() -> None:
    import bioetl.application.services.control_plane.manifest.diagnostics.persistence as seam

    assert seam.__all__ == []


def test_replay_invariants_persistence_policy_seam_exports_nothing() -> None:
    import bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.persistence_policy as seam

    assert seam.__all__ == []


def test_replay_invariants_replay_family_seam_exports_nothing() -> None:
    import bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family as seam

    assert seam.__all__ == []


# --- manifest service (152, 156) ---


def test_assert_manifest_persisted_rejects_unresolvable_run_id() -> None:
    from bioetl.application.services.control_plane.manifest.service import (
        RunManifestService,
    )

    manifest = SimpleNamespace(manifest_id="m-1", run_id="run-1")
    port = SimpleNamespace(
        get=lambda manifest_id: manifest, get_by_run_id=lambda run_id: None
    )
    with pytest.raises(RuntimeError, match="not resolvable by run_id"):
        RunManifestService._assert_manifest_persisted(
            SimpleNamespace(manifest_port=port), manifest
        )


def test_assert_manifest_persisted_rejects_run_id_conflict() -> None:
    from bioetl.application.services.control_plane.manifest.service import (
        RunManifestService,
    )

    manifest = SimpleNamespace(manifest_id="m-1", run_id="run-1")
    port = SimpleNamespace(
        get=lambda manifest_id: manifest,
        get_by_run_id=lambda run_id: SimpleNamespace(
            manifest_id="m-2", run_id="run-1"
        ),
    )
    with pytest.raises(RuntimeError, match="different manifest_id"):
        RunManifestService._assert_manifest_persisted(
            SimpleNamespace(manifest_port=port), manifest
        )


# --- manifest validation (93, 145) ---


def test_strict_replay_provenance_requires_planned_artifacts() -> None:
    from bioetl.application.services.control_plane.manifest.validation import (
        _validate_strict_replay_provenance,
    )
    from bioetl.domain.control_plane import RunCodeProvenance

    request = SimpleNamespace(
        launch_context={"required_persistence_profile": "replay_ready"},
        planned_artifacts=(),
    )
    provenance = RunCodeProvenance(
        contract_ref="contract",
        contract_version="v1",
        contract_schema_hash="hash",
        dq_policy_ref="policy",
        rule_bundle_version="bundle",
        effective_config_artifact_id="artifact",
    )
    with pytest.raises(RuntimeError, match="planned_artifacts"):
        _validate_strict_replay_provenance(request, provenance)


def test_explicit_degraded_opt_down_rejects_exact_replay() -> None:
    from bioetl.application.services.control_plane.manifest.validation import (
        _is_explicit_degraded_profile_opt_down,
    )

    assert (
        _is_explicit_degraded_profile_opt_down(
            SimpleNamespace(launch_context={"exact_replay": True})
        )
        is False
    )
