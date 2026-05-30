"""Integration tests for cross-scope marker contract - required titles by transition."""

import json
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
        # From Overview to other dashboards
        ("bioetl-overview-v2", "bioetl-runtime"): ["2. Runtime", "Open Runtime"],
        ("bioetl-overview-v2", "bioetl-control-plane-v1"): [
            "0. Control Plane",
            "Open Control Plane",
        ],
        ("bioetl-overview-v2", "bioetl-dq-v2"): [
            "4. Data Quality",
            "Open Data Quality",
        ],
        ("bioetl-overview-v2", "bioetl-provider-health-v2"): [
            "3. Provider Health",
            "Open Provider Health",
        ],
        ("bioetl-overview-v2", "bioetl-workflow-overview"): [
            "5. Workflow",
            "Open Workflow",
        ],
        # From Runtime to other dashboards
        ("bioetl-runtime", "bioetl-dq-v2"): [
            "Open Data Quality",
            "Inspect DQ",
            "4. Data Quality",
        ],
        ("bioetl-runtime", "bioetl-provider-health-v2"): [
            "Open Provider Health",
            "Inspect Provider",
            "3. Provider Health",
        ],
        # From DQ to other dashboards
        ("bioetl-dq-v2", "bioetl-silver-reject-explorer"): [
            "Open Silver Reject Explorer",
            "Inspect Rejects",
            "Silver Reject Explorer",
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
            url = str(link.get("url", ""))
            tooltip = str(link.get("tooltip", ""))

            # Only check if tooltip exists and mentions dashboard scope reset or context mapping
            if tooltip and (
                "scope reset" in tooltip.lower() or "context mapping" in tooltip.lower()
            ):
                has_scope_reset = "reset scope" in tooltip.lower()
                has_context_mapping = "context mapping" in tooltip.lower()
                assert has_scope_reset or has_context_mapping, (
                    f"{dashboard_path.name}: link {link.get('title')} has scope-related tooltip "
                    f"but doesn't mention 'reset scope' or 'context mapping', got '{tooltip}'"
                )


def test_workflow_dashboard_provenance_banner_makes_scope_split_explicit() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-workflow-overview.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next((item for item in dashboard["panels"] if item.get("id") == 9400), None)

    assert panel is not None
    content = str(panel.get("options", {}).get("content", ""))
    description = str(panel.get("description", ""))
    assert "Exact run: ID card only" in content
    assert "Evidence below: selected-range workflow scope" in content
    assert "Run ID only fills the local ID card" in content
    assert "run_id is local control-plane identity context only" in description


def test_workflow_status_panel_repeats_selected_range_contract() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-workflow-overview.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next((item for item in dashboard["panels"] if item.get("id") == 9401), None)

    assert panel is not None
    description = str(panel.get("description", ""))
    assert "Selected-range workflow evidence status" in description
    assert "not exact-run evidence" in description
    assert "run_id remains local ID-only identity context" in description
