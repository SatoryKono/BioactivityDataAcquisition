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
        # From Overview to other dashboards
        ("bioetl-overview-v2", "bioetl-runtime"): ["2. Runtime", "Open Runtime"],
        ("bioetl-overview-v2", "bioetl-control-plane-v1"): ["0. Control Plane", "Open Control Plane"],
        ("bioetl-overview-v2", "bioetl-dq-v2"): ["4. Data Quality", "Open Data Quality"],
        ("bioetl-overview-v2", "bioetl-provider-health-v2"): ["3. Provider Health", "Open Provider Health"],
        ("bioetl-overview-v2", "bioetl-workflow-overview"): ["5. Workflow", "Open Workflow"],
        # From Runtime to other dashboards
        ("bioetl-runtime", "bioetl-dq-v2"): ["Open Data Quality", "Inspect DQ", "4. Data Quality"],
        ("bioetl-runtime", "bioetl-provider-health-v2"): ["Open Provider Health", "Inspect Provider", "3. Provider Health"],
        # From DQ to other dashboards
        ("bioetl-dq-v2", "bioetl-silver-reject-explorer"): ["Open Silver Reject Explorer", "Inspect Rejects", "Silver Reject Explorer"],
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
    # Define required markers for specific transitions from section 17.2
    required_transitions = {
        # Reset scope transitions
        ("bioetl-control-plane-v1", "bioetl-workflow-overview"): "Reset scope",
        ("bioetl-provider-health-v2", "bioetl-workflow-overview"): "Reset scope",
        ("bioetl-overview-v2", "bioetl-workflow-overview"): "Reset scope",
        ("bioetl-runtime", "bioetl-workflow-overview"): "Reset scope",
        ("bioetl-dq-v2", "bioetl-workflow-overview"): "Reset scope",
        # Context mapping transitions
        ("bioetl-control-plane-v1", "bioetl-provider-health-v2"): "Context mapping",
        ("bioetl-provider-health-v2", "bioetl-overview-v2"): "Context mapping",
        ("bioetl-provider-health-v2", "bioetl-runtime"): "Context mapping",
        ("bioetl-provider-health-v2", "bioetl-control-plane-v1"): "Context mapping",
        ("bioetl-provider-health-v2", "bioetl-dq-v2"): "Context mapping",
        ("bioetl-overview-v2", "bioetl-provider-health-v2"): "Context mapping",
        ("bioetl-runtime", "bioetl-provider-health-v2"): "Context mapping",
        ("bioetl-dq-v2", "bioetl-provider-health-v2"): "Context mapping",
        ("bioetl-provider-health-v2", "bioetl-silver-reject-explorer"): "Context mapping",
        ("bioetl-silver-reject-explorer", "bioetl-provider-health-v2"): "Context mapping",
        ("bioetl-workflow-overview", "bioetl-provider-health-v2"): "Context mapping",
    }

    for (source_uid, target_uid), required_marker in required_transitions.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{source_uid}.json")
        links = _collect_dashboard_links(dashboard)

        for link in links:
            url = str(link.get("url", ""))
            tooltip = str(link.get("tooltip", ""))

            # Check if this link targets the expected dashboard
            if f"/d/{target_uid}/" in url:
                # Only check tooltip if it exists (some links may not have tooltips)
                if tooltip:
                    assert required_marker.lower() in tooltip.lower(), (
                        f"Link from {source_uid} to {target_uid} must have tooltip with "
                        f"'{required_marker}', got '{tooltip}'"
                    )

