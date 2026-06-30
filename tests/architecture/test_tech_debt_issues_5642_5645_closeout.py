"""Closeout guards for technical-debt issues #5642, #5643, and #5645."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5642-5645-closeout.json"
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
HOTSPOT_BASELINE = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
DEBT_SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"

EXPECTED_ISSUES = {5642, 5643, 5645}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _gate(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in payload["gates"]:
        if gate["name"] == name:
            return gate
    raise AssertionError(f"missing debt governance gate: {name}")


def test_closeout_artifact_covers_requested_issues__5642_5645() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5642-5645-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5642_adapter_duplication_is_below_opening_baseline() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}

    assert by_target["src/bioetl/infrastructure/adapters"]["duplicate_count"] == 56
    assert by_target["src/bioetl/infrastructure/adapters"]["duplicate_count"] < 70


def test_issue_5643_pipeline_and_cli_duplication_are_below_opening_baselines() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}

    assert by_target["src/bioetl/application/pipelines"]["duplicate_count"] == 15
    assert by_target["src/bioetl/application/pipelines"]["duplicate_count"] < 20
    assert by_target["src/bioetl/interfaces/cli"]["duplicate_count"] == 0
    assert by_target["src/bioetl/interfaces/cli"]["duplicate_count"] < 5


def test_issue_5645_hotspot_warning_count_is_ratcheted_down() -> None:
    baseline = _load_json(HOTSPOT_BASELINE)
    gates = _load_json(DEBT_GATES)
    scorecard = _load_yaml(DEBT_SCORECARD)
    baseline_families = {family["name"]: family for family in baseline["families"]}
    scorecard_families = {
        family["name"]: family
        for family in scorecard["hotspot_family_ratchets"]["families"]
    }
    baseline_family = baseline_families["composition_runtime_builders"]
    scorecard_family = scorecard_families["composition_runtime_builders"]
    hotspot_gate = _gate(gates, "hotspot_family_baseline_budget_warnings")

    assert baseline["summary"]["budget_warnings"] == 0
    assert baseline["summary"]["budget_review_notes"] == 6
    assert baseline_family["files_ge_250_loc"] == 1
    assert baseline_family["max_internal_fan_in"] == 5
    assert baseline_family["budget_warnings"] == []
    assert baseline_family["budget_review_notes"] == [
        "at_budget:max_internal_fan_in=5/5"
    ]
    assert scorecard_family["metrics"]["files_ge_250_loc"] == 1
    assert scorecard_family["metrics"]["max_internal_fan_in"] == 5
    assert scorecard_family["bounded_growth_budgets"]["files_ge_250_loc"] == 3
    assert scorecard_family["bounded_growth_budgets"]["max_internal_fan_in"] == 5
    assert hotspot_gate["status"] == "pass"
    assert hotspot_gate["current"] == 0
