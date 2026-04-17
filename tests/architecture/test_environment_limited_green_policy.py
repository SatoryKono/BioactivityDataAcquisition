"""Architecture tests for environment-limited green interpretation policy."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs" / "quality" / "environment_limited_green_policy.yaml"
TAXONOMY_PATH = ROOT / "configs" / "quality" / "test_health_reporting.yaml"
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
SCORECARD_PATH = ROOT / "configs" / "quality" / "debt_scorecard.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.mark.architecture
class TestEnvironmentLimitedGreenPolicy:
    """Keep environment-limited green interpretation explicit and consistent."""

    def test_policy_tracks_taxonomy_and_classifier_sources(self) -> None:
        policy = _load_yaml(POLICY_PATH)

        assert policy.get("policy_scope") == "environment_limited_green_interpretation"
        assert (
            policy.get("taxonomy_path") == "configs/quality/test_health_reporting.yaml"
        )
        assert policy.get("classifier_source") == "scripts/engineering/ci/quality_integral_gate.py"
        assert (ROOT / policy["taxonomy_path"]).exists()
        assert (ROOT / policy["classifier_source"]).exists()

    def test_policy_covers_every_environment_limit_skip_class(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        taxonomy = _load_yaml(TAXONOMY_PATH)
        skip_classes = set(taxonomy.get("skip_classes", {}))
        mapped = {entry["skip_class"] for entry in policy.get("reason_policy", [])}

        assert mapped == skip_classes

    def test_current_baseline_policy_matches_live_provider_matrix(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        matrix = _load_yaml(MATRIX_PATH)
        baseline = matrix.get("contract_testing", {}).get(
            "live_api_minimum_baseline", {}
        )
        current_baseline = policy.get("current_baseline", {})

        assert current_baseline.get("enforced_provider_count") == len(
            baseline.get("enforced_providers", [])
        )
        assert baseline.get("pilot_providers", []) == []
        assert baseline.get("vcr_only_providers", []) == []
        assert set(current_baseline.get("accepted_steady_state_reasons", [])) == {
            "live_network_opt_in_gate",
            "live_api_gate_mode_non_always",
        }
        assert set(current_baseline.get("disallowed_reopened_gap_reasons", [])) == {
            "pilot_provider_count",
            "vcr_only_provider_count",
        }

    def test_architecture_skip_budget_reference_stays_explicit(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        scorecard = _load_yaml(SCORECARD_PATH)
        budget_ref = policy.get("current_baseline", {}).get(
            "architecture_skip_budget_reference", {}
        )

        assert budget_ref.get("scorecard_path") == "configs/quality/debt_scorecard.yaml"
        assert budget_ref.get("coarse_budget_key") == "architecture_skip_count"
        coarse_budgets = scorecard.get("governance", {}).get("coarse_budgets", {})
        assert coarse_budgets.get("architecture_skip_count", {}).get("max_count") == 7

    def test_reason_postures_distinguish_policy_from_reopened_gap(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        entries = {
            entry["skip_class"]: entry for entry in policy.get("reason_policy", [])
        }

        assert (
            entries["live_network_opt_in_gate"]["posture"]
            == "accepted_steady_state_policy"
        )
        assert (
            entries["live_api_gate_mode_non_always"]["posture"]
            == "accepted_steady_state_policy"
        )
        assert entries["architecture_suite_skips"]["posture"] == "transitional_debt"
        assert entries["pilot_provider_count"]["posture"] == "reopened_baseline_gap"
        assert entries["vcr_only_provider_count"]["posture"] == "reopened_baseline_gap"

        assert entries["pilot_provider_count"]["allowed_in_current_baseline"] is False
        assert (
            entries["vcr_only_provider_count"]["allowed_in_current_baseline"] is False
        )
