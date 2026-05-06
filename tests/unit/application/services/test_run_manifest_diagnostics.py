"""Unit tests for run-manifest diagnostics summary helpers."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.types import RunID
from tests.helpers.control_plane import InMemoryRunLedgerStore
from tests.unit.application.services.run_manifest_test_support import (
    VALID_CONFIG_HASH as _VALID_CONFIG_HASH,
    VALID_EFFECTIVE_CONFIG_HASH as _VALID_EFFECTIVE_CONFIG_HASH,
    VALID_RESOLVED_CONFIG_HASH as _VALID_RESOLVED_CONFIG_HASH,
    RunManifestOverrides,
    build_published_silver_artifact,
    build_source_refs,
    expected_canonical_execution_identity as _expected_canonical_execution_identity,
    expected_degraded_runtime_anchor as _expected_degraded_runtime_anchor,
    expected_exact_replay_anchors as _expected_exact_replay_anchors,
    expected_lineage_closure_boundary as _expected_lineage_closure_boundary,
    expected_produced_artifact_trace as _shared_expected_produced_artifact_trace,
    expected_replay_family_contract as _expected_replay_family_contract,
    expected_replay_parentage as _expected_replay_parentage,
    expected_resume_contract as _expected_resume_contract,
    make_run_manifest as _build_manifest,
)


_InMemoryRunLedgerStore = InMemoryRunLedgerStore


def _make_manifest() -> RunManifest:
    return _build_manifest(
        manifest_id="manifest-diagnostics",
        execution_fingerprint="fingerprint-diagnostics",
        run_id=RunID(uuid4()),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )


def _expected_missing_produced_artifact_trace(
    manifest: RunManifest,
) -> dict[str, object]:
    return _shared_expected_produced_artifact_trace(
        manifest,
        ledger_entries_present=False,
    )


def _expected_produced_artifact_trace(manifest: RunManifest) -> dict[str, object]:
    return _shared_expected_produced_artifact_trace(
        manifest,
        ledger_entries_present=True,
        artifacts=[
            build_published_silver_artifact(
                artifact_path="data/output/silver/chembl/activity",
            )
        ],
    )


def _build_ledger_entries(
    manifest: RunManifest,
    *,
    terminal_status: str,
) -> tuple[RunLedgerEntry, ...]:
    store = _InMemoryRunLedgerStore()
    entry_counter = {"value": 0}

    def _entry_id_factory() -> str:
        entry_counter["value"] += 1
        return f"entry-{entry_counter['value']}"

    service = RunLedgerService(
        ledger_port=store,
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        _entry_id_factory=_entry_id_factory,
    )
    service.record_manifest_created(manifest)
    service.record_run_started()
    service.record_stage_completed(
        stage="execute_pipeline",
        metrics_snapshot={"records_bronze": 5},
        details={"result": "ok"},
    )
    service.record_artifact_published(
        layer="silver",
        artifact_path="data/output/silver/chembl/activity",
        dataset_ref="silver:chembl.activity@1",
        lineage_fragment_id="silver:fragment-1",
    )
    if terminal_status == "success":
        service.record_run_finished(metrics_snapshot={"records_silver": 5})
    elif terminal_status == "failed":
        service.record_run_failed(
            message="boom",
            error_type="RuntimeError",
            metrics_snapshot={"records_silver": 3},
        )
    elif terminal_status == "shutdown":
        service.record_run_shutdown(metrics_snapshot={"records_silver": 2})
    else:
        raise AssertionError(f"unsupported terminal status {terminal_status!r}")
    return tuple(store.items)


def _assert_provenance_only_score(
    summary: dict[str, object], manifest: RunManifest
) -> None:
    score = summary["reproducibility_audit_score"]
    assert score["schema_version"] == "2.0"
    assert score["contract_version"] == "1.2.0"
    assert score["scale"] == "0-10"
    assert score["required_profile"] == "degraded_observable"
    assert score["score_scope"] == "supported_boundary_run"
    assert score["overall_score"] == pytest.approx(7.3)
    assert score["thresholds"] == {}
    assert score["threshold_failures"] == []
    assert score["thresholds_satisfied"] is True
    assert score["scored_at"] == manifest.created_at.isoformat()
    assert score["source"] == "run_manifest_diagnostics"
    assert score["supported_boundary_verdict"]["scope"] == "supported_boundary_run"
    assert score["supported_boundary_verdict"]["verdict"] == (
        "supported_boundary_gaps_present"
    )
    assert score["supported_boundary_verdict"]["supported_boundary_satisfied"] is (
        False
    )
    assert score["global_reproducibility_claim"]["claimed"] is False
    assert score["global_reproducibility_claim"]["verdict"] == (
        "universal_exact_replay_not_claimed"
    )
    assert score["blockers"] == [
        "dependency_lock_hash_missing",
        "exact_replay_not_eligible",
        "identity_graph_incomplete",
        "immutable_input_snapshots_missing",
        "missing_immutable_input_snapshots",
    ]
    assert "diagnostics.git_commit" in score["evidence_refs"]
    assert "diagnostics.source_revision_state" in score["evidence_refs"]
    assert score["category_scores"]["run_identity"] == {
        "score": 9,
        "evidence": [
            "manifest_id_present",
            "execution_fingerprint_present",
            "resolved_config_hash_present",
            "effective_config_hash_present",
            "effective_config_artifact_id_present",
            "contract_ref_present",
            "git_commit_present",
            "source_revision_state_present",
            "dependency_lock_hash_missing",
        ],
        "blockers": ["dependency_lock_hash_missing"],
        "evidence_refs": [
            "diagnostics.manifest_id",
            "diagnostics.execution_fingerprint",
            "diagnostics.resolved_config_hash",
            "diagnostics.effective_config_hash",
            "diagnostics.effective_config_artifact_id",
            "diagnostics.contract_ref",
            "diagnostics.git_commit",
            "diagnostics.source_revision_state",
            "diagnostics.dependency_lock_hash",
        ],
        "confidence": "high",
    }


def _expected_provenance_only_summary_without_score(
    manifest: RunManifest,
) -> dict[str, object]:
    return {
        "manifest_id": "manifest-diagnostics",
        "manifest_created_at": manifest.created_at.isoformat(),
        "run_id": str(manifest.run_id),
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "execution_fingerprint": "fingerprint-diagnostics",
        "config_hash": _VALID_CONFIG_HASH,
        "resolved_config_hash": _VALID_RESOLVED_CONFIG_HASH,
        "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        "pipeline_version": "1.0.0",
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "dependency_lock_state": "missing",
        "code_provenance_state": {
            "git_commit": "abc1234",
            "source_revision_state": "clean",
            "dependency_lock_state": "missing",
            "strict_code_provenance_ready": False,
            "strict_code_provenance_blockers": ["dependency_lock_hash_missing"],
        },
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "dq_policy_ref": "chembl_activity.gold",
        "rule_bundle_version": "2026.03",
        "dq_contract_compatibility_hash": "compat-hash-1",
        "effective_config_artifact_id": "eca-123",
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "replay_capability": "rebuild_only",
        "required_persistence_profile": "degraded_observable",
        "requested_exact_replay": False,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_capability_reason": "immutable_input_snapshots_missing",
        "exact_replay_eligible": False,
        "exact_replay_blockers": ["immutable_input_snapshots_missing"],
        "replay_readiness_verdict": "incremental_new_run",
        "append_mode_semantic_sinks": [],
        "input_snapshot_ids": [],
        "input_snapshot_content_hashes": [],
        "input_snapshot_identity_fingerprint": None,
        "replay_mode": "rebuild",
        "operator_replay_mode": "Incremental New Run",
        "snapshot_status": "none",
        "continuation_mode": "rebuild_only",
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        "input_snapshot_count": 0,
        "input_snapshots": [],
        "planned_artifacts": [],
        "occurrence_only_diagnostics": [],
        "artifact_refs": [],
        "lineage_fragment_ids": [],
        "published_artifact_count": 0,
        "exact_replay_anchors": _expected_exact_replay_anchors(manifest),
        "produced_artifact_trace": _expected_missing_produced_artifact_trace(manifest),
        "persistence_profile": {
            "attained_profile": "degraded_observable",
            "required_profile": "degraded_observable",
            "required_profile_satisfied": True,
            "claims": {
                "degraded_observable": True,
                "replay_ready": False,
                "forensic_grade": False,
            },
            "surfaces": {
                "control_plane_manifest": True,
                "dependency_lock_provenance": False,
                "effective_config_artifact": True,
                "reproducible_semantic_output_mode": True,
                "strict_replay_execution_context_support": True,
                "immutable_input_snapshots": False,
                "exact_replay_capability": False,
                "produced_artifact_trace": False,
                "run_ledger_history": False,
                "artifact_lineage_links": True,
                "lineage_closure_boundary_support": True,
            },
            "required_profile_missing_requirements": [],
            "replay_ready_missing_requirements": [
                "exact_replay_capability",
                "dependency_lock_provenance",
                "immutable_input_snapshots",
                "produced_artifact_trace",
            ],
            "forensic_grade_missing_requirements": [
                "exact_replay_capability",
                "dependency_lock_provenance",
                "immutable_input_snapshots",
                "produced_artifact_trace",
                "run_ledger_history",
            ],
            "composite_resume_reconstructability": {
                "scope": "coarse_grained_composite_resume",
                "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
                "reconstructs": [
                    "state",
                    "seed_completed",
                    "merge_completed",
                    "last_event_id",
                    "last_event_occurred_at",
                ],
                "does_not_reconstruct": [
                    "per_provider_result_maps",
                    "rich_checkpoint_payloads",
                ],
                "forensic_grade_supported": True,
            },
            "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        },
        "alert_signals": {
            "run_failed": False,
            "run_shutdown": False,
            "artifact_linkage_gap": False,
            "lineage_gap": False,
            "immutable_input_snapshot_gap": True,
            "strict_replay_boundary_gap": False,
            "reproducible_semantic_output_mode_gap": False,
            "produced_artifact_trace_gap": True,
            "lineage_closure_boundary_gap": False,
            "composite_resume_reconstructability_gap": False,
            "required_persistence_profile_gap": False,
            "replay_ready_gap": True,
            "forensic_grade_gap": True,
            "dq_signal_present": False,
            "cross_validation_signal_present": False,
        },
        "next_steps": [
            "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
            "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
            "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
            "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        ],
    }


def _assert_provenance_only_policy(
    summary: dict[str, object], manifest: RunManifest
) -> None:
    assert summary["replay_capability_assessment"] == {
        "required_persistence_profile": "degraded_observable",
        "replay_capability": "rebuild_only",
        "strict_requirement_requested": False,
        "strict_exact_replay_supported": True,
        "replay_readiness_verdict": "incremental_new_run",
        "required_profile_satisfied": True,
        "blocking_gaps": [],
        "snapshot_envelope": {
            "source_count": 0,
            "sources_with_snapshots": 0,
            "any_input_snapshots": False,
            "full_snapshot_envelope": False,
            "require_full_snapshot_envelope": False,
        },
    }
    assert (
        summary["reproducibility_diagnostics"]["policy"]["required_persistence_profile"]
        == "degraded_observable"
    )
    assert (
        summary["reproducibility_diagnostics"]["policy"]["capability_assessment"]
        == summary["replay_capability_assessment"]
    )
    assert (
        summary["reproducibility_diagnostics"]["semantic_identity"][
            "execution_fingerprint"
        ]
        == manifest.execution_fingerprint
    )
    effective_config_diag = summary["reproducibility_diagnostics"]["effective_config"]
    assert effective_config_diag["semantic"]["legacy_config_hash"] == _VALID_CONFIG_HASH
    assert (
        effective_config_diag["semantic"]["legacy_config_hash_alias_of"]
        == "resolved_config_hash"
    )
    assert effective_config_diag["semantic"]["effective_config_hash"] == (
        _VALID_EFFECTIVE_CONFIG_HASH
    )
    assert effective_config_diag["occurrence"]["run_id"] == str(manifest.run_id)
    assert effective_config_diag["diff_policy"]["occurrence_fields"] == [
        "run_id",
        "manifest_id",
        "manifest_created_at",
    ]
    assert (
        effective_config_diag["diff_policy"]["legacy_config_hash_display_only"] is True
    )
    assert (
        effective_config_diag["diff_policy"][
            "legacy_config_hash_replay_identity_anchor"
        ]
        is False
    )


def test_build_diagnostics_summary_without_ledger_returns_provenance_only() -> None:
    manifest = _make_manifest()

    summary = build_diagnostics_summary(manifest, ())

    _assert_provenance_only_score(summary, manifest)
    _assert_provenance_only_policy(summary, manifest)

    summary_without_score = {
        key: value
        for key, value in summary.items()
        if key
        not in {
            "reproducibility_audit_score",
            "reproducibility_diagnostics",
            "replay_capability_assessment",
        }
    }
    assert summary_without_score == _expected_provenance_only_summary_without_score(
        manifest
    )


def test_build_diagnostics_summary_classifies_dependency_lock_provenance() -> None:
    manifest = _build_manifest(
        manifest_id="manifest-deps",
        execution_fingerprint="fingerprint-deps",
        run_id=RunID(uuid4()),
        overrides=RunManifestOverrides(dependency_lock_hash="sha256:deps-present"),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["dependency_lock_state"] == "present"
    assert summary["dependency_lock_hash"] == "sha256:deps-present"
    assert summary["code_provenance_state"]["dependency_lock_state"] == "present"
    assert summary["code_provenance_state"]["strict_code_provenance_ready"] is True
    assert summary["code_provenance_state"]["strict_code_provenance_blockers"] == []
    assert (
        summary["code_provenance_state"]["dependency_lock_hash"]
        == "sha256:deps-present"
    )
    assert (
        summary["exact_replay_anchors"]["dependency_lock_hash"] == "sha256:deps-present"
    )
    assert (
        summary["persistence_profile"]["surfaces"]["dependency_lock_provenance"] is True
    )
    assert (
        summary["reproducibility_audit_score"]["category_scores"]["run_identity"][
            "score"
        ]
        == 10
    )


def test_build_diagnostics_summary_distinguishes_resume_only_runs() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={"limit": 25, "resume": True, "exact_replay": False},
        replay_capability=ReplayCapability.RESUME_ONLY,
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["replay_capability"] == "resume_only"
    assert summary["requested_exact_replay"] is False
    assert (
        summary["exact_replay_support_boundary"] == "snapshot_backed_source_runs_only"
    )
    assert summary["replay_family_contract"] == _expected_replay_family_contract(
        manifest
    )
    assert (
        summary["replay_capability_reason"]
        == "resume_requested_without_snapshot_backed_inputs"
    )
    assert summary["exact_replay_eligible"] is False
    assert summary["exact_replay_blockers"] == ["immutable_input_snapshots_missing"]
    assert summary["input_snapshot_ids"] == []
    assert summary["input_snapshot_content_hashes"] == []
    assert summary["input_snapshot_identity_fingerprint"] is None
    assert summary["replay_mode"] == "resume"
    assert summary["replay_readiness_verdict"] == "resume_compatible"
    assert summary["operator_replay_mode"] == "Resume"
    assert summary["continuation_mode"] == "checkpoint_snapshot_only_resume"
    assert (
        summary["resume_contract"]["continuation_mode"]
        == "checkpoint_snapshot_only_resume"
    )
    assert summary["input_snapshot_count"] == 0
    assert summary["snapshot_status"] == "none"
    assert summary["input_snapshots"] == []


def test_build_diagnostics_summary_classifies_full_scan_idempotent_rebuild() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={"limit": 25, "resume": True, "exact_replay": False},
        runtime_config={"pipeline": {"loading_strategy": "full_scan_only"}},
        resolved_config={"pipeline": {"loading_strategy": "full_scan_only"}},
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["replay_mode"] == "resume"
    assert summary["continuation_mode"] == "full_scan_idempotent_rebuild"
    assert (
        summary["resume_contract"]["continuation_mode"]
        == "full_scan_idempotent_rebuild"
    )


def test_build_diagnostics_summary_surfaces_required_profile_gap() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={
            "limit": 25,
            "required_persistence_profile": "replay_ready",
        },
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["required_persistence_profile"] == "replay_ready"
    assert summary["persistence_profile"]["required_profile"] == "replay_ready"
    assert summary["persistence_profile"]["required_profile_satisfied"] is False
    assert summary["persistence_profile"]["required_profile_missing_requirements"] == [
        "exact_replay_capability",
        "dependency_lock_provenance",
        "immutable_input_snapshots",
        "produced_artifact_trace",
    ]
    assert summary["alert_signals"]["required_persistence_profile_gap"] is True
    assert summary["alert_signals"]["produced_artifact_trace_gap"] is True
    assert summary["next_steps"] == [
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ]


def test_build_diagnostics_summary_distinguishes_snapshot_backed_runs_from_exact_replay() -> (
    None
):
    manifest = replace(
        _make_manifest(),
        launch_context={"limit": 25, "resume": False, "exact_replay": False},
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=build_source_refs(
            immutable_uri="file:///workspace/bronze/batch_1.jsonl.zst",
            storage_provider="s3",
            object_bucket="bioetl-bronze",
            object_key="chembl/activity/batch_1.jsonl.zst",
            object_version_id="version-001",
        ),
        code_provenance=replace(
            _make_manifest().code_provenance,
            dependency_lock_hash="sha256:deps-present",
        ),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["replay_capability"] == "exact_replay_supported"
    assert summary["requested_exact_replay"] is False
    assert (
        summary["exact_replay_support_boundary"] == "snapshot_backed_source_runs_only"
    )
    assert summary["replay_family_contract"] == _expected_replay_family_contract(
        manifest
    )
    assert summary["exact_replay_eligible"] is True
    assert summary["replay_mode"] == "same_data_state_recovery"
    assert summary["replay_readiness_verdict"] == "exact_replay_ready"
    assert summary["operator_replay_mode"] == "Rebuild"
    assert summary["exact_replay_blockers"] == []
    assert summary["input_snapshot_ids"] == ["snapshot-1"]
    assert summary["snapshot_status"] == "full"
    assert summary["input_snapshots"] == [
        {
            "provider": "chembl",
            "entity": "activity",
            "pipeline_name": "chembl_activity",
            "query": None,
            "snapshot_id": "snapshot-1",
            "content_hash": "sha256:snapshot-1",
            "immutable_uri": "file:///workspace/bronze/batch_1.jsonl.zst",
            "query_fingerprint": None,
            "storage_provider": "s3",
            "object_bucket": "bioetl-bronze",
            "object_key": "chembl/activity/batch_1.jsonl.zst",
            "object_version_id": "version-001",
            "etag": None,
            "last_modified": None,
            "captured_at": None,
        }
    ]


def test_build_diagnostics_summary_does_not_report_exact_replay_from_intent_alone() -> (
    None
):
    manifest = replace(
        _make_manifest(),
        launch_context={"limit": 25, "resume": False, "exact_replay": True},
        replay_capability=ReplayCapability.REBUILD_ONLY,
        source_refs=(),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["requested_exact_replay"] is True
    assert (
        summary["exact_replay_support_boundary"] == "snapshot_backed_source_runs_only"
    )
    assert summary["replay_family_contract"] == _expected_replay_family_contract(
        manifest
    )
    assert summary["exact_replay_eligible"] is False
    assert summary["replay_mode"] == "rebuild"
    assert summary["replay_readiness_verdict"] == "exact_replay_blocked"
    assert summary["operator_replay_mode"] == "Exact Replay Blocked"
    assert summary["snapshot_status"] == "none"
    assert summary["exact_replay_blockers"] == [
        "immutable_input_snapshots_missing",
        "dependency_lock_provenance_missing",
    ]


def test_build_diagnostics_summary_marks_published_source_family_strict_replay_safe() -> (
    None
):
    manifest = replace(
        _make_manifest(),
        provider="openalex",
        entity="publication",
        launch_context={"limit": 25, "resume": False, "exact_replay": True},
        resolved_config={"provider": "openalex", "entity_type": "publication"},
        code_provenance=replace(
            _make_manifest().code_provenance,
            contract_ref="openalex.publication",
            dq_policy_ref="openalex_publication.gold",
            dependency_lock_hash="sha256:openalex-publication-lock",
        ),
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=build_source_refs(
            provider="openalex",
            entity="publication",
            pipeline_name="openalex_publication",
            immutable_uri="file:///workspace/bronze/batch_1.jsonl.zst",
        ),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["replay_family_contract"]["strict_exact_replay_supported"] is True
    assert summary["replay_readiness_verdict"] == "exact_replay_ready"
    assert summary["resume_contract"]["applied_checkpoint_compatibility_policy"] == (
        "hard_fail"
    )
    assert summary["resume_contract"]["strict_replay_safe"] is True
    assert summary["exact_replay_blockers"] == []


def test_build_diagnostics_summary_flags_append_mode_semantic_sinks() -> None:
    manifest = replace(
        _make_manifest(),
        runtime_config={"sink": {"silver": {"enabled": True, "mode": "append"}}},
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=build_source_refs(
            immutable_uri="file:///workspace/bronze/batch_1.jsonl.zst",
        ),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["append_mode_semantic_sinks"] == ["sink.silver.mode=append"]
    assert summary["replay_capability_reason"] == (
        "append_mode_semantic_outputs_block_exact_replay"
    )
    assert summary["exact_replay_eligible"] is False
    assert "append_mode_semantic_outputs" in summary["exact_replay_blockers"]
    assert (
        "reproducible_semantic_output_mode"
        in summary["persistence_profile"]["replay_ready_missing_requirements"]
    )
    assert summary["alert_signals"]["reproducible_semantic_output_mode_gap"] is True


def test_build_diagnostics_summary_surfaces_legacy_observe_resume_contract() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={
            "resume": True,
            "checkpoint_compatibility_policy": "legacy_observe",
        },
    )

    summary = build_diagnostics_summary(manifest, ())

    resume_contract = summary["resume_contract"]
    assert resume_contract["requested_checkpoint_compatibility_policy"] == (
        "legacy_observe"
    )
    assert resume_contract["applied_checkpoint_compatibility_policy"] == (
        "legacy_observe"
    )
    score = summary["reproducibility_audit_score"]
    assert (
        "legacy_observe_checkpoint_policy"
        in (score["category_scores"]["checkpoint_safety"]["blockers"])
    )


def test_build_diagnostics_summary_coerces_observe_for_replay_ready_profile() -> None:
    manifest = replace(
        _make_manifest(),
        launch_context={
            "resume": True,
            "required_persistence_profile": "replay_ready",
            "checkpoint_compatibility_policy": "observe",
        },
    )

    summary = build_diagnostics_summary(manifest, ())

    resume_contract = summary["resume_contract"]
    assert resume_contract["requested_checkpoint_compatibility_policy"] == "observe"
    assert resume_contract["applied_checkpoint_compatibility_policy"] == "soft_fail"
    score = summary["reproducibility_audit_score"]
    assert (
        "checkpoint_policy_below_profile_minimum"
        in score["category_scores"]["checkpoint_safety"]["blockers"]
    )


@pytest.mark.parametrize(
    ("terminal_status", "expected_event_type", "signal_key"),
    [
        ("success", "run_finished", None),
        ("failed", "run_failed", "run_failed"),
        ("shutdown", "run_shutdown", "run_shutdown"),
    ],
)
def test_build_diagnostics_summary_exposes_required_operator_fields(
    terminal_status: str,
    expected_event_type: str,
    signal_key: str | None,
) -> None:
    manifest = _make_manifest()
    ledger_entries = _build_ledger_entries(
        manifest,
        terminal_status=terminal_status,
    )

    summary = build_diagnostics_summary(manifest, ledger_entries)

    assert summary["latest_status"] == terminal_status
    assert summary["latest_event_type"] == expected_event_type
    assert summary["event_family_counts"] == {
        "artifact": 1,
        "diagnostic": 1,
        "pipeline.lifecycle": 2,
        "pipeline.phase": 1,
    }
    assert summary["event_type_counts"][expected_event_type] == 1
    assert summary["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "stage": "silver",
            "artifact_id": "silver:chembl.activity@1",
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
            "artifact_path": "data/output/silver/chembl/activity",
        }
    ]
    assert summary["planned_artifact_count"] == 0
    assert summary["published_artifact_count"] == 1
    assert summary["missing_artifact_links"] == 0
    assert summary["identity_graph_complete"] is True
    assert summary["identity_graph"] == {
        "run_id": str(manifest.run_id),
        "manifest_id": "manifest-diagnostics",
        "execution_fingerprint": "fingerprint-diagnostics",
        "config_hash": _VALID_CONFIG_HASH,
        "resolved_config_hash": _VALID_RESOLVED_CONFIG_HASH,
        "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        "git_commit": "abc1234",
        "source_revision_state": "clean",
        "dependency_lock_state": "missing",
        "code_provenance_state": {
            "git_commit": "abc1234",
            "source_revision_state": "clean",
            "dependency_lock_state": "missing",
            "strict_code_provenance_ready": False,
            "strict_code_provenance_blockers": ["dependency_lock_hash_missing"],
        },
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "replay_of_run_id": None,
        "replay_of_manifest_id": None,
        "replay_parentage": _expected_replay_parentage(manifest),
        "canonical_execution_identity": _expected_canonical_execution_identity(
            manifest
        ),
        "exact_replay_anchors": _expected_exact_replay_anchors(
            manifest,
            published_artifact_ids=["silver:chembl.activity@1"],
            published_artifact_paths=["data/output/silver/chembl/activity"],
            lineage_fragment_ids=["silver:fragment-1"],
        ),
        "degraded_runtime_anchor": _expected_degraded_runtime_anchor(manifest),
        "replay_capability": "rebuild_only",
        "requested_exact_replay": False,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": _expected_replay_family_contract(manifest),
        "replay_capability_reason": "immutable_input_snapshots_missing",
        "exact_replay_eligible": False,
        "exact_replay_blockers": ["immutable_input_snapshots_missing"],
        "replay_readiness_verdict": "incremental_new_run",
        "append_mode_semantic_sinks": [],
        "input_snapshot_ids": [],
        "input_snapshot_content_hashes": [],
        "input_snapshot_identity_fingerprint": None,
        "replay_mode": "rebuild",
        "operator_replay_mode": "Incremental New Run",
        "snapshot_status": "none",
        "continuation_mode": "rebuild_only",
        "resume_contract": _expected_resume_contract(manifest),
        "resume_diagnostics": None,
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
        "input_snapshot_count": 0,
        "input_snapshots": [],
        "planned_artifacts": [],
        "published_artifacts": [
            build_published_silver_artifact(
                artifact_path="data/output/silver/chembl/activity",
                include_dataset_ref=True,
                include_artifact_id=False,
            )
        ],
        "produced_artifact_trace": _expected_produced_artifact_trace(manifest),
        "occurrence_only_diagnostics": [],
    }
    assert summary["persistence_profile"] == {
        "attained_profile": "degraded_observable",
        "required_profile": "degraded_observable",
        "required_profile_satisfied": True,
        "claims": {
            "degraded_observable": True,
            "replay_ready": False,
            "forensic_grade": False,
        },
        "surfaces": {
            "control_plane_manifest": True,
            "dependency_lock_provenance": False,
            "effective_config_artifact": True,
            "reproducible_semantic_output_mode": True,
            "strict_replay_execution_context_support": True,
            "immutable_input_snapshots": False,
            "exact_replay_capability": False,
            "produced_artifact_trace": True,
            "run_ledger_history": True,
            "artifact_lineage_links": True,
            "lineage_closure_boundary_support": True,
        },
        "required_profile_missing_requirements": [],
        "replay_ready_missing_requirements": [
            "exact_replay_capability",
            "dependency_lock_provenance",
            "immutable_input_snapshots",
        ],
        "forensic_grade_missing_requirements": [
            "exact_replay_capability",
            "dependency_lock_provenance",
            "immutable_input_snapshots",
        ],
        "composite_resume_reconstructability": {
            "scope": "coarse_grained_composite_resume",
            "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
            "reconstructs": [
                "state",
                "seed_completed",
                "merge_completed",
                "last_event_id",
                "last_event_occurred_at",
            ],
            "does_not_reconstruct": [
                "per_provider_result_maps",
                "rich_checkpoint_payloads",
            ],
            "forensic_grade_supported": True,
        },
        "lineage_closure_boundary": _expected_lineage_closure_boundary(manifest),
    }
    assert summary["correlation_anchor_gaps"] == {
        "resolved_config_hash": 0,
        "effective_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }
    assert summary["cross_validation_signal_present"] is False
    assert summary["occurrence_only_diagnostics"] == []
    assert summary["exact_replay_anchors"] == _expected_exact_replay_anchors(
        manifest,
        published_artifact_ids=["silver:chembl.activity@1"],
        published_artifact_paths=["data/output/silver/chembl/activity"],
        lineage_fragment_ids=["silver:fragment-1"],
    )
    assert summary["produced_artifact_trace"] == _expected_produced_artifact_trace(
        manifest
    )
    alert_signals = summary["alert_signals"]
    assert isinstance(alert_signals, dict)
    assert alert_signals["artifact_linkage_gap"] is False
    assert alert_signals["lineage_gap"] is False
    assert alert_signals["immutable_input_snapshot_gap"] is True
    assert alert_signals["strict_replay_boundary_gap"] is False
    assert alert_signals["reproducible_semantic_output_mode_gap"] is False
    assert alert_signals["produced_artifact_trace_gap"] is False
    assert alert_signals["lineage_closure_boundary_gap"] is False
    assert alert_signals["composite_resume_reconstructability_gap"] is False
    assert alert_signals["required_persistence_profile_gap"] is False
    assert alert_signals["replay_ready_gap"] is True
    assert alert_signals["forensic_grade_gap"] is True
    assert alert_signals["dq_signal_present"] is False
    assert alert_signals["cross_validation_signal_present"] is False
    if signal_key is None:
        assert alert_signals["run_failed"] is False
        assert alert_signals["run_shutdown"] is False
        assert summary["next_steps"] == [
            "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
            "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
            "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        ]
    else:
        assert alert_signals[signal_key] is True
        assert "No alert signals detected" not in summary["next_steps"]


def test_build_diagnostics_summary_surfaces_persisted_resume_diagnostics() -> None:
    manifest = _make_manifest()
    ledger_entries = (
        RunLedgerEntry(
            entry_id="entry-resume-rejected",
            manifest_id=manifest.manifest_id,
            run_id=manifest.run_id,
            event_type="checkpoint_resume_rejected",
            event_family="pipeline.lifecycle",
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            status="rejected",
            details={
                "compatibility_disposition": "hard_fail",
                "resume_rejected": True,
                "execution_identity_compatible": False,
                "messages": ["composite_run_identity mismatch"],
                "current_identity": {
                    "execution_fingerprint": manifest.execution_fingerprint,
                    "composite_run_identity": "current-composite-identity",
                },
                "checkpoint_identity": {
                    "execution_fingerprint": manifest.execution_fingerprint,
                    "composite_run_identity": "checkpoint-composite-identity",
                },
            },
        ),
    )

    summary = build_diagnostics_summary(manifest, ledger_entries)

    assert summary["resume_contract"] == _expected_resume_contract(manifest)
    assert summary["resume_diagnostics"] == {
        "source_event_type": "checkpoint_resume_rejected",
        "source_status": "rejected",
        "compatibility_disposition": "hard_fail",
        "resume_rejected": True,
        "execution_identity_compatible": False,
        "messages": ["composite_run_identity mismatch"],
        "current_identity": {
            "execution_fingerprint": manifest.execution_fingerprint,
            "composite_run_identity": "current-composite-identity",
        },
        "checkpoint_identity": {
            "execution_fingerprint": manifest.execution_fingerprint,
            "composite_run_identity": "checkpoint-composite-identity",
        },
    }
    assert summary["identity_graph"]["resume_contract"] == _expected_resume_contract(
        manifest
    )
    assert (
        summary["identity_graph"]["resume_diagnostics"] == summary["resume_diagnostics"]
    )
    checkpoint_diag = summary["reproducibility_diagnostics"]["checkpoint_anchors"]
    assert checkpoint_diag["resume_anchor_comparison"] == {
        "checkpoint_identity_present": True,
        "matching_fields": ["execution_fingerprint"],
        "mismatched_fields": ["composite_run_identity"],
        "missing_current_fields": [],
        "missing_checkpoint_fields": [],
    }


def test_build_diagnostics_summary_projects_composite_dossier_correlation() -> None:
    base_manifest = _make_manifest()
    manifest = replace(
        base_manifest,
        provider="composite",
        entity="composite_activity",
        launch_context={
            **base_manifest.launch_context,
            "execution_context": "composite",
        },
    )
    entry = RunLedgerEntry(
        entry_id="entry-composite-1",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type="composite_merge_completed",
        event_family="composite",
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        status="success",
        details={
            "_diagnostic": {
                "manifest_id": manifest.manifest_id,
                "run_id": str(manifest.run_id),
                "event_type": "composite_merge_completed",
                "event_family": "composite",
                "resolved_config_hash": _VALID_RESOLVED_CONFIG_HASH,
                "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
                "contract_ref": "chembl.activity",
                "contract_version": "1.2.0",
                "composite_run_id": "composite-run-1",
            }
        },
    )

    summary = build_diagnostics_summary(manifest, (entry,))

    assert summary["composite_dossier_projection"] == {
        "is_composite_run": True,
        "primary_composite_run_id": "composite-run-1",
        "composite_run_ids": ["composite-run-1"],
        "composite_run_id_consistent": True,
        "correlation_policy": {
            "required_anchor": "composite_run_id",
            "required_event_families": ["checkpoint", "composite"],
            "semantic_anchor": "execution_fingerprint",
            "occurrence_anchor": "run_id",
            "status": "satisfied",
        },
        "correlation_anchor_gaps": {"composite_run_id": 0},
        "resume_diagnostics": None,
        "resume_reconstructability": {
            "scope": "coarse_grained_composite_resume",
            "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
            "reconstructs": [
                "state",
                "seed_completed",
                "merge_completed",
                "last_event_id",
                "last_event_occurred_at",
            ],
            "does_not_reconstruct": [
                "per_provider_result_maps",
                "rich_checkpoint_payloads",
            ],
            "forensic_grade_supported": False,
        },
    }


def test_replay_surfaces_ignore_occurrence_only_manifest_drift() -> None:
    manifest = replace(
        _make_manifest(),
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="fixture://sample",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-1",
                        content_hash="sha256:snapshot-1",
                        immutable_uri="file:///snapshots/bronze-1.jsonl.zst",
                        query_fingerprint="query-hash-1",
                        captured_at=datetime(2025, 1, 1, tzinfo=UTC),
                    ),
                ),
            ),
        ),
        launch_context={
            **_make_manifest().launch_context,
            "exact_replay": True,
            "required_persistence_profile": "replay_ready",
        },
        runtime_config={
            **_make_manifest().runtime_config,
            "exact_replay": True,
            "required_persistence_profile": "replay_ready",
        },
    )
    drifted = replace(
        manifest,
        manifest_id="manifest-diagnostics-drifted",
        run_id=RunID(uuid4()),
        created_at=datetime(2026, 4, 13, 12, 0, tzinfo=UTC),
    )

    summary = build_diagnostics_summary(manifest, ())
    summary_drifted = build_diagnostics_summary(drifted, ())

    replay_keys = (
        "replay_mode",
        "replay_capability",
        "replay_capability_reason",
        "exact_replay_support_boundary",
        "exact_replay_blockers",
        "required_persistence_profile",
        "resume_contract",
        "persistence_profile",
    )
    for key in replay_keys:
        assert summary[key] == summary_drifted[key]


def test_exact_replay_anchors_exclude_occurrence_only_identifiers() -> None:
    manifest = _make_manifest()

    summary = build_diagnostics_summary(manifest, ())

    anchors = summary["exact_replay_anchors"]
    assert isinstance(anchors, dict)
    assert anchors["semantic_identity_anchor"] == "execution_fingerprint"
    assert "manifest_id" not in anchors
    assert "run_id" not in anchors
    assert summary["produced_artifact_trace"]["manifest_id"] == manifest.manifest_id


def test_build_diagnostics_summary_accepts_legacy_data_contract_version_alias() -> None:
    manifest = _make_manifest()
    entry = RunLedgerEntry(
        entry_id="entry-legacy-alias",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type="run_finished",
        event_family="pipeline.lifecycle",
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        status="success",
        details={
            "_diagnostic": {
                "diagnostic_contract_version": "v1",
                "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
                "contract_ref": "chembl.activity",
                "data_contract_version": "1.2.0",
            }
        },
    )

    summary = build_diagnostics_summary(manifest, (entry,))

    assert summary["correlation_anchor_gaps"]["contract_version"] == 0


def test_build_diagnostics_summary_formalizes_composite_exact_replay_boundary() -> None:
    base_manifest = _make_manifest()
    manifest = replace(
        base_manifest,
        provider="composite",
        entity="publications",
        pipeline_name="publications",
        launch_context={
            "resume": False,
            "exact_replay": False,
            "execution_context": "composite",
            "exact_replay_support_boundary": "composite_snapshot_backed_input_envelope",
        },
        replay_capability=ReplayCapability.REBUILD_ONLY,
        source_refs=(),
        code_provenance=replace(
            base_manifest.code_provenance,
            contract_ref="composite.publications",
            dq_policy_ref="composite.publications.dq",
        ),
    )

    summary = build_diagnostics_summary(manifest, ())

    assert (
        summary["exact_replay_support_boundary"]
        == "composite_snapshot_backed_input_envelope"
    )
    assert summary["replay_family_contract"] == _expected_replay_family_contract(
        manifest
    )
    assert summary["replay_capability_reason"] == "composite_snapshot_envelope_missing"
    assert summary["exact_replay_blockers"] == ["immutable_input_snapshots_missing"]
    assert summary["persistence_profile"]["surfaces"] == {
        "control_plane_manifest": True,
        "dependency_lock_provenance": False,
        "effective_config_artifact": True,
        "reproducible_semantic_output_mode": True,
        "strict_replay_execution_context_support": True,
        "immutable_input_snapshots": False,
        "exact_replay_capability": False,
        "produced_artifact_trace": False,
        "run_ledger_history": False,
        "artifact_lineage_links": True,
        "lineage_closure_boundary_support": False,
    }
    assert summary["persistence_profile"]["replay_ready_missing_requirements"] == [
        "exact_replay_capability",
        "dependency_lock_provenance",
        "immutable_input_snapshots",
        "produced_artifact_trace",
    ]
    assert summary["persistence_profile"]["forensic_grade_missing_requirements"] == [
        "exact_replay_capability",
        "dependency_lock_provenance",
        "immutable_input_snapshots",
        "produced_artifact_trace",
        "run_ledger_history",
        "lineage_closure_boundary_support",
        "composite_rich_replay_projection",
    ]
    assert summary["alert_signals"]["strict_replay_boundary_gap"] is False
    assert summary["alert_signals"]["lineage_closure_boundary_gap"] is True
    assert summary["alert_signals"]["produced_artifact_trace_gap"] is True
    assert summary["alert_signals"]["composite_resume_reconstructability_gap"] is True
    assert summary["next_steps"] == [
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
        (
            "Treat this pipeline family as outside the current operator-grade "
            "lineage closure boundary; do not claim forensic-grade trace/debug "
            "support for it."
        ),
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
        (
            "Treat composite resume as checkpoint snapshot plus ledger suffix "
            "replay only; do not expect per-provider result maps or other rich "
            "checkpoint payloads to be reconstructed."
        ),
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ]
