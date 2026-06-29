"""Closeout guardrails for technical-debt issues #5510-#5516."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5510-5516-closeout.json"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
MODULE_COVERAGE_GATES = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"
FLAKY_REVIEW = ROOT / "reports" / "quality" / "flaky-test-burndown-review.json"
RUNTIME_CARDINALITY_INVENTORY = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
CONTRACT_POLICY_LOADER = (
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "contract_policy_loader.py"
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def test_closeout_artifact_covers_requested_issues__5510_5516() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5510-5516-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == {
        5510,
        5511,
        5512,
        5513,
        5514,
        5515,
        5516,
    }
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5510_control_plane_root_facade_stays_zero_src_importers() -> None:
    payload = _load_json(COMPATIBILITY_CENSUS)
    summary = payload["summary"]
    control_plane = payload["control_plane_root_facade"]

    assert summary["control_plane_root_src_importer_count"] == 0
    assert control_plane["target_module"] == "bioetl.application.services.control_plane"
    assert control_plane["src_importers"] == []


def test_issues_5511_5512_duplication_wave_reduced_live_baseline_counts() -> None:
    payload = _load_json(DUPLICATION_BASELINE)
    rows = {row["target"]: row for row in payload["targets"] if isinstance(row, dict)}

    assert rows["src/bioetl/interfaces/cli"]["duplicate_count"] <= 10
    assert rows["src/bioetl/composition/bootstrap"]["duplicate_count"] <= 1
    assert payload["summary"]["total_duplicate_clusters"] <= 105


def test_issue_5513_coverage_gate_promoted_to_block() -> None:
    payload = _load_yaml(MODULE_COVERAGE_GATES)
    enforcement = payload["enforcement"]
    ranked_targets = payload["coverage_tail"]["ranked_targets"]
    by_path = {row["path"]: row for row in ranked_targets}

    assert enforcement["tier_violation_mode"] == "block"
    assert (
        by_path["src/bioetl/infrastructure/observability/tracing.py"]["status"]
        == "focused_owner_tests_added"
    )


def test_issue_5514_flaky_review_stays_zero() -> None:
    payload = _load_json(FLAKY_REVIEW)

    assert payload["summary"]["total_flaky"] == 0
    assert payload["reviewed_flaky_tests"] == []


def test_issue_5515_unused_event_review_stays_zero() -> None:
    payload = _load_json(RUNTIME_CARDINALITY_INVENTORY)

    assert payload["unused_declared_observability_events"] == []
    assert payload["unused_declared_metrics"] == []
    assert payload["runtime_cardinality_review_required"] == []
    assert payload["runtime_cardinality_threshold_violations"] == []


def test_issue_5516_contract_policy_loader_no_longer_projects_root_hash_selectors() -> (
    None
):
    source = CONTRACT_POLICY_LOADER.read_text(encoding="utf-8")

    assert "_root_runtime_hash_selectors" not in source
    assert "_build_effective_contract_policy_payload" not in source
