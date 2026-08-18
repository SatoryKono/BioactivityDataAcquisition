# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
"""Focused fail-closed regressions for #8953 control-plane residuals."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.effective_config.context import (
    build_effective_config_context,
)
from bioetl.application.services.control_plane.effective_config.runtime_overrides import (
    normalize_runtime_overrides_for_semantic_identity,
)
from bioetl.application.services.control_plane.manifest.diagnostics.ledger_processing import (
    _extract_resume_diagnostics,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profile_support import (
    resolve_persistence_inputs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profiles import (
    resolve_required_profile_requirements,
)
from bioetl.application.services.control_plane.manifest.identity_graph_assembly import (
    RunManifestIdentityGraphAssembler,
)
from bioetl.application.services.control_plane.manifest.inspection_dossier import (
    _AUTHORITATIVE_REPLAY_ARTIFACTS,
    _list_payload_values,
    build_authoritative_replay_dossier,
)
from bioetl.application.services.control_plane.manifest.inspection_helpers import (
    build_run_artifact_diff_payload,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (
    json_equal,
)
from bioetl.application.services.control_plane.manifest.models import (
    RunManifestCreateSpec,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    _copy_projection_value,
    resolve_replay_resume_rebuild_verdict,
    resolve_replay_taxonomy_projection,
)
from bioetl.application.services.control_plane.manifest.validation import (
    _is_explicit_degraded_profile_opt_down,
)
from bioetl.application.services.control_plane.manifest.validation_provenance import (
    _validate_executable_code_provenance,
)
from bioetl.application.services.control_plane.replay._historical_certification_support import (
    HistoricalReplayCertificationValidator,
)
from bioetl.application.services.control_plane.replay.closure_claims import (
    build_narrowed_scope_global_claim,
)
from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    resolve_closure_verdict,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationSpec,
    HistoricalReplayCertifiabilityInventory,
    HistoricalReplayCertifiabilityRecord,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_universe_service import (
    HistoricalReplayUniverseExternalRecord,
    HistoricalReplayUniverseService,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_claims import (
    build_historical_replay_universe_exact_replay_claim,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)
from bioetl.application.services.control_plane.workflow.execution_preparation_incremental import (
    _apply_incremental_offset,
)
from bioetl.application.services.control_plane.workflow.execution_recording import (
    WorkflowExecutionRecorder,
    record_workflow_finished,
)
from bioetl.application.services.control_plane.workflow.execution_recording_payloads import (
    build_step_completion_details,
)
from bioetl.application.services.control_plane.workflow.manifest_models import (
    WorkflowManifestCreateSpec,
)
from bioetl.application.services.control_plane.workflow.manifest_service import (
    WorkflowManifestService,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.domain.control_plane import RunCodeProvenance, WorkflowExecutionState
from bioetl.domain.types import RunID, RunType
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from tests.helpers.clock import FIXED_TEST_TIME
from tests.unit.application.services.run_manifest_test_support import make_run_manifest


pytestmark = pytest.mark.unit


def test_stale_settings_snapshot_hash_is_removed_without_runtime_snapshot() -> None:
    normalized = normalize_runtime_overrides_for_semantic_identity(
        {
            "env": {
                "execution_environment": {
                    "settings_snapshot_hash": "sha256:stale-caller-hash",
                }
            }
        }
    )

    assert "settings_snapshot_hash" not in normalized["env"]["execution_environment"]


def test_effective_config_snapshots_are_isolated_from_caller_mutation() -> None:
    resolved_config = {"pipeline": {"limit": 10}}
    runtime_overrides = {"cli": {"limit": 5}}

    context = build_effective_config_context(
        pipeline_name="chembl_activity",
        pipeline_kind="activity",
        resolved_config=resolved_config,
        runtime_overrides=runtime_overrides,
        source_refs=[],
        dq_config=None,
        resolution_policy=None,
        required_persistence_profile="degraded_observable",
        normalization_profile_ref=None,
        normalization_profile_version=None,
        normalization_profile_hash=None,
    )
    resolved_config["pipeline"]["limit"] = 99
    runtime_overrides["cli"]["limit"] = 99

    assert context.resolved_snapshot.config_data["pipeline"]["limit"] == 10
    assert context.overrides_snapshot.cli_overrides["limit"] == 5


def test_pipeline_child_details_require_both_child_identifiers() -> None:
    complete = build_step_completion_details(
        WorkflowStepExecutionResult(
            step_id="extract",
            step_kind="pipeline",
            status="success",
            child_run_id="run-1",
            child_manifest_id="manifest-1",
            payload={"fingerprint": "fp-1"},
        )
    )
    partial = build_step_completion_details(
        WorkflowStepExecutionResult(
            step_id="extract",
            step_kind="pipeline",
            status="success",
            child_run_id="run-1",
        )
    )

    assert complete == {
        "child_run_id": "run-1",
        "child_manifest_id": "manifest-1",
        "fingerprint": "fp-1",
    }
    assert partial is None


def test_workflow_manifest_ignores_nested_input_mutation_after_create() -> None:
    launch_context = {"filters": {"assay_type": "B"}, "limit": 25}
    transform_config = {"mode": "bounded", "keys": ["assay_id"]}
    saved: list[object] = []
    service = WorkflowManifestService(
        manifest_port=SimpleNamespace(save=saved.append),
        created_at_factory=lambda: FIXED_TEST_TIME,
        _manifest_id_factory=lambda: "workflow-manifest-isolated",
    )

    manifest = service.create_manifest(
        WorkflowManifestCreateSpec(
            workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000895")),
            config=WorkflowConfig(
                name="chembl_core",
                steps=(
                    TransformStepConfig(
                        step_id="repair",
                        transform_name="repair_crosswalk",
                        config=transform_config,
                    ),
                ),
            ),
            launch_context=launch_context,
        )
    )
    launch_context["filters"]["assay_type"] = "mutated"
    transform_config["mode"] = "mutated"

    assert manifest.launch_context["filters"]["assay_type"] == "B"
    assert manifest.steps[0].config["mode"] == "bounded"
    assert saved == [manifest]


def test_resume_diagnostics_ignore_messages_only_payloads() -> None:
    entry = SimpleNamespace(
        event_type="checkpoint_evaluated",
        status="ok",
        details={"messages": ["resume hint only"]},
    )

    assert _extract_resume_diagnostics((entry,)) is None


def test_explicit_none_persistence_flags_use_boundary_defaults() -> None:
    inputs = resolve_persistence_inputs(
        base_summary={
            "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
            "replay_family_contract": {
                "execution_context": "source",
                "strict_exact_replay_supported": None,
            },
            "composite_resume_rich_replay_supported": None,
        },
        artifact_refs=[],
        lineage_fragment_ids=set(),
        missing_link_count=0,
    )

    assert inputs.strict_replay_execution_context_supported is True
    assert inputs.composite_resume_rich_replay_supported is True


def test_unknown_required_profile_is_not_silently_degraded() -> None:
    profile, missing = resolve_required_profile_requirements(
        required_profile="not_a_real_profile",
        replay_ready_missing_requirements=[],
        forensic_grade_missing_requirements=[],
    )

    assert profile == "not_a_real_profile"
    assert missing == ["unknown_required_persistence_profile"]


def test_unknown_scoring_profile_fails_thresholds() -> None:
    scoring = build_reproducibility_audit_scoring(
        {"required_persistence_profile": "not_a_real_profile"}
    )

    assert scoring["thresholds_satisfied"] is False
    assert scoring["threshold_failures"] == [
        {
            "category": "required_profile",
            "required": None,
            "actual": "not_a_real_profile",
            "reason": "unknown_required_persistence_profile",
        }
    ]


def test_historical_exact_replay_claim_requires_governed_gate() -> None:
    claim = build_historical_replay_universe_exact_replay_claim(
        summary={
            "historical_replay_universe_claim": {
                "claimed": True,
                "scope": "all_known_historical_runs",
            },
            "historical_replay_universe_durable_evidence_claimed": True,
            "historical_replay_universe_governed_full_corpus_gate": {
                "satisfied": False,
                "verdict": "gate_blocked",
            },
        },
        evidence_refs=[],
    )

    assert claim["claimed"] is False
    assert claim["reason"] == "governed_full_corpus_gate_unsatisfied"


def test_incremental_offset_preserves_distinct_step_offsets() -> None:
    config = WorkflowConfig(
        name="chembl_incremental",
        defaults=WorkflowRunOptionsConfig(start_offset=None),
        steps=(
            WorkflowStepConfig(
                step_id="inherited",
                pipeline_name="chembl_activity",
            ),
            WorkflowStepConfig(
                step_id="explicit",
                pipeline_name="chembl_assay",
                run_options=WorkflowRunOptionsConfig(start_offset=7),
            ),
        ),
    )
    state = WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000896")),
        manifest_id="workflow-manifest-offset",
        workflow_name="chembl_incremental",
        execution_fingerprint="fp",
        status="success",
        started_at=FIXED_TEST_TIME,
        updated_at=FIXED_TEST_TIME,
        completed_at=FIXED_TEST_TIME,
        selected_step_ids=("inherited", "explicit"),
        steps=(),
        completed_transform_fingerprints={},
        last_start_offset=10,
        last_limit=5,
    )

    updated = _apply_incremental_offset(
        config=config,
        workflow_state_port=SimpleNamespace(get_latest=lambda _name: state),
    )

    assert updated.defaults.start_offset == 15
    assert updated.steps[0].run_options.start_offset == 15
    assert updated.steps[1].run_options.start_offset == 7


def test_blocked_manifest_ids_are_unique_and_sorted() -> None:
    claim = build_narrowed_scope_global_claim(
        unresolved_records=(
            SimpleNamespace(manifest_id="m-2"),
            SimpleNamespace(manifest_id="m-1"),
        ),
        narrowed_scope_blockers=("m-1", "m-3"),
    )

    assert claim["blocked_manifest_ids"] == ["m-1", "m-2", "m-3"]


def test_successful_finish_preserves_stored_offsets_when_omitted() -> None:
    saved: list[WorkflowExecutionState] = []
    state = WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000897")),
        manifest_id="manifest-1",
        workflow_name="chembl_baseline",
        execution_fingerprint="fp",
        status="running",
        started_at=FIXED_TEST_TIME,
        updated_at=FIXED_TEST_TIME,
        completed_at=None,
        selected_step_ids=("extract",),
        steps=(),
        completed_transform_fingerprints={},
        last_start_offset=40,
        last_limit=20,
    )
    context = WorkflowExecutionRecorder(
        ledger=SimpleNamespace(
            record_workflow_finished=lambda details: SimpleNamespace(
                occurred_at=FIXED_TEST_TIME,
                entry_id="finished-1",
            )
        ),
        state_port=SimpleNamespace(save=saved.append),
        state=state,
    )

    record_workflow_finished(
        context,
        WorkflowRunExecutionResult(
            workflow_name="chembl_baseline",
            status="success",
            steps=(),
        ),
        completed_at=FIXED_TEST_TIME,
    )

    assert context.state.last_start_offset == 40
    assert context.state.last_limit == 20
    assert saved


def test_query_scoped_certification_does_not_satisfy_other_queries() -> None:
    missing = HistoricalReplayCertificationValidator._find_missing_source_keys(
        expected={
            ("chembl", "activity", "chembl_activity", "q1"),
            ("chembl", "activity", "chembl_activity", "q2"),
        },
        actual={("chembl", "activity", "chembl_activity", "q1")},
    )

    assert missing == [("chembl", "activity", "chembl_activity", "q2")]


def test_unscoped_certification_still_covers_query_specific_expected_keys() -> None:
    missing = HistoricalReplayCertificationValidator._find_missing_source_keys(
        expected={("chembl", "activity", "chembl_activity", "q1")},
        actual={("chembl", "activity", "chembl_activity", None)},
    )

    assert missing == []


def test_ambiguous_certification_query_raises() -> None:
    validator = HistoricalReplayCertificationValidator(
        manifest_port=SimpleNamespace(),
        ledger_port=SimpleNamespace(),
    )
    manifest = make_run_manifest()
    manifest = SimpleNamespace(
        source_refs=(
            SimpleNamespace(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="q1",
            ),
            SimpleNamespace(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="q2",
            ),
        )
    )

    with pytest.raises(ValueError, match="ambiguous"):
        validator.resolve_certification_query(
            manifest=manifest,
            certification=SimpleNamespace(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query=None,
            ),
        )


def test_empty_inventory_is_not_fully_closed() -> None:
    verdict = resolve_closure_verdict(
        inventory=HistoricalReplayCertifiabilityInventory(records=()),
        unresolved_records=(),
        disposition_map={},
        claim_scope_mode="all_retained_historical_runs",
    )

    assert verdict == (
        "no_retained_historical_runs",
        "inventory_contains_no_retained_historical_runs",
    )


def test_authoritative_artifacts_and_list_payloads_are_copied() -> None:
    diagnostics = {
        "artifact_refs": [{"stage": "bronze", "artifact_id": "a1"}],
        "input_snapshot_ids": ["snap-1"],
    }
    dossier = build_authoritative_replay_dossier(
        manifest=make_run_manifest(),
        diagnostics=diagnostics,
        identity_graph={},
    )
    dossier["authoritative_replay_artifacts"].append("mutated")
    dossier["input_snapshot_ids"].append("mutated")
    _list_payload_values(diagnostics, "input_snapshot_ids").append("aliased")

    assert "mutated" not in _AUTHORITATIVE_REPLAY_ARTIFACTS
    assert diagnostics["input_snapshot_ids"] == ["snap-1"]


def test_json_equal_preserves_timezone_awareness() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    assert json_equal({"a": 1}, {"a": 1}) is True
    assert json_equal(naive, aware) is False
    assert json_equal(naive, "2026-01-01 12:00:00") is False


def test_strict_code_provenance_normalizes_profile_aliases() -> None:
    request = RunManifestCreateSpec(
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000898")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"required_persistence_profile": "replay-ready"},
        runtime_config={},
        resolved_config={},
    )
    dirty = RunCodeProvenance(
        git_commit="abc123",
        source_revision_state="dirty",
        dependency_lock_hash="lock",
        resolved_config_hash="b" * 64,
        effective_config_hash="c" * 64,
    )

    with pytest.raises(RuntimeError, match="clean source_revision_state"):
        _validate_executable_code_provenance(request, dirty)


def test_identity_graph_build_does_not_mutate_caller_diagnostics() -> None:
    published = {"stage": "bronze", "artifact_id": "a1"}
    diagnostics = {
        "identity_graph": {"canonical_execution_identity": {"fingerprint": "fp"}},
        "artifact_refs": [published],
    }

    graph = RunManifestIdentityGraphAssembler.build(make_run_manifest(), diagnostics)
    graph["published_artifacts"][0]["stage"] = "mutated"
    graph["extra"] = True

    assert "published_artifacts" not in diagnostics["identity_graph"]
    assert published["stage"] == "bronze"


def test_artifact_refs_available_is_always_boolean() -> None:
    empty = build_run_artifact_diff_payload(
        left_manifest=make_run_manifest(),
        right_manifest=make_run_manifest(),
    )
    present = build_run_artifact_diff_payload(
        left_manifest=make_run_manifest(),
        right_manifest=make_run_manifest(),
        left_artifact_refs=({"stage": "bronze", "artifact_id": "a1"},),
    )

    assert empty["artifact_refs_available"] is False
    assert present["artifact_refs_available"] is True


def test_missing_anchors_degrade_only_resume_capable_runs() -> None:
    resume = resolve_replay_resume_rebuild_verdict(
        replay_capability="resume_only",
        replay_mode="resume",
        continuation_mode="checkpoint_snapshot_only_resume",
        replay_readiness_verdict="resume_only_ready",
        missing_anchors=["execution_fingerprint"],
    )
    rebuild = resolve_replay_resume_rebuild_verdict(
        replay_capability="rebuild_only",
        replay_mode="rebuild",
        continuation_mode="full_scan_idempotent_rebuild",
        replay_readiness_verdict="rebuild_only",
        missing_anchors=["execution_fingerprint"],
    )

    assert resume == "resume_only_degraded"
    assert rebuild == "rebuild_only"


def test_production_context_cannot_opt_down_to_degraded() -> None:
    request = RunManifestCreateSpec(
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000899")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={
            "env": "production",
            "required_persistence_profile_opt_down": True,
            "configured_required_persistence_profile": "degraded_observable",
            "required_persistence_profile": "degraded_observable",
        },
        runtime_config={},
        resolved_config={},
    )

    assert _is_explicit_degraded_profile_opt_down(request) is False


def test_list_projection_normalizes_sets_and_rejects_scalars() -> None:
    projection = resolve_replay_taxonomy_projection(
        {"exact_replay_blockers": {"b", "a"}}
    )

    assert projection["exact_replay_blockers"] == ["a", "b"]
    with pytest.raises(TypeError, match="exact_replay_blockers"):
        _copy_projection_value("exact_replay_blockers", "not-a-list")


def test_bulk_certification_skips_needs_operator_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = make_run_manifest(manifest_id="review-manifest")
    inventory_record = HistoricalReplayCertifiabilityRecord(
        manifest_id=manifest.manifest_id,
        run_id=str(manifest.run_id),
        pipeline_name=manifest.pipeline_name,
        provider=manifest.provider,
        entity=manifest.entity,
        execution_context="source",
        family="chembl.activity",
        certification_scope="historical_source_replay",
        certification_status="needs_operator_review",
        replay_occurrence_kind="ordinary_live_capture",
        broader_historical_exact_replay_policy=(
            "certified_historical_exact_replay_tranche_supported"
        ),
        broader_historical_exact_replay_boundary="historical_source_snapshot_certification",
        broader_historical_exact_replay_state="unknown",
        blocking_reasons=("replay_certifiability_state_requires_review",),
    )
    service = HistoricalReplayCorpusService(
        manifest_port=SimpleNamespace(list_all=lambda: (manifest,)),
        ledger_port=SimpleNamespace(),
        certification_service=SimpleNamespace(),
    )
    monkeypatch.setattr(
        HistoricalReplayCorpusService,
        "build_certifiability_inventory",
        lambda _self: SimpleNamespace(records=(inventory_record,)),
    )

    result = service.certify_retained_corpus(
        specs=(
            HistoricalReplayBulkCertificationSpec(
                manifest_id="review-manifest",
                certifications=(),
            ),
        )
    )

    assert result.records[0].status == "skipped_needs_operator_review"
    assert result.completed_count == 0


def test_universe_inventory_prefers_local_record_on_duplicate_manifest_id() -> None:
    local_record = SimpleNamespace(
        manifest_id="shared-manifest",
        run_id="local-run",
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        execution_context="source",
        certification_status="already_certified",
        replay_occurrence_kind="historical_source_replay_certified_parent",
        blocking_reasons=(),
    )
    service = HistoricalReplayUniverseService(
        corpus_service=SimpleNamespace(
            build_certifiability_inventory=lambda: SimpleNamespace(
                records=(local_record,)
            )
        ),
        now_factory=lambda: FIXED_TEST_TIME,
    )

    inventory = service.build_universe_inventory(
        external_records=(
            HistoricalReplayUniverseExternalRecord(
                manifest_id="shared-manifest",
                run_id="archived-run",
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                execution_context="source",
                certification_status="awaiting_source_snapshot_certification",
                replay_occurrence_kind="ordinary_live_capture",
                blocking_reasons=("archive_snapshot_missing",),
            ),
        )
    )

    assert inventory.manifest_count == 1
    assert inventory.records[0].universe_origin == "local_retained"
    assert inventory.records[0].run_id == "local-run"
