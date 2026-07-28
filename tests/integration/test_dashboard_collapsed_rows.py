"""Integration tests for Grafana dashboard row visibility policy."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


PROGRESSIVE_DISCLOSURE_ROWS = {
    (
        "bioetl-control-plane-v1.json",
        "Identity evidence and remaining replay-safety signals",
    ),
    (
        "bioetl-control-plane-v1.json",
        "Incident Drilldown: Audit / Lineage Completeness",
    ),
    (
        "bioetl-control-plane-v1.json",
        "Incident Drilldown: Global Control-Plane Store Reliability",
    ),
    ("bioetl-control-plane-v1.json", "Incident Drilldown: Manifest / Ledger Integrity"),
    (
        "bioetl-control-plane-v1.json",
        "Incident Drilldown: Replay Safety (Checkpoint / Replay)",
    ),
    ("bioetl-control-plane-v1.json", "Run context (thin) → Run Explorer"),
    ("bioetl-dq-v2.json", "Range lane · debug evidence"),
    ("bioetl-dq-v2.json", "Run context (thin) → Run Explorer"),
    ("bioetl-dq-v2.json", "Run lane · Silver/Gold rejects"),
    ("bioetl-dq-v2.json", "Now lane · validation diagnostics"),
    ("bioetl-overview-v2.json", "Alert/SLO Triage"),
    ("bioetl-overview-v2.json", "Diagnostics & Docs (Logs / Traces / Raw Metrics)"),
    ("bioetl-overview-v2.json", "L1 Historical Trends"),
    ("bioetl-overview-v2.json", "Range Evidence (Historical / Recent History)"),
    ("bioetl-overview-v2.json", "Run context (thin) → Run Explorer"),
    ("bioetl-provider-health-v2.json", "Range / debug evidence"),
    ("bioetl-provider-health-v2.json", "Run context (thin) → Run Explorer"),
    ("bioetl-provider-health-v2.json", "Selected Provider Detail"),
    ("bioetl-runtime.json", "Detect"),
    ("bioetl-runtime.json", "Escalate"),
    ("bioetl-runtime.json", "Localize"),
    ("bioetl-runtime.json", "Run context (thin) → Run Explorer"),
    ("bioetl-runtime.json", "Runtime secondary KPIs"),
    ("bioetl-runtime.json", "Workflow band (merged from bioetl-workflow-overview)"),
    ("bioetl-run-explorer-v1.json", "Run report detail (Ops HTTP)"),
}


def test_dashboard_rows_follow_progressive_disclosure_policy():
    """Decision rows stay open; forensic/detail rows are one expand action away."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") == "row":
                title = panel.get("title", "")
                row_key = (dashboard_path.name, title)
                if row_key in PROGRESSIVE_DISCLOSURE_ROWS:
                    assert panel.get("collapsed") is True, (
                        f"{dashboard_path.name}: detail row {title!r} must stay "
                        "collapsed by default"
                    )
                    assert panel.get("panels"), (
                        f"{dashboard_path.name}: collapsed row {title!r} must keep "
                        "its child panels nested under row.panels"
                    )
                else:
                    assert panel.get("collapsed") is False, (
                        f"{dashboard_path.name}: row {title!r} must be expanded "
                        "by default"
                    )
                    assert not panel.get("panels"), (
                        f"{dashboard_path.name}: expanded row {title!r} must not "
                        "keep panels nested under row.panels"
                    )
                assert title, f"{dashboard_path.name}: row must have title"


def test_all_declared_progressive_disclosure_rows_exist() -> None:
    observed: set[tuple[str, str]] = set()
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        observed.update(
            (dashboard_path.name, str(panel.get("title")))
            for panel in get_dashboard_panels(dashboard)
            if panel.get("type") == "row" and panel.get("collapsed") is True
        )
    assert observed == PROGRESSIVE_DISCLOSURE_ROWS
