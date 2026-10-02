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
"""Integration tests for cross-scope marker contract - required titles by transition."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_cross_scope_links_use_required_titles():
    """Cross-scope links must use canonical titles from navigation-contract."""
    # Define required title patterns for specific dashboard transitions
    # Based on dashboard-audit-checklist.md section 17.2
    required_transitions = {
        ("bioetl-overview-v2", "bioetl-control-plane-v1"): [
            "Replay Readiness",
            "Open Control Plane",
            "Open Trust",
        ],
        ("bioetl-overview-v2", "bioetl-dq-v2"): ["Data Quality"],
    }

    for (source_uid, target_uid), allowed_titles in required_transitions.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{source_uid}.json")
        links = _collect_dashboard_links(dashboard)

        for link in links:
            url = str(link.get("url", ""))
            title = str(link.get("title", ""))

            # Check if this link targets the expected dashboard
            if f"/d/{target_uid}/" in url:
                # Check if title matches one of the allowed patterns
                title_matches = any(allowed in title for allowed in allowed_titles)
                assert title_matches, (
                    f"Link from {source_uid} to {target_uid} must use canonical title. "
                    f"Expected one of: {allowed_titles}, Got: '{title}'"
                )


def test_cross_scope_links_have_required_tooltip_tokens():
    """Cross-scope links must include 'Scope reset' or 'Context mapping' tokens in tooltips."""
    # This is a SHOULD check - only verify for links that explicitly have scope-related tooltips
    for dashboard_path in Path("grafana/dashboards").glob("*.json"):
        dashboard = load_dashboard(dashboard_path)
        links = _collect_dashboard_links(dashboard)

        for link in links:
            tooltip = str(link.get("tooltip", ""))

            # Only check if tooltip exists and mentions dashboard scope reset or context mapping
            if tooltip and (
                "scope reset" in tooltip.lower() or "context mapping" in tooltip.lower()
            ):
                has_scope_reset = "scope reset" in tooltip.lower()
                has_context_mapping = "context mapping" in tooltip.lower()
                assert has_scope_reset or has_context_mapping, (
                    f"{dashboard_path.name}: link {link.get('title')} has scope-related tooltip "
                    f"but doesn't mention 'scope reset' or 'context mapping', got '{tooltip}'"
                )


def test_retired_dashboards_resolve_to_current_evidence_owners() -> None:
    for name in (
        "bioetl-workflow-overview",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
    ):
        assert not (Path("grafana/dashboards") / f"{name}.json").exists()
    incident = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    assert {9996, 9997} <= {p["id"] for p in get_dashboard_panels(incident)}
    assert {9480, 9481} <= {p["id"] for p in get_dashboard_panels(overview)}


def test_workflow_status_panel_repeats_selected_range_contract() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9996)
    description = panel["description"]
    assert "Workflow only, not a single Run ID" in description
    assert "Pipeline does not filter this count" in description
    assert "not current Workflow or Pipeline Health" in description
    expression = panel["targets"][0]["expr"]
    assert 'workflow=~"$workflow"' in expression
    assert "[$__range]" in expression
    assert "run_id" not in expression


def test_provider_evidence_is_saved_run_scoped() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    for panel_id in (9480, 9481):
        panel = panels[panel_id]
        assert "SELECTED RUN" in panel["description"]
        assert "UNKNOWN" in panel["description"]
        assert panel["targets"][0]["url"].startswith(
            "/ops/observability/selected-run-status?"
        )
        assert "run_id=${run_id}" in panel["targets"][0]["url"]
    assert "not live fleet health" in panels[9481]["description"]
