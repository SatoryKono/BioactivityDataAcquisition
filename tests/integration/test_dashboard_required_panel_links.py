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

    # Live alert/first-action cards are no longer selected-run evidence.
    assert 214 not in panels and 215 not in panels
    links = panels[9002]["links"]
    assert {link["title"] for link in links} == {
        "Open Control Plane",
        "Open Data Quality",
        "Open Provider Evidence",
    }
    assert all("${run_id:queryparam}" in link["url"] for link in links)
    assert all("${__url_time_range}" in link["url"] for link in links)


def test_dq_dashboard_required_panel_links():
    """bioetl-dq-v2: Check required panel links by panel ID."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels = {p.get("id"): p for p in get_dashboard_panels(dashboard)}

    assert 9102 not in panels
    assert 9406 in panels
    links = panels[9406].get("fieldConfig", {}).get("defaults", {}).get("links") or []
    assert any(link.get("title") == "Open Run Explorer" for link in links)


def test_workflow_overview_required_panel_links():
    """bioetl-workflow-overview retired; workflow-band lives on runtime."""
    from pathlib import Path

    workflow_overview = Path("grafana/dashboards/bioetl-workflow-overview.json")
    runtime = Path("grafana/dashboards/bioetl-runtime.json")
    incident = Path("grafana/dashboards/bioetl-incident-v1.json")
    assert not workflow_overview.exists(), (
        "bioetl-workflow-overview.json was retired (#6570/#6647); "
        "workflow-band evidence lives on bioetl-runtime"
    )
    assert not runtime.exists()
    assert incident.is_file()
    panels = {p["id"]: p for p in get_dashboard_panels(load_dashboard(incident))}
    assert {9996, 9997, 9701} <= set(panels)
