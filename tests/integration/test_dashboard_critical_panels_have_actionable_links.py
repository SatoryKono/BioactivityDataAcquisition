"""Integration tests for critical panel actionable links."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def _iter_panel_data_links(panel: dict) -> list[dict]:
    """Extract dataLinks from panel options and fieldConfig."""
    result: list[dict] = []
    options = panel.get("options")
    if isinstance(options, dict):
        links = options.get("dataLinks", [])
        if isinstance(links, list):
            result.extend(link for link in links if isinstance(link, dict))

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    if isinstance(defaults, dict):
        field_links = defaults.get("links", [])
        if isinstance(field_links, list):
            result.extend(link for link in field_links if isinstance(link, dict))
    return result


def test_p1_p2_panels_have_data_links():
    """P1/P2 operator panels should have dataLinks where applicable."""
    # Definition of P1/P2 panels by title/role
    p1_p2_patterns = {
        "Status",
        "Runtime Status",
        "Current Status",
        "Severity Matrix",
        "Runtime Blockers",
        "Blockers",
        "Top Causes",
    }
    # Skip panels that are trend/summary only
    skip_patterns = ["Trend", "Rate", "Overview", "Outcomes", "Events", "Duration"]
    # Skip workflow-overview entirely (different role - selected-range evidence surface)
    skip_dashboards = ["bioetl-workflow-overview.json"]
    for dashboard_path in get_dashboard_files():
        if dashboard_path.name in skip_dashboards:
            continue
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            if title in p1_p2_patterns:
                # Skip trend/summary panels
                if any(skip in title for skip in skip_patterns):
                    continue
                data_links = _iter_panel_data_links(panel)
                assert len(data_links) >= 1, (
                    f"{dashboard_path.name}:{title} must have at least one dataLink"
                )


def test_runbook_links_follow_canonical_format():
    """Runbook links must use canonical GitHub blob pattern."""
    canonical_prefix = "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/"
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            for link in _iter_panel_data_links(panel):
                url = link.get("url", "")
                title = link.get("title", "")
                if "runbook" in title.lower():
                    assert url.startswith(canonical_prefix), (
                        f"{dashboard_path.name}:{title} runbook link must use "
                        f"canonical GitHub blob pattern, got {url!r}"
                    )


def test_critical_panels_have_open_target_pattern():
    """Critical panel dashboard links should start with 'Open <target>' pattern."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title", "")
            # Check for critical panels
            if title in {
                "Status",
                "Runtime Status",
                "Current Status",
                "Runtime Blockers",
                "Blockers",
                "Severity Matrix",
                "Top Causes",
            }:
                data_links = _iter_panel_data_links(panel)
                for link in data_links:
                    link_title = link.get("title", "")
                    # Check if it's a dashboard link
                    url = link.get("url", "")
                    if url.startswith("/d/"):
                        # Allow "Open ", "Inspect ", and "Review " patterns
                        assert link_title.startswith(("Open ", "Inspect ", "Review ")), (
                            f"{dashboard_path.name}:{title} dashboard link title "
                            f"must start with 'Open ', 'Inspect ', or 'Review ', got {link_title!r}"
                        )
