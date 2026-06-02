"""Companion traceability tests for RunManifestInspectionService."""

from __future__ import annotations

import pytest

from datetime import UTC, datetime
from uuid import UUID, uuid4

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID
from tests.unit.application.services.test_run_manifest_inspection_service import (
    COMPOSITE_CV_REPORT_PATH,
    _FIXED_TIME,
    _InMemoryRunLedgerStore,
    _InMemoryRunManifestStore,
    _make_manifest,
)


pytestmark = pytest.mark.unit


def test_show_surfaces_supported_gold_trace_path_in_diagnostics() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000151"))
    manifest = _make_manifest(manifest_id="manifest-gold-trace", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-gold-trace-1",
            manifest_id="manifest-gold-trace",
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=datetime(2025, 1, 1, tzinfo=UTC),
            event_family="artifact",
            status="success",
            stage="gold",
            dataset_ref="gold:chembl.activity",
            lineage_fragment_id="gold:fragment-1",
            details={
                "artifact_path": "gold/chembl/activity",
                "metadata_path": "gold/chembl/activity/chembl_activity_metadata.yaml",
                "artifact_kind": "metadata_sidecar",
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "run_id": str(run_id),
                "manifest_id": "manifest-gold-trace",
            },
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-gold-trace")

    assert result.diagnostics["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "publication_status": "success",
            "stage": "gold",
            "artifact_id": "gold:chembl.activity",
            "dataset_ref": "gold:chembl.activity",
            "lineage_fragment_id": "gold:fragment-1",
            "artifact_path": "gold/chembl/activity",
            "metadata_path": "gold/chembl/activity/chembl_activity_metadata.yaml",
            "artifact_kind": "metadata_sidecar",
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity": "activity",
            "run_id": str(run_id),
            "manifest_id": "manifest-gold-trace",
        }
    ]
    assert result.diagnostics["lineage_fragment_ids"] == ["gold:fragment-1"]
    assert result.diagnostics["missing_artifact_links"] == 0
    assert result.diagnostics["alert_signals"] == {
        "run_failed": False,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "produced_artifact_trace_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": False,
        "replay_ready_gap": False,
        "forensic_grade_gap": False,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }


def test_show_surfaces_cross_validation_traceability_in_diagnostics() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-cv", run_id=run_id)
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-cv-1",
            manifest_id="manifest-cv",
            run_id=run_id,
            event_type="dq_policy_applied",
            occurred_at=_FIXED_TIME,
            event_family="dq",
            status="failed",
            stage="cross_validation",
            details={
                "rule_id": "composite.cross_validation.quarantine",
                "disposition": "quarantine",
                "violation_kind": "cross_validation_mismatch",
                "config_path": "cross_validation",
                "artifact_policy": "occurrence_only_diagnostic",
                "replay_contract": "excluded_from_exact_replay",
                "diagnostic_scope": "composite_cross_validation_quarantine",
                "dq_report_path": COMPOSITE_CV_REPORT_PATH,
            },
        )
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show("manifest-cv")

    assert result.diagnostics["dq_rule_ids"] == [
        "composite.cross_validation.quarantine"
    ]
    assert result.diagnostics["dq_dispositions"] == ["quarantine"]
    assert result.diagnostics["dq_violation_kinds"] == ["cross_validation_mismatch"]
    assert result.diagnostics["cross_validation_rule_ids"] == [
        "composite.cross_validation.quarantine"
    ]
    assert result.diagnostics["cross_validation_config_paths"] == ["cross_validation"]
    assert (
        result.diagnostics["cross_validation_quarantine_policy"]
        == "occurrence_only_diagnostic"
    )
    assert (
        result.diagnostics["cross_validation_quarantine_replay_contract"]
        == "excluded_from_exact_replay"
    )
    assert result.diagnostics["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
    assert result.diagnostics["cross_validation_signal_present"] is True
    assert result.identity_graph["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
    assert result.diagnostics["alert_signals"] == {
        "run_failed": True,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "produced_artifact_trace_gap": True,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": True,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": True,
        "cross_validation_signal_present": True,
    }
    assert result.diagnostics["next_steps"] == [
        "Inspect failure classification and decide retry/quarantine/escalation.",
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
        "Review cross-validation mismatch outcomes and composite policy anchors before retry or quarantine changes.",
    ]
