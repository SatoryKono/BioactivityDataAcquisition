"""Unit tests for architecture quality scorecard aggregation."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    _build_categories,
    build_architecture_quality_scorecard,
)

ROOT = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.unit


def test_architecture_quality_scorecard_has_stable_weighted_shape() -> None:
    payload = build_architecture_quality_scorecard(repo_root=ROOT)

    assert payload["schema_version"] == 1
    assert payload["weights_sum"] == 1.0
    assert len(payload["categories"]) == 10
    assert payload["integral_score"] >= 8.0
    assert payload["interpretation"] in {
        "satisfactory_system_refactoring_required",
        "good_targeted_improvements",
    }
    assert all(0.0 <= category["score"] <= 10.0 for category in payload["categories"])


def test_architecture_quality_scorecard_carries_live_evidence_metrics() -> None:
    payload = build_architecture_quality_scorecard(repo_root=ROOT)
    metrics = payload["metrics"]

    assert metrics["layer_violations"] == 0
    assert metrics["retained_entrypoint_count"] >= 0
    assert metrics["unmeasured_module_count"] >= 0
    assert metrics["contract_blocking_issue_count"] == 0
    assert metrics["dq_blocking_issue_count"] == 0
    assert metrics["total_duplicate_clusters"] >= 0
    assert metrics["hotspot_budget_warning_count"] >= 0
    assert metrics["compatibility_test_file_count"] >= 0


def test_architecture_quality_scorecard_integral_score_improves_with_debt_reduction() -> (
    None
):
    baseline_metrics = {
        "layer_violations": 0,
        "source_module_count": 2180,
        "unmeasured_module_count": 0,
        "uncovered_module_count": 0,
        "hotspot_family_count": 5,
        "hotspot_budget_warning_count": 8,
        "total_duplicate_clusters": 95,
        "retained_entrypoint_count": 12,
        "retained_public_export_facade_count": 4,
        "twin_pair_count": 0,
        "compatibility_test_file_count": 25,
        "repo_wide_untriaged_zero_import_candidate_count": 0,
        "contract_blocking_issue_count": 0,
        "dq_blocking_issue_count": 0,
        "dashboarded_without_emission_count": 0,
        "dashboarded_without_declaration_count": 0,
        "runtime_cardinality_review_required_count": 0,
        "runtime_cardinality_threshold_violation_count": 0,
        "adr_enforcement_blocking_gap_count": 0,
    }
    improved_metrics = {
        **baseline_metrics,
        "hotspot_budget_warning_count": 4,
        "total_duplicate_clusters": 54,
        "retained_entrypoint_count": 9,
        "retained_public_export_facade_count": 2,
        "compatibility_test_file_count": 18,
    }

    baseline_categories = _build_categories(baseline_metrics)
    improved_categories = _build_categories(improved_metrics)

    baseline_integral = round(
        sum(float(category["weighted_score"]) for category in baseline_categories), 2
    )
    improved_integral = round(
        sum(float(category["weighted_score"]) for category in improved_categories), 2
    )

    assert improved_integral > baseline_integral


def test_architecture_quality_scorecard_integral_score_drops_with_regressions() -> None:
    baseline_metrics = {
        "layer_violations": 0,
        "source_module_count": 2180,
        "unmeasured_module_count": 0,
        "uncovered_module_count": 0,
        "hotspot_family_count": 5,
        "hotspot_budget_warning_count": 8,
        "total_duplicate_clusters": 95,
        "retained_entrypoint_count": 12,
        "retained_public_export_facade_count": 4,
        "twin_pair_count": 0,
        "compatibility_test_file_count": 25,
        "repo_wide_untriaged_zero_import_candidate_count": 0,
        "contract_blocking_issue_count": 0,
        "dq_blocking_issue_count": 0,
        "dashboarded_without_emission_count": 0,
        "dashboarded_without_declaration_count": 0,
        "runtime_cardinality_review_required_count": 0,
        "runtime_cardinality_threshold_violation_count": 0,
        "adr_enforcement_blocking_gap_count": 0,
    }
    regressed_metrics = {
        **baseline_metrics,
        "layer_violations": 2,
        "unmeasured_module_count": 3,
        "uncovered_module_count": 2,
        "hotspot_budget_warning_count": 11,
        "total_duplicate_clusters": 140,
        "retained_entrypoint_count": 18,
        "retained_public_export_facade_count": 7,
        "contract_blocking_issue_count": 1,
        "dq_blocking_issue_count": 2,
        "dashboarded_without_emission_count": 1,
        "runtime_cardinality_threshold_violation_count": 1,
        "repo_wide_untriaged_zero_import_candidate_count": 2,
        "adr_enforcement_blocking_gap_count": 1,
    }

    baseline_categories = _build_categories(baseline_metrics)
    regressed_categories = _build_categories(regressed_metrics)

    baseline_integral = round(
        sum(float(category["weighted_score"]) for category in baseline_categories), 2
    )
    regressed_integral = round(
        sum(float(category["weighted_score"]) for category in regressed_categories), 2
    )

    assert regressed_integral < baseline_integral
