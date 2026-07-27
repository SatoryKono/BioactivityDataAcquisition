"""Unit tests for dashboard performance budget checker (#6571)."""

from __future__ import annotations

pytestmark = pytest.mark.unit


from pathlib import Path

from scripts.engineering.qa.check_dashboard_performance_budgets import evaluate


def test_shipped_dashboards_meet_performance_budgets() -> None:
    violations, warnings, report = evaluate(
        Path("docs/03-guides/dashboards/contracts/performance-budgets.yaml"),
        Path("grafana/dashboards"),
    )
    assert not violations, "\n".join(violations)
    assert report["measurements"], "expected measurements for shipped dashboards"
    uids = {m["uid"] for m in report["measurements"]}
    assert "bioetl-overview-v2" in uids
    assert "bioetl-workflow-overview" not in uids
    assert "bioetl-alerts-slo" not in uids
