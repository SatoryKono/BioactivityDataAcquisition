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


def test_dashboard_rows_follow_progressive_disclosure_shape() -> None:
    """Expanded rows keep children at root; collapsed forensic rows nest them."""
    collapsed_rows = 0
    expanded_rows = 0
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "row":
                continue
            title = panel.get("title", "")
            collapsed = panel.get("collapsed")
            assert isinstance(collapsed, bool), (
                f"{dashboard_path.name}: row {title!r} must declare collapsed"
            )
            nested = panel.get("panels") or []
            if collapsed:
                collapsed_rows += 1
                assert nested, (
                    f"{dashboard_path.name}: collapsed row {title!r} must nest "
                    "its forensic child panels"
                )
            else:
                expanded_rows += 1
                assert not nested, (
                    f"{dashboard_path.name}: expanded row {title!r} must not nest "
                    "child panels under row.panels (children live at root)"
                )

    # Design-system §4.3 (visibility tiers / collapse policy): forensic and
    # diagnostic rows are collapsed by default, and always-visible answer
    # surfaces live at root — not inside an expanded ``type: row``. A shipped
    # dashboard may therefore legitimately have zero expanded rows (all shipped
    # rows are forensic "Inspect …" groups today). Keep the per-row nesting-shape
    # assertions above; require only that at least one row exists. The >=20 row
    # floor is covered by ``test_every_dashboard_has_at_least_one_row``.
    assert collapsed_rows + expanded_rows > 0


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
