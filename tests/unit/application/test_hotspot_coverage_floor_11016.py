"""Execute extracted hotspot helpers so the coverage floor stays measured."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.control_plane.manifest.diagnostics.main_helpers_build_unified_reproducibility_diagnostics_policy_payload import (
    _build_unified_reproducibility_diagnostics_policy_payload,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_alerts_build_alert_signals import (
    build_alert_signals,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profile_support_build_composite_resume_reconstructability import (
    build_composite_resume_reconstructability,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support_build_exact_replay_anchors import (
    build_exact_replay_anchors,
)
from bioetl.application.services.control_plane.replay._bundle_descriptor_payloads_build_code_provenance_dict import (
    _build_code_provenance_dict,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_aggregation_evaluate_threshold_failures import (
    evaluate_threshold_failures,
)

pytestmark = pytest.mark.unit


def test_extracted_control_plane_helpers_cover_both_branches() -> None:
    signals = build_alert_signals(
        latest_status=" failed ",
        artifact_refs=[{"dataset_ref": "ds"}],
        lineage_fragment_ids=set(),
        missing_link_count=1,
        composite_resume_reconstructability_gap=True,
        dq_signal_present=True,
        cross_validation_signal_present=False,
        required_persistence_profile_missing_requirements=["gap"],
        replay_ready_missing_requirements=[
            "immutable_input_snapshots",
            "strict_replay_execution_context_support",
            "reproducible_semantic_output_mode",
            "produced_artifact_trace",
        ],
        forensic_grade_missing_requirements=["lineage_closure_boundary_support"],
    )
    assert signals["run_failed"] is True
    assert signals["lineage_gap"] is True

    rich = build_composite_resume_reconstructability(
        composite_execution_context=True,
        composite_resume_rich_replay_supported=True,
    )
    coarse = build_composite_resume_reconstructability(
        composite_execution_context=False,
        composite_resume_rich_replay_supported=False,
    )
    assert rich["forensic_grade_supported"] is True
    assert coarse["scope"] == "coarse_grained_composite_resume"

    policy = _build_unified_reproducibility_diagnostics_policy_payload(
        {"required_persistence_profile": "replay_ready"},
        {"attained_profile": "forensic_grade"},
    )
    assert policy["attained_profile"] == "forensic_grade"
    assert policy["exact_replay_blockers"] == []

    manifest = SimpleNamespace(
        execution_fingerprint="fp",
        pipeline_name="chembl",
        run_type=SimpleNamespace(value="backfill"),
    )
    anchors = build_exact_replay_anchors(
        manifest=manifest,  # type: ignore[arg-type]
        summary={
            "pipeline_version": "1",
            "dependency_lock_hash": "lock",
            "input_snapshot_ids": ["snap"],
            "input_snapshot_content_hashes": [],
        },
        artifact_refs=[{"dataset_ref": "ds", "artifact_path": "path"}],
        lineage_fragment_ids={"frag"},
    )
    assert anchors["dependency_lock_hash"] == "lock"
    assert anchors["published_artifact_ids"] == ["ds"]

    provenance = _build_code_provenance_dict(
        SimpleNamespace(pipeline_version="1", git_commit=None)
    )
    assert provenance == {"pipeline_version": "1"}

    failures = evaluate_threshold_failures(
        thresholds={"lineage": 8, "identity": 5},
        category_scores={
            "lineage": {"score": 4},
            "identity": {"score": "bad"},
        },
    )
    assert {row["reason"] for row in failures} == {
        "below_required_threshold",
        "category_score_missing",
    }
    assert (
        evaluate_threshold_failures(
            thresholds={"lineage": 8},
            category_scores={"lineage": {"score": 9}},
        )
        == []
    )
