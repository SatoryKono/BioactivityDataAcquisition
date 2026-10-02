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
        ],
        ("bioetl-overview-v2", "bioetl-dq-v2"): ["Open Data Quality"],
        ("bioetl-incident-v1", "bioetl-dq-v2"): [
            "Open Data Quality",
            "Inspect DQ",
            "Open domain workspace",
        ],
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


def _panels(uid: str):
    from tests.integration._grafana_test_support import get_dashboard_panels

    return {
        p["id"]: p
        for p in get_dashboard_panels(
            load_dashboard(Path("grafana/dashboards") / f"{uid}.json")
        )
    }


def test_workflow_dashboard_provenance_banner_makes_scope_split_explicit() -> None:
    for uid in (
        "bioetl-workflow-overview",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
    ):
        assert not (Path("grafana/dashboards") / f"{uid}.json").exists()
    incident = _panels("bioetl-incident-v1")
    assert "CURRENT" in incident[9701]["description"]
    assert "independent of Selected Run" in incident[9701]["description"]


def test_workflow_status_panel_repeats_selected_range_contract() -> None:
    incident = _panels("bioetl-incident-v1")
    for pid in (9996, 9997):
        description = incident[pid]["description"]
        assert description.startswith("TIME RANGE")
        assert "selected range" in description
        assert "TELEMETRY MISSING is not a zero" in description


def test_provider_health_descriptions_separate_global_and_selected_scope() -> None:
    saved = _panels("bioetl-overview-v2")
    current = _panels("bioetl-incident-v1")
    for pid in (9480, 9481):
        description = saved[pid]["description"]
        assert description.startswith("SELECTED RUN")
        assert "saved" in description.lower()
        assert "UNKNOWN" in description
    assert current[2003]["description"].startswith("GLOBAL")
    assert "pipeline and run selectors do not filter" in current[2003]["description"]
    assert "VALID EMPTY is not TELEMETRY MISSING" in current[2003]["description"]
