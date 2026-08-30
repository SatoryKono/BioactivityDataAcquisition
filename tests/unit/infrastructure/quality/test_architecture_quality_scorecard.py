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
"""Unit tests for architecture quality scorecard aggregation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from scripts.engineering.qa.report_lazy_import_inventory import collect_lazy_imports

from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    _build_categories,
    build_architecture_quality_scorecard,
)
from bioetl.infrastructure.quality import (
    architecture_quality_scorecard as scorecard_module,
    architecture_quality_scoring as scoring_module,
)

ROOT = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.unit


def test_scorecard_load_json_rejects_non_mapping(tmp_path: Path) -> None:
    """Scorecard evidence inputs must be JSON objects."""
    evidence = tmp_path / "evidence.json"
    evidence.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match="must contain a JSON object"):
        scorecard_module._load_json(tmp_path, "evidence.json")


@pytest.mark.parametrize(
    ("payload", "error", "message"),
    [
        ({"packages": "invalid"}, TypeError, "packages must be a list"),
        ({"packages": [None]}, ValueError, "budget is missing"),
        (
            {
                "packages": [
                    {"path": "src/bioetl/composition", "max_modules": "invalid"}
                ]
            },
            TypeError,
            "max_modules must be an integer",
        ),
    ],
)
def test_composition_module_cap_rejects_invalid_evidence(
    payload: dict[str, object],
    error: type[Exception],
    message: str,
) -> None:
    """Invalid cohesion evidence must fail closed."""
    with pytest.raises(error, match=message):
        scoring_module._composition_module_cap(payload)


def test_scoring_diagnostic_payload_requires_integer_lazy_import_cap() -> None:
    """The shrink-only lazy import cap cannot be coerced from text."""
    with pytest.raises(TypeError, match="max_count must be an integer"):
        scoring_module._build_diagnostic_payload(
            families_at_budget={"count": 0, "names": []},
            lazy_import_observed_count=0,
            lazy_import_ratchet={"max_count": "98"},
            composition_module_count=0,
            package_cohesion_budget={"packages": []},
        )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (4.9, "critical"),
        (8.0, "satisfactory_system_refactoring_required"),
    ],
)
def test_score_interpretation_lower_bands(score: float, expected: str) -> None:
    """Lower score bands retain explicit operator-facing interpretations."""
    assert scoring_module._interpretation(score) == expected


@pytest.fixture(scope="module")
def architecture_quality_scorecard_payload() -> dict[str, object]:
    """Build the live scorecard once for assertions sharing the same snapshot."""
    return build_architecture_quality_scorecard(repo_root=ROOT)


def test_architecture_quality_scorecard_has_stable_weighted_shape(
    architecture_quality_scorecard_payload: dict[str, object],
) -> None:
    payload = architecture_quality_scorecard_payload

    assert payload["schema_version"] == 2
    assert payload["weights_sum"] == 1.0
    assert len(payload["categories"]) == 10
    # Governed floor: integral score must stay at or above 8.0 without
    # lowering the threshold (issue #8455). Live score is ~9.1 after #9791.
    assert payload["integral_score"] >= 8.0
    assert payload["interpretation"] in {
        "satisfactory_system_refactoring_required",  # [5.0, 8.5)
        "good_targeted_improvements",  # >= 8.5
    }
    assert all(0.0 <= category["score"] <= 10.0 for category in payload["categories"])


def test_architecture_quality_scorecard_carries_live_evidence_metrics(
    architecture_quality_scorecard_payload: dict[str, object],
) -> None:
    payload = architecture_quality_scorecard_payload
    metrics = payload["metrics"]

    assert metrics["layer_violations"] == 0
    assert metrics["retained_entrypoint_count"] >= 0
    assert metrics["transition_compat_count"] >= 0
    assert metrics["expired_compat_count"] >= 0
    assert metrics["public_entrypoint_growth_count"] == 0
    assert metrics["public_export_facade_growth_count"] == 0
    assert metrics["public_export_facade_conflict_count"] == 0
    assert metrics["unmeasured_module_count"] >= 0
    assert metrics["contract_blocking_issue_count"] == 0
    assert metrics["dq_blocking_issue_count"] == 0
    assert metrics["total_duplicate_clusters"] >= 0
    assert metrics["hotspot_budget_warning_count"] >= 0
    assert metrics["compatibility_test_file_count"] >= 0


def test_architecture_quality_scorecard_separates_diagnostics_from_program_gate(
    architecture_quality_scorecard_payload: dict[str, object],
) -> None:
    payload = architecture_quality_scorecard_payload
    metrics = payload["metrics"]
    diagnostics = payload["diagnostics"]
    composition_root = ROOT / "src" / "bioetl" / "composition"
    lazy_import_ratchet = yaml.safe_load(
        (ROOT / "configs/quality/lazy_import_ratchet.yaml").read_text(encoding="utf-8")
    )
    package_cohesion_budget = yaml.safe_load(
        (ROOT / "configs/quality/package_cohesion_budget.yaml").read_text(
            encoding="utf-8"
        )
    )
    composition_budget = next(
        package
        for package in package_cohesion_budget["packages"]
        if package["path"] == "src/bioetl/composition"
    )

    assert diagnostics["grade_kind"] == "diagnostic_proxy"
    assert diagnostics["program_gate_policy"] == "external_unchanged"
    assert (
        diagnostics["families_at_budget_count"] == metrics["families_at_budget_count"]
    )
    assert diagnostics["families_at_budget"] == metrics["families_at_budget"]
    assert diagnostics["lazy_import_observed_count"] == len(
        collect_lazy_imports(composition_root)
    )
    assert diagnostics["lazy_import_cap"] == lazy_import_ratchet["max_count"]
    assert diagnostics["composition_module_count"] == len(
        list(composition_root.rglob("*.py"))
    )
    assert diagnostics["composition_module_cap"] == composition_budget["max_modules"]
    assert diagnostics["lazy_util"] == metrics["lazy_util"]
    assert diagnostics["composition_util"] == metrics["composition_util"]
    assert (
        "not a count of DDD aggregates" in diagnostics["proxy_notes"]["ddd_invariants"]
    )


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
        "transition_compat_count": 0,
        "sunset_compat_count": 0,
        "expired_compat_count": 0,
        "public_entrypoint_growth_count": 0,
        "public_export_facade_growth_count": 0,
        "public_export_facade_conflict_count": 0,
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
        "transition_compat_count": 0,
        "sunset_compat_count": 0,
        "expired_compat_count": 0,
        "public_entrypoint_growth_count": 0,
        "public_export_facade_growth_count": 0,
        "public_export_facade_conflict_count": 0,
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
        "transition_compat_count": 3,
        "sunset_compat_count": 2,
        "expired_compat_count": 1,
        "public_entrypoint_growth_count": 6,
        "public_export_facade_growth_count": 3,
        "public_export_facade_conflict_count": 1,
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


def test_architecture_quality_scorecard_does_not_penalize_retained_public_api() -> None:
    metrics = {
        "layer_violations": 0,
        "source_module_count": 2180,
        "unmeasured_module_count": 0,
        "uncovered_module_count": 0,
        "hotspot_family_count": 5,
        "hotspot_budget_warning_count": 8,
        "total_duplicate_clusters": 95,
        "retained_entrypoint_count": 12,
        "retained_public_export_facade_count": 4,
        "transition_compat_count": 0,
        "sunset_compat_count": 0,
        "expired_compat_count": 0,
        "public_entrypoint_growth_count": 0,
        "public_export_facade_growth_count": 0,
        "public_export_facade_conflict_count": 0,
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
    retained_counts_changed = {
        **metrics,
        "retained_entrypoint_count": 30,
        "retained_public_export_facade_count": 10,
    }

    assert _build_categories(retained_counts_changed) == _build_categories(metrics)


def test_architecture_quality_scorecard_does_not_double_count_sunset_subset() -> None:
    metrics = {
        "transition_compat_count": 3,
        "sunset_compat_count": 0,
        "expired_compat_count": 0,
    }
    overlapping_sunset_metrics = {**metrics, "sunset_compat_count": 2}

    baseline_scores = {
        category["id"]: category["score"] for category in _build_categories(metrics)
    }
    overlapping_scores = {
        category["id"]: category["score"]
        for category in _build_categories(overlapping_sunset_metrics)
    }

    assert overlapping_scores == baseline_scores


def test_architecture_quality_scorecard_penalizes_at_budget_saturation() -> None:
    clean_metrics = {
        "layer_violations": 0,
        "source_module_count": 2180,
        "unmeasured_module_count": 0,
        "uncovered_module_count": 0,
        "hotspot_family_count": 5,
        "hotspot_budget_warning_count": 0,
        "families_at_budget_count": 0,
        "total_duplicate_clusters": 0,
        "transition_compat_count": 0,
        "sunset_compat_count": 0,
        "expired_compat_count": 0,
        "public_entrypoint_growth_count": 0,
        "public_export_facade_growth_count": 0,
        "public_export_facade_conflict_count": 0,
        "twin_pair_count": 0,
        "compatibility_test_file_count": 0,
        "repo_wide_untriaged_zero_import_candidate_count": 0,
        "contract_blocking_issue_count": 0,
        "dq_blocking_issue_count": 0,
        "dashboarded_without_emission_count": 0,
        "dashboarded_without_declaration_count": 0,
        "runtime_cardinality_review_required_count": 0,
        "runtime_cardinality_threshold_violation_count": 0,
        "adr_enforcement_blocking_gap_count": 0,
        "lazy_util": 0.0,
        "composition_util": 0.0,
    }
    saturated_metrics = {
        **clean_metrics,
        "families_at_budget_count": 2,
        "lazy_util": 1.0,
        "composition_util": 0.9833,
    }

    def _integral(metrics: dict[str, object]) -> float:
        return round(
            sum(float(category["weighted_score"]) for category in _build_categories(metrics)),
            2,
        )

    clean_integral = _integral(clean_metrics)
    saturated_integral = _integral(saturated_metrics)
    assert clean_integral == 10.0
    assert 9.0 <= saturated_integral <= 9.25
    assert saturated_integral < clean_integral
