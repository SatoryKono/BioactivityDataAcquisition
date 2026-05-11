"""Integration tests for required panel links by UID."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_overview_dashboard_required_panel_links():
    """bioetl-overview-v2: Check required panel links by panel ID."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {p.get("id"): p for p in get_dashboard_panels(dashboard)}

    # Panel 214 (System Status) should have dataLinks to specific dashboards
    panel_214 = panels.get(214)
    assert panel_214 is not None, "Panel 214 (System Status) must exist"
    data_links_214 = panel_214.get("fieldConfig", {}).get("defaults", {}).get("links", [])
    required_links_214 = ["Open Runtime", "Open Control Plane", "Open Data Quality", "Open Provider Health", "Open Workflow"]
    for required_link in required_links_214:
        assert any(required_link in link.get("title", "") for link in data_links_214), (
            f"Panel 214 must have dataLink '{required_link}'"
        )

    # Panel 215 (Next Action) should have dataLinks to specific dashboards
    panel_215 = panels.get(215)
    assert panel_215 is not None, "Panel 215 (Next Action) must exist"
    data_links_215 = panel_215.get("fieldConfig", {}).get("defaults", {}).get("links", [])
    for required_link in required_links_214:  # Same as System Status
        assert any(required_link in link.get("title", "") for link in data_links_215), (
            f"Panel 215 must have dataLink '{required_link}'"
        )


def test_dq_dashboard_required_panel_links():
    """bioetl-dq-v2: Check required panel links by panel ID."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels = {p.get("id"): p for p in get_dashboard_panels(dashboard)}

    # Panel 9102 (Inspect DQ Current Reasons) should have dataLink to Silver Reject Explorer
    panel_9102 = panels.get(9102)
    assert panel_9102 is not None, "Panel 9102 (Inspect DQ Current Reasons) must exist"
    data_links_9102 = panel_9102.get("fieldConfig", {}).get("defaults", {}).get("links", [])
    assert any("Silver Reject Explorer" in link.get("title", "") for link in data_links_9102), (
        "Panel 9102 must have dataLink to 'Open Silver Reject Explorer'"
    )
