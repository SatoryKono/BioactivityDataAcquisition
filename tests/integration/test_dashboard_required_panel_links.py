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
    """Selected-run domains retain CP/DQ/provider actions after retirement."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {p.get("id"): p for p in get_dashboard_panels(dashboard)}
    assert 9603 in panels and 9002 in panels and 9480 in panels
    links = panels[9002]["fieldConfig"]["defaults"]["links"]
    assert {link["title"] for link in links} == {
        "Open Control Plane",
        "Open Data Quality",
        "Open Provider Evidence",
    }
    assert all(link["includeVars"] is False for link in links)
    assert not ({214, 215} & set(panels)), (
        "Retired CURRENT fleet cards must stay absent"
    )


def test_dq_dashboard_required_panel_links():
    """bioetl-dq-v2: Check required panel links by panel ID."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels = {p.get("id"): p for p in get_dashboard_panels(dashboard)}

    assert 9102 not in panels
    assert 9406 in panels
    links = panels[9406].get("fieldConfig", {}).get("defaults", {}).get("links") or []
    assert any(link.get("title") == "Open Run Explorer" for link in links)


def test_retired_workflow_and_runtime_workspaces_stay_absent():
    """Workflow evidence is reached through saved run evidence, not retired UIDs."""
    for name in (
        "bioetl-workflow-overview",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
    ):
        assert not (Path("grafana/dashboards") / f"{name}.json").exists()
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    assert any(p["id"] == 9002 for p in get_dashboard_panels(overview))
