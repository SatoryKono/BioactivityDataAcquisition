# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Grafana dashboard PromQL reuse contracts."""

from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration

_DUPLICATE_ALLOWLIST = Path("configs/quality/dashboard_query_duplicate_allowlist.yaml")


def _expected_duplicate_uses() -> dict[str, set[tuple[str, str]]]:
    payload = yaml.safe_load(_DUPLICATE_ALLOWLIST.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    exact_duplicates = payload.get("exact_duplicates")
    assert isinstance(exact_duplicates, dict)
    allowed_groups = exact_duplicates.get("allowed_groups")
    assert isinstance(allowed_groups, list)

    expected: dict[str, set[tuple[str, str]]] = {}
    for group in allowed_groups:
        assert isinstance(group, dict)
        expression = group.get("normalized_expression")
        panel_refs = group.get("panel_refs")
        assert isinstance(expression, str) and expression.strip()
        assert isinstance(panel_refs, list) and panel_refs

        normalized_expression = " ".join(expression.split())
        uses: set[tuple[str, str]] = set()
        for panel_ref in panel_refs:
            assert isinstance(panel_ref, str)
            dashboard, separator, title = panel_ref.partition(" :: ")
            assert separator and dashboard and title
            uses.add((dashboard, title))
        assert len(uses) > 1
        assert normalized_expression not in expected
        expected[normalized_expression] = uses

    return expected


def _assert_dq_score_time_semantics() -> None:
    dq_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    dq_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dq_dashboard)
        if panel.get("title")
    }
    score_summary = dq_panels["Monitor Volume-Weighted DQ Score"]
    score_trend = dq_panels["Track Volume-Weighted DQ Score"]
    assert score_summary.get("type") == "stat"
    assert score_summary.get("options", {}).get("colorMode") == "value"
    assert score_summary.get("options", {}).get("graphMode") == "none"
    summary_defaults = score_summary.get("fieldConfig", {}).get("defaults", {})
    assert summary_defaults.get("unit") == "percentunit"
    assert summary_defaults.get("min") == 0
    assert summary_defaults.get("max") == 1
    # Base step is gray (no-value / unset), then risk bands orange→green.
    assert summary_defaults.get("thresholds", {}).get("steps") == [
        {"color": "gray", "value": None},
        {"color": "orange", "value": 0.8},
        {"color": "green", "value": 0.95},
    ]
    assert score_trend.get("type") == "timeseries"
    assert score_trend.get("options", {}).get("tooltip", {}).get("mode") == "single"

    summary_targets = score_summary.get("targets", [])
    trend_targets = score_trend.get("targets", [])
    assert len(summary_targets) == 1
    assert len(trend_targets) == 1
    summary_expr = " ".join(str(summary_targets[0].get("expr", "")).split())
    trend_expr = " ".join(str(trend_targets[0].get("expr", "")).split())
    assert summary_expr != trend_expr
    assert "last_over_time(" in summary_expr
    assert "[7d]" in summary_expr
    assert "last_over_time(" not in trend_expr
    assert trend_targets[0].get("range") is True

    summary_description = str(score_summary.get("description", "")).lower()
    assert "7 days" in summary_description
    assert "trend panel" in summary_description


def _assert_lineage_control_plane_ownership_handoff() -> None:
    dq_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    control_plane_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-control-plane-v1.json")
    )
    dq_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dq_dashboard)
        if panel.get("title")
    }
    control_plane_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(control_plane_dashboard)
        if panel.get("title")
    }
    dq_handoff = dq_panels["Inspect Lineage in Control Plane"]
    control_plane_lineage = control_plane_panels["Track Missing Lineage References"]
    assert dq_handoff.get("type") == "text"
    dq_content = str(dq_handoff.get("options", {}).get("content", "")).lower()
    assert "control plane" in dq_content
    assert "canonical" in dq_content
    dq_links = list(dq_handoff.get("links") or [])
    assert any(
        "bioetl-control-plane-v1" in str(link.get("url", ""))
        and "viewPanel=904" in str(link.get("url", ""))
        for link in dq_links
    )
    assert control_plane_lineage.get("options", {}).get("graphMode") == "area"
    lineage_description = str(control_plane_lineage.get("description", "")).lower()
    assert "missing upstream lineage references" in lineage_description
    assert "replay evidence incomplete" in lineage_description


def test_exact_duplicate_promql_groups_are_only_explicitly_justified_reuse() -> None:
    """Exact duplicate PromQL must stay limited to audited, role-justified reuse."""
    observed_uses_by_expr: dict[str, set[tuple[str, str]]] = {}

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title")
            if not isinstance(title, str):
                continue
            for target in panel.get("targets", []):
                expr = target.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    continue
                normalized_expr = " ".join(expr.split())
                observed_uses_by_expr.setdefault(normalized_expr, set()).add(
                    (dashboard_path.name, title)
                )

    duplicate_uses_by_expr = {
        expr: uses for expr, uses in observed_uses_by_expr.items() if len(uses) > 1
    }
    expected_duplicate_uses = _expected_duplicate_uses()
    assert duplicate_uses_by_expr == expected_duplicate_uses, (
        "Dashboard exact PromQL duplication drifted outside the audited allowlist: "
        f"{duplicate_uses_by_expr}"
    )
    _assert_dq_score_time_semantics()
    _assert_lineage_control_plane_ownership_handoff()
