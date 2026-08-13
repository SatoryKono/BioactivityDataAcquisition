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
    materialize_expanded,
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

    # Operator policy: panel groups are EXPANDED at the testing/audit stage and
    # COLLAPSED in production. The shipped ``grafana/dashboards/*.json`` is the
    # production artifact, so every row group must ship collapsed with its
    # children nested (progressive disclosure, design-system §4.3). Test tooling
    # materializes the expanded content in-memory via ``get_dashboard_panels``,
    # which walks nested ``row.panels`` — that does not change the shipped state.
    assert collapsed_rows > 0, "expected at least one collapsed row group"
    assert expanded_rows == 0, (
        f"production dashboards must ship all row groups collapsed; found "
        f"{expanded_rows} expanded row(s). Expansion is a test/audit-time "
        "materialization, not a shipped state."
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


def test_row_groups_materialize_expanded_for_test_stage() -> None:
    """Test-stage expansion: every shipped row group expands cleanly.

    Operator policy: EXPANDED at the testing/audit stage, COLLAPSED in
    production. ``materialize_expanded`` produces the test-stage view; verify it
    has no collapsed rows, hoists all children to root, preserves the panel
    count, and never mutates the cached shipped (production) dashboard.
    """
    for dashboard_path in get_dashboard_files():
        shipped = load_dashboard(dashboard_path)
        shipped_total = len(get_dashboard_panels(shipped))

        materialized = materialize_expanded(shipped)
        root_panels = materialized["panels"]
        rows = [panel for panel in root_panels if panel.get("type") == "row"]
        assert rows, f"{dashboard_path.name}: expected at least one row group"
        for row in rows:
            assert row.get("collapsed") is False, (
                f"{dashboard_path.name}: row {row.get('title')!r} must be "
                "expanded in the materialized test-stage view"
            )
            assert not (row.get("panels") or []), (
                f"{dashboard_path.name}: row {row.get('title')!r} must hoist its "
                "children to root when expanded"
            )

        assert len(get_dashboard_panels(materialized)) == shipped_total, (
            f"{dashboard_path.name}: expansion must not add or drop panels"
        )
        assert all(
            panel.get("collapsed") is True
            for panel in shipped["panels"]
            if panel.get("type") == "row"
        ), (
            f"{dashboard_path.name}: materialize_expanded must not mutate the "
            "shipped (production) dashboard, which stays collapsed"
        )
