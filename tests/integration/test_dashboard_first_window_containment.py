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
"""First-window panel containment and summary-table row-cap contracts (#8896)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_CONTAINMENT_TYPES,
    FIRST_WINDOW_OVERFLOW_ALLOWLIST,
    FIRST_WINDOW_Y,
    HORIZONTAL_SCROLL_ALLOWLIST,
    PANEL_CONTAINMENT_TOLERANCE_PX,
    first_window_summary_tables,
    is_first_window_panel,
    panel_declared_row_cap,
    select_first_window_panels,
)
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    load_dashboard,
)


pytestmark = pytest.mark.integration


def _root_panels(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    return [panel for panel in dashboard.get("panels") or [] if isinstance(panel, dict)]


def test_first_window_panel_selection_is_root_non_row_below_fold() -> None:
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        root = _root_panels(dashboard)
        selected = select_first_window_panels(root)
        expected = [
            panel
            for panel in root
            if panel.get("type") != "row"
            and isinstance((panel.get("gridPos") or {}).get("y"), int)
            and int((panel.get("gridPos") or {})["y"]) < FIRST_WINDOW_Y
        ]
        assert [panel.get("id") for panel in selected] == [
            panel.get("id") for panel in expected
        ], dashboard_path.name
        assert all(is_first_window_panel(panel) for panel in selected)
        assert all(panel.get("type") != "row" for panel in selected)


def test_first_window_overflow_allowlist_stays_empty() -> None:
    assert FIRST_WINDOW_OVERFLOW_ALLOWLIST == {}
    assert PANEL_CONTAINMENT_TOLERANCE_PX == 2
    assert FIRST_WINDOW_CONTAINMENT_TYPES == frozenset({"text", "stat", "table"})


def test_horizontal_scroll_allowlist_is_below_fold_only() -> None:
    if not HORIZONTAL_SCROLL_ALLOWLIST:
        return
    by_name = {path.name: load_dashboard(path) for path in get_dashboard_files()}
    for (dashboard_name, panel_id), meta in HORIZONTAL_SCROLL_ALLOWLIST.items():
        dashboard = by_name[dashboard_name]
        panel = next(
            item
            for item in _root_panels(dashboard)
            if item.get("id") == panel_id
        )
        y = int((panel.get("gridPos") or {}).get("y") or 0)
        assert y >= FIRST_WINDOW_Y, (
            f"{dashboard_name}:{panel_id} horizontal-scroll allowlist is first-window"
        )
        assert meta.get("owner", "").strip()
        assert meta.get("rationale", "").strip()
        assert meta.get("retire_when", "").strip()


def test_every_first_window_table_owns_a_row_cap() -> None:
    contracts = first_window_summary_tables()
    owned = {(item["dashboard"], item["id"]): item for item in contracts}
    missing: list[str] = []
    unbound: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in select_first_window_panels(_root_panels(dashboard)):
            if panel.get("type") != "table":
                continue
            key = (dashboard_path.name, panel.get("id"))
            contract = owned.get(key)
            if contract is None:
                missing.append(f"{dashboard_path.name}:{panel.get('id')}")
                continue
            declared = panel_declared_row_cap(panel)
            if declared is None or declared > int(contract["max_rows"]):
                unbound.append(
                    f"{dashboard_path.name}:{panel.get('id')} "
                    f"declared={declared} max_rows={contract['max_rows']}"
                )
    extra = sorted(
        f"{item['dashboard']}:{item['id']}"
        for item in contracts
        if item["dashboard"]
        not in {path.name for path in get_dashboard_files()}
    )
    assert not missing, f"first-window tables missing row-cap ownership: {missing}"
    assert not unbound, f"first-window tables exceed or lack a declared cap: {unbound}"
    assert not extra, f"row-cap contract refers to missing dashboards: {extra}"


def test_row_cap_contracts_are_unique_and_owned() -> None:
    seen: set[tuple[str, int]] = set()
    for item in first_window_summary_tables():
        key = (str(item["dashboard"]), int(item["id"]))
        assert key not in seen, f"duplicate row-cap contract {key}"
        seen.add(key)
        assert str(item["owner"]).startswith("@")
        assert item["bind"] in {"topk", "limit", "filter"}
        assert 1 <= int(item["max_rows"]) <= 5
