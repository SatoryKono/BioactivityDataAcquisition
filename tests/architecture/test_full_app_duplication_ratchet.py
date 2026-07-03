"""Architecture guardrails for full-app duplication ratchets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
BASELINE_PATH = PROJECT_ROOT / "reports/quality/full-app-duplication-baseline.json"


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _target_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = payload.get("targets", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def test_full_app_duplication_budgets_hold_reviewed_baseline() -> None:
    """Full-app duplication budgets must not grow past the reviewed baseline."""
    scorecard = _load_scorecard()
    policy = scorecard.get("full_app_duplication_ratchets", {})
    assert isinstance(policy, dict)
    assert policy.get("mode") == "fail-fast"

    artifact_policy = policy.get("artifact_policy", {})
    assert isinstance(artifact_policy, dict)
    baseline_artifact = artifact_policy.get("baseline_artifact")
    assert isinstance(baseline_artifact, str) and baseline_artifact

    baseline_payload = _load_json(PROJECT_ROOT / baseline_artifact)
    baseline_summary = baseline_payload.get("summary", {})
    assert isinstance(baseline_summary, dict)

    baseline_rows = _target_rows(baseline_payload)
    by_target = {
        str(row["target"]): row
        for row in baseline_rows
        if isinstance(row.get("target"), str)
    }

    families = policy.get("families", [])
    assert isinstance(families, list) and families
    for family in families:
        assert isinstance(family, dict)
        metrics = family.get("metrics", {})
        assert isinstance(metrics, dict)
        duplication_budget = metrics.get("duplication_clusters", {})
        assert isinstance(duplication_budget, dict)
        max_count = duplication_budget.get("max_count")
        assert isinstance(max_count, int) and max_count >= 0

        path_prefix = family.get("path_prefix")
        assert isinstance(path_prefix, str)
        matched = [
            row
            for target, row in by_target.items()
            if target.startswith(path_prefix.rstrip("/"))
        ]
        assert matched, f"Family {family.get('name')} missing from full-app baseline"
        actual = max(int(row["duplicate_count"]) for row in matched)
        assert actual <= max_count, (
            f"Family {family.get('name')} has {actual} duplicate clusters, "
            f"exceeding reviewed budget {max_count}."
        )

    summary_metrics = policy.get("summary_metrics", {})
    assert isinstance(summary_metrics, dict)
    total_budget = summary_metrics.get("total_duplicate_clusters", {})
    assert isinstance(total_budget, dict)
    total_max = total_budget.get("max_count")
    assert isinstance(total_max, int)
    total_actual = int(baseline_summary.get("total_duplicate_clusters", -1))
    assert total_actual <= total_max
