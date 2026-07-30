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
        "Inspect Run Identity Evidence",
    ),
    (
        "bioetl-control-plane-v1.json",
        "Inspect Audit & Lineage Evidence",
    ),
    (
        "bioetl-control-plane-v1.json",
        "Inspect Global Store Reliability",
    ),
    ("bioetl-control-plane-v1.json", "Inspect Manifest & Ledger Evidence"),
    (
        "bioetl-control-plane-v1.json",
        "Inspect Replay & Checkpoint Evidence",
    ),
    ("bioetl-control-plane-v1.json", "Inspect Run Details"),
    ("bioetl-dq-v2.json", "Range lane · debug evidence"),
    ("bioetl-dq-v2.json", "Run context (thin) -> Run Explorer hub"),
    ("bioetl-dq-v2.json", "Run Lane · Silver/Gold Rejects"),
    ("bioetl-dq-v2.json", "Now lane · validation diagnostics"),
    ("bioetl-incident-v1.json", "Domain suspect detail (forensics; collapsed)"),
    ("bioetl-overview-v2.json", "Inspect Alerts"),
    ("bioetl-overview-v2.json", "Inspect Domain Diagnostics"),
    ("bioetl-overview-v2.json", "Inspect Historical Trends"),
    ("bioetl-overview-v2.json", "Inspect Range Evidence"),
    ("bioetl-overview-v2.json", "Inspect Run Context"),
    ("bioetl-provider-health-v2.json", "Range / debug evidence"),
    ("bioetl-provider-health-v2.json", "Run context (thin) -> Run Explorer hub"),
    ("bioetl-provider-health-v2.json", "Selected Provider Detail"),
    ("bioetl-runtime.json", "Inspect Detection Signals"),
    ("bioetl-runtime.json", "Review Escalation Paths"),
    ("bioetl-runtime.json", "Localize Runtime Cause"),
    ("bioetl-runtime.json", "Inspect Run Context"),
    (
        "bioetl-runtime.json",
        "Inspect Secondary Runtime Indicators",
    ),
    ("bioetl-runtime.json", "Inspect Workflow Evidence"),
    ("bioetl-run-explorer-v1.json", "Selected Run Details"),
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
