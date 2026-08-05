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


def test_dashboard_rows_are_expanded_by_default() -> None:
    """Operator policy: all panel groups ship expanded (no collapsed rows)."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "row":
                continue
            title = panel.get("title", "")
            assert panel.get("collapsed") is False, (
                f"{dashboard_path.name}: row {title!r} must be expanded by default"
            )
            nested = panel.get("panels") or []
            assert len(nested) == 0, (
                f"{dashboard_path.name}: expanded row {title!r} must not nest "
                "child panels under row.panels (children live at root)"
            )


def test_every_dashboard_has_at_least_one_row() -> None:
    observed = 0
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        rows = [
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("type") == "row"
        ]
        assert rows, f"{dashboard_path.name} must declare at least one row group"
        observed += len(rows)
    assert observed >= 20
