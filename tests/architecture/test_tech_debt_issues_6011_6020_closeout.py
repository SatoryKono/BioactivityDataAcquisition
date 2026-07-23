"""Architecture guards for issues #6011-#6020 closeout evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports/quality/tech-debt-issues-6011-6020-closeout.json"


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issues_6011_6020_closeout_artifact_has_expected_scope() -> None:
    """Closeout evidence should cover exactly the requested issue range."""
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]
    assert isinstance(issues, list)

    assert payload["schema_version"] == "tech-debt-issues-6011-6020-closeout-v1"
    assert [issue["number"] for issue in issues] == list(range(6011, 6021))
    assert all(str(issue["status"]).startswith("closeable") for issue in issues)


def test_issue_6016_hotspot_family_fan_in_is_no_longer_saturated() -> None:
    """composition_factories_pipeline should have margin below its fan-in budget."""
    baseline = _load_json(ROOT / "reports/quality/hotspot-family-baseline.json")
    families = baseline["families"]
    assert isinstance(families, list)
    family = next(
        item
        for item in families
        if isinstance(item, dict) and item["name"] == "composition_factories_pipeline"
    )
    budgets = family["bounded_growth_budgets"]
    assert isinstance(budgets, dict)

    assert family["max_internal_fan_in"] == 3
    assert budgets["max_internal_fan_in"] == 3
    assert not family.get("budget_warnings")


def test_issue_6019_duplication_triage_matches_current_baselines() -> None:
    """Duplication triage should reflect current report-only baseline counts."""
    closeout = _load_json(CLOSEOUT)
    issue_6019 = next(
        issue
        for issue in closeout["issues"]
        if isinstance(issue, dict) and issue["number"] == 6019
    )
    triage = issue_6019["triage"]
    assert isinstance(triage, dict)

    hotspot = _load_json(ROOT / "reports/quality/hotspot-duplication-baseline.json")
    full_app = _load_json(ROOT / "reports/quality/full-app-duplication-baseline.json")
    broad = _load_json(ROOT / "reports/quality/duplication-baseline.json")

    assert (
        triage["hotspot_duplicate_clusters"]
        == hotspot["summary"]["total_duplicate_clusters"]
    )
    assert (
        triage["full_app_duplicate_clusters"]
        == full_app["summary"]["total_duplicate_clusters"]
    )
    assert (
        triage["broad_report_only_duplicate_clusters"]
        == broad["summary"]["total_duplicate_clusters"]
    )


def test_issue_6015_local_full_coverage_attempt_is_not_overstated() -> None:
    """The closeout should not claim fresh repo-wide branch XML when it timed out."""
    closeout = _load_json(CLOSEOUT)
    issue_6015 = next(
        issue
        for issue in closeout["issues"]
        if isinstance(issue, dict) and issue["number"] == 6015
    )
    attempt = issue_6015["local_coverage_attempt"]
    assert isinstance(attempt, dict)

    assert attempt["result"] == "timed_out"
    log_path = ROOT / str(attempt["log"])
    assert log_path.exists()
    assert "timed out after 900s" in log_path.read_text(encoding="utf-8")
