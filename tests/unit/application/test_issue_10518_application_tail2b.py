"""Behavior-focused unit tests closing application-layer residuals for #10518.

Covers small missing-line residuals measured against ``tests/unit/application``
(batch tail2b: run-report snapshots through workflow transform primitives).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit


# --- run_reports snapshots (31, 32) ---


class _DictReportStore:
    """In-memory RunReportStorePort double keyed by path string."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def is_file(self, path: str) -> bool:
        return path in self.files

    def read_text(self, path: str) -> str:
        return self.files[path]

    def mkdir(self, path: str) -> None:
        return None

    def write_text(self, path: str, content: str) -> None:
        self.files[path] = content


def test_publish_snapshot_is_idempotent_for_identical_report() -> None:
    from bioetl.application.services.run_reports.snapshots import publish_snapshot

    store = _DictReportStore()
    path = Path("reports/status.json")
    first = publish_snapshot({"run": "a"}, path, store=store)
    second = publish_snapshot({"run": "a"}, path, store=store)
    assert second["selected_run_snapshot"] == first["selected_run_snapshot"]


def test_publish_snapshot_rejects_conflicting_revision() -> None:
    from bioetl.application.services.run_reports.snapshots import publish_snapshot
    from bioetl.domain.run_reports.selected_status import build_snapshot

    store = _DictReportStore()
    path = Path("reports/status.json")
    publish_snapshot({"run": "a"}, path, store=store)
    revision = build_snapshot(
        {**{"run": "a"}, "schema_version": "pipeline_run_report_v2"}
    )["revision"]
    store.files[f"reports/status-revisions/{revision}.json"] = "tampered"
    with pytest.raises(ValueError, match="revision conflict"):
        publish_snapshot({"run": "a"}, path, store=store)


# --- _preflight_reporting (40) ---


def test_log_profile_loading_summary_emits_debug() -> None:
    from bioetl.application.composite._preflight_reporting import (
        PreflightValidationReportingMixin,
    )
    from bioetl.application.composite._preflight_types import ProfileInfo

    host = PreflightValidationReportingMixin.__new__(PreflightValidationReportingMixin)
    host._logger = MagicMock()
    host._log_profile_loading_summary(
        {
            "chembl": ProfileInfo(
                source="chembl",
                profile_name="default",
                profile_version="v1",
                profile_hash="hash",
                field_hashes={},
            )
        }
    )
    assert host._logger.debug.called


# --- column_renamer (207) ---


def test_is_system_column_matches_identity_columns() -> None:
    from bioetl.application.composite.column_renamer import ColumnRenamer

    renamer = ColumnRenamer(logger=MagicMock())
    assert renamer._is_system_column("entity_id") is True
    assert renamer._is_system_column("title") is False


# --- runtime_models (101) ---


def test_composite_runtime_config_normalizes_enrich_only() -> None:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig

    assert CompositeRuntimeConfig(
        enrich_only=["chembl_activity"]  # type: ignore[list-item]
    ).enrich_only == ("chembl_activity",)


# --- batch_writer (171) ---


def test_track_batch_failed_delegates_to_metrics() -> None:
    from bioetl.application.core.batch_writer import BatchWriter

    writer = BatchWriter.__new__(BatchWriter)
    writer._batch_metrics = MagicMock()
    writer.track_batch_failed(stage="silver", count=2)
    writer._batch_metrics.track_batch_failed.assert_called_once_with(
        stage="silver", count=2
    )


# --- pipeline_services (141) ---


async def test_aclose_closes_metadata_writer() -> None:
    from bioetl.application.core.pipeline_services import PipelineService

    service = PipelineService(
        data_source=MagicMock(aclose=AsyncMock()),
        storage=MagicMock(aclose=AsyncMock()),
        lock=MagicMock(aclose=AsyncMock()),
        checkpoint=MagicMock(aclose=AsyncMock()),
        quarantine=MagicMock(aclose=AsyncMock()),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=MagicMock(),
        metadata_writer=MagicMock(aclose=AsyncMock()),
    )
    await service.aclose()
    assert service.metadata_writer.aclose.called


# --- _phase_descriptions (99) ---


def test_describe_compaction_phase_records_error_attribute() -> None:
    from bioetl.application.core.postrun._phase_descriptions import (
        describe_compaction_phase,
    )
    from bioetl.application.core.postrun.compact_orchestrator import CompactionResult

    phase = describe_compaction_phase(
        CompactionResult(status="failed", error="disk pressure")
    )
    assert phase.span_attributes["bioetl.compaction_error"] == "disk pressure"
    assert phase.level == "warning"


# --- metadata_write_service (70) ---


async def test_write_final_metadata_returns_false_without_coroutines() -> None:
    from bioetl.application.core.postrun.metadata_write_service import (
        PostrunMetadataWriteService,
    )

    service = PostrunMetadataWriteService.__new__(PostrunMetadataWriteService)
    service._metadata_writer = MagicMock()
    service._build_write_coroutines = lambda **kwargs: []
    assert (
        await service.write_final_metadata_if_available(
            executor=MagicMock(), dq_reports=None
        )
        is False
    )


# --- pre_silver_finalization_flow (217) ---


def test_transform_optional_business_data_returns_none_when_absent() -> None:
    from bioetl.application.core.pre_silver_finalization_flow import (
        _PreSilverFinalizationFlowMixin,
    )

    assert (
        _PreSilverFinalizationFlowMixin._transform_optional_normalized_business_data(
            MagicMock(),
            context=MagicMock(),
            index=0,
            business_data=None,
            resolve_entity_id=lambda data: "entity-1",
        )
        is None
    )


# --- pre_silver_staging_flow (124) ---


def test_stage_optional_business_data_returns_none_when_absent() -> None:
    from bioetl.application.core.pre_silver_staging_flow import (
        _PreSilverStagingFlowMixin,
    )

    assert (
        _PreSilverStagingFlowMixin._stage_optional_normalized_business_data(
            MagicMock(),
            business_data=None,
            resolve_entity_id=lambda data: "entity-1",
        )
        is None
    )


# --- runner_flow_metrics (186) ---


def test_monotonic_invariant_status_unknown_when_unobserved() -> None:
    from bioetl.application.core.runner_flow_metrics import (
        _monotonic_invariant_status,
    )

    assert _monotonic_invariant_status(upper=1, lower=2, observed=False) == "unknown"
    assert _monotonic_invariant_status(upper=2, lower=1, observed=True) == "passed"


# --- service_support (70) ---


def test_source_error_payload_reports_read_failure() -> None:
    from bioetl.application.observability.control_plane_evidence.service_support import (
        EvidenceScopeContext,
        source_error_payload,
    )

    scope = EvidenceScopeContext(
        requested_pipeline="chembl_activity",
        selected_run_id=None,
        selected_run_types=(),
        resolved_via="selector",
        manifest=None,
    )
    payload = source_error_payload(
        endpoint="evidence", scope=scope, reason="read_failed", check="snapshot"
    )
    assert payload["trust_status"] == "ERROR"
    assert payload["rows"][0]["reason"] == "read_failed"


# --- reason_aliases (28) ---


def test_display_reason_returns_blank_code_unchanged() -> None:
    from bioetl.application.observability.reason_aliases import display_reason

    assert display_reason("   ") == "   "
    assert display_reason("archive_restore_verified") == "Archive verified"


# --- molecule_transformer (232) ---


def test_molecule_business_data_tags_alogp_method() -> None:
    from bioetl.application.pipelines.chembl.molecule_transformer import (
        MoleculeTransformer,
    )

    host = SimpleNamespace(
        validate_value_object=lambda cls, value: value,
        serialize_json_fields=lambda record, fields: {},
    )
    data = MoleculeTransformer._extract_business_data(
        host, {"molecule_properties": {"alogp": 2.5}}, "CHEMBL25"
    )
    assert data["molecule_id"] == "CHEMBL25"
    assert data["logp_method"] == "alogp"


# --- _compound_business_data (64) ---


def test_resolve_compound_identifier_prefers_cid() -> None:
    from bioetl.application.pipelines.pubchem._compound_business_data import (
        _resolve_compound_identifier,
    )

    assert _resolve_compound_identifier({"cid": 2244}) == 2244
    assert _resolve_compound_identifier({"molecule_id": "CID2244"}) == "CID2244"
    assert _resolve_compound_identifier({}) is None


# --- idmapping_transformer (113) ---


def test_mapping_business_data_flags_multiple_mappings() -> None:
    from bioetl.application.pipelines.uniprot.idmapping_transformer import (
        IDMappingTransformer,
    )

    host = SimpleNamespace(_get_required_field=lambda record, name: "P12345")
    _, business_data = IDMappingTransformer._build_mapping_business_data(
        host,
        {
            "target_id": "P12345",
            "uniprot_accession": "P12345",
            "all_mappings": [{"accession": "P12345"}],
        },
    )
    assert business_data["mapping_status"] == "multiple"


# --- effective_config context (93) ---


def test_resolve_resolution_policy_returns_explicit_policy() -> None:
    from bioetl.application.services.control_plane.effective_config.context import (
        resolve_resolution_policy,
    )
    from bioetl.domain.control_plane.effective_config_artifact import (
        ConfigResolutionPolicy,
    )

    policy = ConfigResolutionPolicy()
    assert resolve_resolution_policy(policy) is policy
    assert isinstance(resolve_resolution_policy(None), ConfigResolutionPolicy)


# --- persistence_profile_support (114) ---


def test_forensic_missing_requirements_flags_closure_boundary() -> None:
    from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profile_support import (
        build_forensic_grade_missing_requirements,
    )

    assert build_forensic_grade_missing_requirements(
        replay_ready_missing_requirements=[],
        ledger_entries_present=True,
        artifact_lineage_links_complete=True,
        lineage_closure_boundary_supported=False,
        composite_resume_rich_replay_supported=True,
    ) == ["lineage_closure_boundary_support"]


# --- persistence_profiles (63) ---


def test_resolve_required_profile_requirements_for_forensic_grade() -> None:
    from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profiles import (
        resolve_required_profile_requirements,
    )

    assert resolve_required_profile_requirements(
        required_profile="forensic_grade",
        replay_ready_missing_requirements=[],
        forensic_grade_missing_requirements=["run_ledger_history"],
    ) == ("forensic_grade", ["run_ledger_history"])


# --- bundle_descriptor_service (45) ---


def test_replay_bundle_descriptor_payload() -> None:
    from bioetl.application.services.control_plane.replay.bundle_descriptor_service import (
        RunReplayBundleDescriptorRecord,
    )

    payload = RunReplayBundleDescriptorRecord(
        manifest_id="m-1",
        run_id="run-1",
        execution_fingerprint="fingerprint",
        replay_capability="exact",
        exact_replay_eligible=True,
        replay_readiness_verdict="ready",
        exact_replay_support_boundary=None,
        replay_family_contract="family",
        required_persistence_profile="replay_ready",
        bundle={"steps": []},
    ).to_dict()
    assert payload["manifest_id"] == "m-1"
    assert payload["missing_requirements"] == []
    assert payload["bundle"] == {"steps": []}


# --- _checks_business (102) ---


def test_normalize_business_rule_returns_typed_spec() -> None:
    from bioetl.application.services.dq._checks_business import (
        _normalize_business_rule,
    )
    from bioetl.domain.types.gold_contracts_rules import GoldBusinessRuleSpec

    rule = GoldBusinessRuleSpec(column="status", condition="not_null")
    assert _normalize_business_rule(rule, contract_version=None) is rule


# --- _metadata_coordinator_helpers (85) ---


def test_merge_input_snapshots_dedupes_repeated_identities() -> None:
    from bioetl.application.services.lineage._metadata_coordinator_helpers import (
        _merge_input_snapshots,
    )
    from bioetl.domain.models._metadata_bronze import InputSnapshotRef

    snapshot = InputSnapshotRef(snapshot_id="s-1", content_hash="hash-1")
    merged = _merge_input_snapshots(source=None, input_snapshots=(snapshot, snapshot))
    assert merged == [snapshot]


# --- metadata_lineage_dataset_nodes (44) ---


def test_canonical_bronze_batch_node_skips_reserved_and_empty_extras() -> None:
    from bioetl.application.services.lineage.metadata_lineage_dataset_nodes import (
        _canonical_bronze_batch_node,
    )

    node = _canonical_bronze_batch_node(
        batch_id="batch-1",
        provider="chembl",
        entity="activity",
        extra={"batch_id": "other", "empty": None, "path": "/data"},
    )
    assert node.attributes["batch_id"] == "batch-1"
    assert "empty" not in node.attributes
    assert node.attributes["path"] == "/data"


# --- medallion_lifecycle (309) ---


async def test_optimize_tables_skips_second_vacuum_for_shared_table() -> None:
    from bioetl.application.services.medallion.medallion_lifecycle import (
        MedallionLifecycleService,
    )

    storage = MagicMock()
    storage.vacuum = AsyncMock(return_value=4)
    service = MedallionLifecycleService(storage=storage, logger=MagicMock())
    assert await service._optimize_tables("table", "table", 24, False) == (4, 0)
    assert storage.vacuum.call_count == 1


# --- dq_report_generation_mixin (109) ---


def test_emit_dq_check_failure_metric_skips_without_metrics() -> None:
    from bioetl.application.services.quality.dq_report_generation_mixin import (
        DQReportGenerationMixin,
    )

    host = DQReportGenerationMixin.__new__(DQReportGenerationMixin)
    host._metrics = None
    assert (
        host._emit_dq_check_failure_metric(
            pipeline="chembl_activity",
            stage="silver",
            check_type="not_null",
            severity="error",
        )
        is None
    )


# --- workflow_runner_models (50) ---


def test_workflow_run_result_success_reflects_status() -> None:
    from bioetl.application.services.workflow.workflow_runner_models import (
        WorkflowRunExecutionResult,
    )

    assert (
        WorkflowRunExecutionResult(
            workflow_name="w", status="success", steps=()
        ).is_success
        is True
    )
    assert (
        WorkflowRunExecutionResult(
            workflow_name="w", status="failed", steps=()
        ).is_success
        is False
    )


# --- workflow_transform_service (129) ---


async def test_run_step_awaits_async_transform_executor() -> None:
    from bioetl.application.services.workflow.workflow_transform_service import (
        WorkflowTransformService,
    )
    from bioetl.application.workflow.transforms import WorkflowTransformRegistry
    from bioetl.domain.workflow import TransformStepConfig

    async def _executor(spec, upstream_outputs):
        return {"rows": 3}

    registry = WorkflowTransformRegistry()
    registry.register("pass_through", _executor)
    service = WorkflowTransformService(registry=registry, metrics=MagicMock())
    result = await service.run_step(
        workflow_name="nightly",
        step=TransformStepConfig(step_id="step-1", transform_name="pass_through"),
    )
    assert result.status == "success"
    assert result.step_id == "step-1"


# --- workflow transforms __init__ (58) ---


def test_record_destructive_commit_without_callback_is_noop() -> None:
    from bioetl.application.workflow.transforms import (
        WorkflowTransformRuntimeContext,
    )

    assert (
        WorkflowTransformRuntimeContext().record_destructive_commit(
            step_id="step-1",
            transform_name="pass_through",
            fingerprint="fingerprint",
            details={},
        )
        is None
    )


def test_record_destructive_commit_invokes_callback() -> None:
    from bioetl.application.workflow.transforms import (
        WorkflowTransformRuntimeContext,
    )

    seen: list = []
    context = WorkflowTransformRuntimeContext(destructive_commit_callback=seen.append)
    context.record_destructive_commit(
        step_id="step-1",
        transform_name="pass_through",
        fingerprint="fingerprint",
        details={},
    )
    assert seen[0].step_id == "step-1"
    assert seen[0].fingerprint == "fingerprint"


# --- cross-file: workflow ledger RunID sanity ---


def test_workflow_run_id_type_roundtrip() -> None:
    from bioetl.domain.types import RunID

    run_id = RunID(UUID("33333333-3333-3333-3333-333333333333"))
    assert str(run_id) == "33333333-3333-3333-3333-333333333333"
