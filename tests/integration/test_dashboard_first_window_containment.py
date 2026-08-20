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
    assert HORIZONTAL_SCROLL_ALLOWLIST == {}
    by_name = {path.name: load_dashboard(path) for path in get_dashboard_files()}
    for (dashboard_name, panel_id), meta in HORIZONTAL_SCROLL_ALLOWLIST.items():
        dashboard = by_name[dashboard_name]
        panel = next(
            item for item in _root_panels(dashboard) if item.get("id") == panel_id
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
        if item["dashboard"] not in {path.name for path in get_dashboard_files()}
    )
    assert not missing, f"first-window tables missing row-cap ownership: {missing}"
    assert not unbound, f"first-window tables exceed or lack a declared cap: {unbound}"
    assert not extra, f"row-cap contract refers to missing dashboards: {extra}"


def test_trust_9418_wraps_only_bounded_reasons_without_moving_fold() -> None:
    """#8975: one Trust row exposes top-3 reasons on the shipped first-screen grid."""
    dashboard_path = next(
        path
        for path in get_dashboard_files()
        if path.name == "bioetl-control-plane-v1.json"
    )
    dashboard = load_dashboard(dashboard_path)
    panel = next(item for item in _root_panels(dashboard) if item.get("id") == 9418)

    assert panel.get("gridPos") == {"h": 7, "w": 12, "x": 0, "y": 8}
    assert panel.get("options", {}).get("cellHeight") == "sm"
    defaults = panel.get("fieldConfig", {}).get("defaults", {}).get("custom", {})
    assert defaults.get("inspect") is True
    assert defaults.get("cellOptions", {}).get("wrapText") is not True

    limit = next(
        transform
        for transform in panel.get("transformations", [])
        if transform.get("id") == "limit"
    )
    assert limit.get("options", {}).get("limitField") == 1
    organize = next(
        transform
        for transform in panel.get("transformations", [])
        if transform.get("id") == "organize"
    ).get("options", {})
    assert organize.get("excludeByName") == {
        "reasons": True,
        "reasons_truncated": True,
    }
    assert organize.get("indexByName") == {
        "processing_status": 0,
        "trust_status": 1,
        "scope_kind": 2,
        "evidence_freshness": 3,
        "reasons_text": 4,
        "evidence_observed_at": 5,
    }

    override_properties = {
        override.get("matcher", {}).get("options"): {
            prop.get("id"): prop.get("value") for prop in override.get("properties", [])
        }
        for override in panel.get("fieldConfig", {}).get("overrides", [])
    }
    assert override_properties["reasons_text"]["custom.cellOptions"] == {
        "type": "auto",
        "wrapText": True,
    }
    assert override_properties["reasons_text"]["custom.inspect"] is True
    assert override_properties["reasons_text"]["custom.width"] >= 280
    assert override_properties["evidence_observed_at"]["custom.hidden"] is True
    assert override_properties["evidence_observed_at"]["unit"] == (
        "time:YYYY-MM-DD HH:mm"
    )
    assert {
        field
        for field, properties in override_properties.items()
        if properties.get("custom.cellOptions", {}).get("wrapText") is True
    } == {"reasons_text"}
    enum_fields = (
        "processing_status",
        "trust_status",
        "scope_kind",
        "evidence_freshness",
    )
    assert all(
        override_properties[field]["custom.cellOptions"].get("wrapText") is False
        for field in enum_fields
    )
    assert (
        sum(
            int(override_properties[field]["custom.width"])
            for field in (*enum_fields, "reasons_text")
        )
        == 655
    )


def test_trust_9416_hides_forensic_columns_without_wrapping_detail() -> None:
    """#9195: first-window retention table must fit w=12 without horizontal overflow."""
    dashboard_path = next(
        path
        for path in get_dashboard_files()
        if path.name == "bioetl-control-plane-v1.json"
    )
    dashboard = load_dashboard(dashboard_path)
    panel = next(item for item in _root_panels(dashboard) if item.get("id") == 9416)

    assert panel.get("gridPos") == {"h": 7, "w": 12, "x": 12, "y": 8}
    assert panel.get("options", {}).get("cellHeight") == "sm"
    defaults = panel.get("fieldConfig", {}).get("defaults", {}).get("custom", {})
    assert defaults.get("inspect") is True
    assert defaults.get("cellOptions", {}).get("wrapText") is not True

    limit = next(
        transform
        for transform in panel.get("transformations", [])
        if transform.get("id") == "limit"
    )
    assert limit.get("options", {}).get("limitField") == 5
    organize = next(
        transform
        for transform in panel.get("transformations", [])
        if transform.get("id") == "organize"
    ).get("options", {})
    assert organize.get("excludeByName") == {
        "endpoint": True,
        "retryable": True,
        "observed_at": True,
    }
    assert organize.get("indexByName") == {
        "check": 0,
        "status": 1,
        "reason": 2,
        "detail": 3,
    }

    override_properties = {
        override.get("matcher", {}).get("options"): {
            prop.get("id"): prop.get("value") for prop in override.get("properties", [])
        }
        for override in panel.get("fieldConfig", {}).get("overrides", [])
    }
    visible = ("check", "status", "reason", "detail")
    assert all(
        override_properties[field]["custom.cellOptions"].get("wrapText") is False
        for field in visible
    )
    assert override_properties["detail"]["custom.inspect"] is True
    assert sum(int(override_properties[field]["custom.width"]) for field in visible) == 655
    for hidden in ("endpoint", "retryable", "observed_at"):
        assert override_properties[hidden]["custom.hidden"] is True


def test_row_cap_contracts_are_unique_and_owned() -> None:
    seen: set[tuple[str, int]] = set()
    for item in first_window_summary_tables():
        key = (str(item["dashboard"]), int(item["id"]))
        assert key not in seen, f"duplicate row-cap contract {key}"
        seen.add(key)
        assert str(item["owner"]).startswith("@")
        assert item["bind"] in {"topk", "limit", "filter"}
        assert 1 <= int(item["max_rows"]) <= 5


def test_first_window_scope_banners_name_current_range_and_selected_run() -> None:
    """#8923: first-window scope copy must not conflate CURRENT / RANGE / SELECTED RUN."""
    required = {
        "bioetl-overview-v2.json": ("CURRENT", "SELECTED RUN", "TIME RANGE"),
        "bioetl-runtime.json": ("CURRENT", "SELECTED RUN"),
        "bioetl-provider-health-v2.json": ("GLOBAL", "SELECTED PROVIDER"),
        "bioetl-dq-v2.json": ("CURRENT", "SELECTED RUN", "TIME RANGE"),
        "bioetl-incident-v1.json": ("CURRENT", "SELECTED RUN"),
        "bioetl-run-explorer-v1.json": ("BROWSE", "SELECTED RUN"),
        "bioetl-control-plane-v1.json": ("CURRENT", "SELECTED RUN"),
    }
    by_name = {path.name: load_dashboard(path) for path in get_dashboard_files()}
    missing: list[str] = []
    for dashboard_name, tokens in required.items():
        dashboard = by_name[dashboard_name]
        first_window = select_first_window_panels(_root_panels(dashboard))
        blob = "\n".join(
            f"{panel.get('title', '')}\n{panel.get('description', '')}\n"
            f"{((panel.get('options') or {}).get('content') or '')}"
            for panel in first_window
            if panel.get("type") == "text"
        )
        for token in tokens:
            if token not in blob:
                missing.append(f"{dashboard_name} missing {token}")
    assert not missing, "first-window scope banners:\n" + "\n".join(missing)
