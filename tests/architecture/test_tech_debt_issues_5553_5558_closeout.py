"""Closeout guardrails for technical-debt issues #5553-#5558."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.application.core.lifecycle.checkpoint_disposition_policy import (
    resolve_missing_compatibility_context_disposition,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5553-5558-closeout.json"
COMPATIBILITY_CENSUS = ROOT / "reports" / "quality" / "compatibility-importer-census.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
HOTSPOT_BASELINE = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
MODULE_COVERAGE_GATES = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"
PR_HYGIENE_DOC = ROOT / ".github" / "PULL_REQUEST_HYGIENE.md"
PR_HYGIENE_WORKFLOW = ROOT / ".github" / "workflows" / "pr-hygiene.yml"
SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
EXPECTED_ISSUES = {5553, 5554, 5555, 5556, 5557, 5558}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _hotspot_row(payload: dict[str, Any], family_name: str) -> dict[str, Any]:
    families = payload["families"]
    assert isinstance(families, list)
    for row in families:
        if isinstance(row, dict) and row.get("name") == family_name:
            return row
    raise AssertionError(f"Missing hotspot family row for {family_name}")


def test_closeout_artifact_covers_requested_issues__5553_5558() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5553-5558-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5553_governance_artifacts_are_aligned_to_committed_inventory() -> None:
    gates_policy = _load_yaml(MODULE_COVERAGE_GATES)
    debt_gates = _load_json(DEBT_GATES)
    aggregate_ratchets = gates_policy["aggregate_residual_ratchets"]
    gate_rows = {row["name"]: row for row in debt_gates["gates"] if isinstance(row, dict)}
    closeout_metrics = _load_json(CLOSEOUT)["metrics"]

    assert aggregate_ratchets["linked_issue"] == "#5553"
    assert aggregate_ratchets["unmeasured_module_count"]["max_count"] == 36
    assert aggregate_ratchets["uncovered_module_count"]["max_count"] == 1611
    assert gate_rows["module_coverage_unmeasured_modules"]["status"] == "pass"
    assert gate_rows["module_coverage_uncovered_modules"]["status"] == "pass"
    assert gate_rows["generated_artifact_drift"]["status"] == "pass"
    assert closeout_metrics["remote_main_sha"] == gate_rows["remote_main_architecture_debt_baseline"]["current"]


def test_issue_5554_control_plane_public_facade_has_zero_first_party_interface_importers() -> (
    None
):
    census = _load_json(COMPATIBILITY_CENSUS)
    summary = census["summary"]

    assert summary["control_plane_root_src_importer_count"] == 0
    assert summary["retained_public_export_facade_count"] == 4

    interface_paths = sorted((ROOT / "src" / "bioetl" / "interfaces").rglob("*.py"))
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in interface_paths
        if "bioetl.composition.control_plane_api" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_issue_5555_hotspot_reviewed_baselines_capture_current_reductions() -> None:
    hotspot = _load_json(HOTSPOT_BASELINE)
    scorecard = _load_yaml(SCORECARD)
    families = scorecard["hotspot_family_ratchets"]["families"]
    scorecard_by_name = {
        family["name"]: family
        for family in families
        if isinstance(family, dict)
        and family.get("name")
        in {"application_services_control_plane", "composition_runtime_builders"}
    }

    application_row = _hotspot_row(hotspot, "application_services_control_plane")
    runtime_row = _hotspot_row(hotspot, "composition_runtime_builders")

    assert application_row["files_ge_250_loc"] == 16
    assert runtime_row["files"] == 43
    assert runtime_row["max_internal_fan_in"] == 5
    assert (
        application_row["files_ge_250_loc"]
        == scorecard_by_name["application_services_control_plane"]["metrics"]["files_ge_250_loc"]
    )
    assert runtime_row["files"] == scorecard_by_name["composition_runtime_builders"]["metrics"]["files"]
    assert (
        runtime_row["max_internal_fan_in"]
        == scorecard_by_name["composition_runtime_builders"]["metrics"]["max_internal_fan_in"]
    )


def test_issue_5556_missing_checkpoint_compatibility_context_fails_closed() -> None:
    assert resolve_missing_compatibility_context_disposition() == (
        "missing_context_hard_fail_raised"
    )


def test_issue_5557_pr_hygiene_policy_and_workflow_stay_narrow() -> None:
    policy_text = PR_HYGIENE_DOC.read_text(encoding="utf-8")
    workflow_text = PR_HYGIENE_WORKFLOW.read_text(encoding="utf-8")

    assert "21" in policy_text
    assert "report-only" in policy_text
    assert "bot-generated" in policy_text
    assert "stale" in workflow_text
    assert "draft" in workflow_text
    assert "workflow_dispatch" in workflow_text


def test_issue_5558_tracker_closeout_metrics_stay_green() -> None:
    payload = _load_json(CLOSEOUT)
    metrics = payload["metrics"]

    assert metrics["generated_artifact_drift_count"] == 0
    assert metrics["replay_missing_context_disposition"] == (
        "missing_context_hard_fail_raised"
    )
