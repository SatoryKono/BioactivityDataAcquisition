#!/usr/bin/env python3
"""Render the canonical BioETL dashboard navigation bus (panel id=1000).

Generates sanitizer-safe HTML + machine-readable panel.links for every shipped
dashboard. Run from repo root:

    python scripts/ops/observability/grafana/render_nav_bus.py
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from scripts.ops.observability.grafana.action_target_routes import (
    ACTION_DASHBOARD_UID_BY_TARGET,
)
from scripts.ops.observability.grafana.dashboard_context_links import (
    build_handoff_url,
)

ROOT = Path(__file__).resolve().parents[4]
if __package__ in {None, ""}:
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
DASH_DIR = ROOT / "grafana" / "dashboards"

# Full portfolio bus (order is normative).
BUS: list[dict[str, str]] = [
    {
        "uid": "bioetl-control-plane-v1",
        "title": "0. Trust",
        "path": "bioetl-control-plane-v1",
    },
    {
        "uid": "bioetl-overview-v2",
        "title": "1. Overview",
        "path": "bioetl-overview-v2",
    },
    {
        "uid": "bioetl-runtime",
        "title": "2. Pipeline Diagnostics",
        "path": "bioetl-runtime",
    },
    {
        "uid": "bioetl-provider-health-v2",
        "title": "3. Provider Health",
        "path": "bioetl-provider-health-v2",
    },
    {
        "uid": "bioetl-dq-v2",
        "title": "4. Data Quality",
        "path": "bioetl-dq-v2",
    },
    {
        "uid": "bioetl-incident-v1",
        "title": "5. Incident Workspace",
        "path": "bioetl-incident-v1",
    },
    {
        "uid": "bioetl-run-explorer-v1",
        "title": "6. Run Explorer",
        "path": "bioetl-run-explorer-v1",
    },
]

FILE_BY_UID = {
    "bioetl-control-plane-v1": "bioetl-control-plane-v1.json",
    "bioetl-overview-v2": "bioetl-overview-v2.json",
    "bioetl-runtime": "bioetl-runtime.json",
    "bioetl-provider-health-v2": "bioetl-provider-health-v2.json",
    "bioetl-dq-v2": "bioetl-dq-v2.json",
    "bioetl-incident-v1": "bioetl-incident-v1.json",
    "bioetl-run-explorer-v1": "bioetl-run-explorer-v1.json",
}


def _validate_action_route_uids() -> None:
    """Fail closed when an action target points outside the shipped portfolio."""
    unknown = set(ACTION_DASHBOARD_UID_BY_TARGET.values()) - set(FILE_BY_UID)
    if unknown:
        raise SystemExit(
            f"action routes reference unknown dashboard UIDs: {sorted(unknown)}"
        )


NAV_DISPLAY_TITLE = "Navigate Dashboards"
NAV_HEIGHT = 4
# layout-budgets.yaml first_window_y / viewport_rows. Expanding nav must not
# push always-visible first-window panels past this fold.
VIEWPORT_ROWS = 18
# First-window copy that was explicitly designed and tested at h=3 must not be
# sacrificed when the shared navigation grows to its canonical h=4.
_MINIMUM_FIRST_WINDOW_HEIGHTS: dict[str, dict[int, int]] = {
    "bioetl-run-explorer-v1": {1: 3},
}
# Run Explorer's ten-row browse table has one row of layout slack after the
# navigation/provenance bands. Keep this explicit instead of turning arbitrary
# data panels into generic overflow donors.
_FALLBACK_COMPACTION_HEIGHTS: dict[str, dict[int, int]] = {
    "bioetl-run-explorer-v1": {3010: 11},
}
_CONTROL_PLANE_FIRST_WINDOW_GEOMETRY: dict[int, tuple[int, int, int, int]] = {
    9400: (0, 4, 16, 3),
    9401: (16, 4, 8, 3),
    9418: (0, 7, 12, 5),
    9416: (12, 7, 12, 5),
    906: (0, 12, 24, 3),
    891: (0, 15, 6, 3),
    892: (6, 15, 6, 3),
    893: (12, 15, 6, 3),
    907: (18, 15, 6, 3),
}
_CONTROL_PLANE_FIRST_DETAIL_ROW_Y = 18
NAV_TITLE_STYLE = "font-size:19px;font-weight:600;line-height:1;margin:0 2px"
CHIP_BASE = (
    "box-sizing:border-box;flex:1 1 0;min-width:0;text-align:center;padding:0 2px;"
    "border-radius:3px;font-weight:600;line-height:1.05;overflow-wrap:anywhere"
)
# Theme-safe chips: slate link surface works on dark and light Grafana themes.
LINK_STYLE = (
    f"{CHIP_BASE};color:#f8fafc;background:#334155;"
    "border:1px solid #94a3b8;text-decoration:none"
)
# Current chip: blue fill + cyan border + underline (not color-only).
# Rendered as <a aria-disabled> so Grafana HTML sanitizer keeps styles
# (bare <span aria-current> may lose attributes/styles in text panels).
CURRENT_STYLE = (
    f"{CHIP_BASE};color:#ffffff;background:#1d4ed8;border:2px solid #7dd3fc;"
    "cursor:default;text-decoration:underline;pointer-events:none"
)
CONTAINER_STYLE = (
    "display:flex;gap:2px;flex-wrap:nowrap;align-items:center;"
    "padding:0 2px;overflow:visible;white-space:normal;font-size:16px"
)
_PROVIDER_VARIABLE_UIDS = {"bioetl-provider-health-v2", "bioetl-incident-v1"}
_STAGE_TARGET_UIDS = {"bioetl-runtime", "bioetl-dq-v2"}
_PRESERVE_SCOPE_TOOLTIP = "Preserves selected scope and time range."

NAV_DESCRIPTION = (
    "Sanitizer-compatible navigation bus with native keyboard focus. "
    "Primary bus 0–4: Trust / Overview / Pipeline Diagnostics / Provider Health / "
    "Data Quality. Adjunct 5–6: Incident Workspace / Run Explorer. "
    "Current workspace is a non-interactive chip (aria-disabled + data-current=page, "
    "underlined) so active state is not color-only. Handoffs open same-tab, "
    "preserve current time range, and document scope reset or context mapping "
    "on cross-scope transitions. Chip colors are theme-safe for dark and light."
)


def _url_for(target: dict[str, str], *, source_uid: str) -> str:
    return build_handoff_url(target["uid"], source_uid=source_uid, template=True)


def _html_href(url: str) -> str:
    return (
        url.replace("&", "&amp;").replace("$", "$")  # keep template vars
    )


def nav_link_tooltip(*, source_uid: str, target: dict[str, str]) -> str:
    """Return operator tooltip copy for one nav-bus handoff.

    Cross-scope URL mutations from ``build_handoff_url`` are listed as
    ``Scope reset: ...``. Same-scope handoffs use the design-system preserve
    phrase. The tooltip never claims a selector the destination contract does
    not receive.
    """
    short = target["title"].split(". ", 1)[-1]
    base = f"{target['title']} ({short})"
    target_uid = target["uid"]
    resets: list[str] = []
    preserved: list[str] = ["time range"]
    if target_uid == "bioetl-provider-health-v2":
        if source_uid in _PROVIDER_VARIABLE_UIDS:
            preserved.append("provider")
        else:
            resets.append("provider=unknown")
        preserved.append("pipeline context")
    if target_uid in _STAGE_TARGET_UIDS:
        resets.append("stage=All")
    if source_uid == "bioetl-provider-health-v2" and target_uid != (
        "bioetl-provider-health-v2"
    ):
        preserved.append("pipeline via pipeline_context")
    if not resets:
        return f"{base}. {_PRESERVE_SCOPE_TOOLTIP}"
    preserve_clause = "; preserves " + ", ".join(dict.fromkeys(preserved)) + "."
    return f"{base}. Scope reset: {', '.join(resets)}{preserve_clause}"


def _chip_html(item: dict[str, str], *, current_uid: str, source_uid: str) -> str:
    short = item["title"].split(". ", 1)[-1]
    if item["uid"] == current_uid:
        title_attr = html.escape(f"{item['title']} ({short})", quote=True)
        # Anchor keeps inline styles under Grafana sanitizer; not in tab order.
        return (
            f'<a class="bioetl-nav-current" href="#{item["uid"]}" '
            f'aria-disabled="true" aria-current="page" data-current="page" '
            f'tabindex="-1" title="{title_attr}" style="{CURRENT_STYLE}">'
            f"{item['title']} (current)</a>"
        )
    tooltip = nav_link_tooltip(source_uid=source_uid, target=item)
    title_attr = html.escape(tooltip, quote=True)
    href = _html_href(_url_for(item, source_uid=source_uid))
    return (
        f'<a class="bioetl-nav-link" style="{LINK_STYLE}" title="{title_attr}" '
        f'href="{href}">{item["title"]}</a>'
    )


def render_html(*, current_uid: str) -> str:
    """Render the full seven-destination bus as one reflow-safe flex row."""
    primary = BUS[:5]
    adjunct = BUS[5:]
    parts: list[str] = [
        f'<div class="bioetl-panel-title" role="heading" aria-level="2" '
        f'data-bioetl-panel-title="{NAV_DISPLAY_TITLE}" '
        f'style="{NAV_TITLE_STYLE}">{NAV_DISPLAY_TITLE}</div>',
        f'<div class="bioetl-nav" role="navigation" '
        f'aria-label="BioETL dashboards" style="{CONTAINER_STYLE}">',
    ]
    for item in primary + adjunct:
        parts.append(_chip_html(item, current_uid=current_uid, source_uid=current_uid))
    parts.append("</div>")
    return "".join(parts)


def render_links(*, current_uid: str) -> list[dict[str, object]]:
    links: list[dict[str, object]] = []
    for item in BUS:
        if item["uid"] == current_uid:
            continue
        links.append(
            {
                "title": item["title"],
                "url": _url_for(item, source_uid=current_uid),
                "tooltip": nav_link_tooltip(source_uid=current_uid, target=item),
                "type": "link",
                "icon": "dashboard",
                "targetBlank": False,
                "keepTime": False,
                "includeVars": False,
                "asDropdown": False,
                "tags": [],
            }
        )
    return links


def _walk_panels(panels: list[object]) -> list[dict[str, object]]:
    discovered: list[dict[str, object]] = []
    stack = list(panels)
    while stack:
        panel = stack.pop(0)
        if not isinstance(panel, dict):
            continue
        discovered.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            stack[0:0] = nested
    return discovered


def _remove_obsolete_provider_handoff_variable(payload: dict[str, object]) -> None:
    templating = payload.setdefault("templating", {})
    if not isinstance(templating, dict):
        raise SystemExit("dashboard templating must be an object")
    variables = templating.setdefault("list", [])
    if not isinstance(variables, list):
        raise SystemExit("dashboard templating.list must be an array")
    variables[:] = [
        item
        for item in variables
        if not (
            isinstance(item, dict)
            and item.get("name") == "provider"
            and item.get("label") == "Provider handoff"
        )
    ]


_PROVIDER_HANDOFF_NEEDLE = "var-provider=$provider"
_PROVIDER_HANDOFF_UNKNOWN = "var-provider=unknown"


def _rewrite_provider_handoff_text(text: str) -> str:
    return text.replace(_PROVIDER_HANDOFF_NEEDLE, _PROVIDER_HANDOFF_UNKNOWN)


def _rewrite_mapping_provider_handoffs(value: dict[str, object]) -> None:
    for key, item in value.items():
        if isinstance(item, str):
            value[key] = _rewrite_provider_handoff_text(item)
        else:
            _fail_closed_provider_handoffs(item, provider_declared=False)


def _rewrite_list_provider_handoffs(value: list[object]) -> None:
    for index, item in enumerate(value):
        if isinstance(item, str):
            value[index] = _rewrite_provider_handoff_text(item)
        else:
            _fail_closed_provider_handoffs(item, provider_declared=False)


def _fail_closed_provider_handoffs(value: object, *, provider_declared: bool) -> None:
    if provider_declared:
        return
    if isinstance(value, dict):
        _rewrite_mapping_provider_handoffs(value)
        return
    if isinstance(value, list):
        _rewrite_list_provider_handoffs(value)


def _root_panels(panels: list[object]) -> list[dict[str, object]]:
    """Return root panels without collapsed-row children."""
    return [panel for panel in panels if isinstance(panel, dict)]


def _panel_grid(panel: object) -> dict[str, object] | None:
    if not isinstance(panel, dict):
        return None
    grid = panel.get("gridPos")
    return grid if isinstance(grid, dict) else None


def _panel_geometry(panel: object) -> tuple[dict[str, object], int, int] | None:
    grid = _panel_grid(panel)
    if grid is None:
        return None
    y = grid.get("y")
    height = grid.get("h")
    if not isinstance(y, int) or not isinstance(height, int):
        return None
    return grid, y, height


def _first_window_overflow(panels: list[object]) -> int:
    overflow = 0
    for panel in _root_panels(panels):
        geometry = _panel_geometry(panel)
        if panel.get("type") == "row" or geometry is None:
            continue
        _, y, height = geometry
        if 0 <= y < VIEWPORT_ROWS:
            overflow = max(overflow, y + height - VIEWPORT_ROWS)
    return overflow


def _slack_candidate(
    panel: dict[str, object],
    *,
    nav: dict[str, object],
    overflow: int,
) -> tuple[int, dict[str, object]] | None:
    geometry = _panel_geometry(panel)
    if panel is nav or panel.get("type") != "text" or geometry is None:
        return None
    _, y, height = geometry
    if panel.get("id") == 1000 or y >= VIEWPORT_ROWS or height - overflow < 3:
        return None
    return y, panel


def _shift_root_panels_up(
    panels: list[object],
    *,
    excluded_ids: frozenset[int],
    from_y: int,
    delta: int,
) -> None:
    for panel in _root_panels(panels):
        geometry = _panel_geometry(panel)
        if id(panel) in excluded_ids or geometry is None:
            continue
        grid, y, _ = geometry
        if y >= from_y:
            grid["y"] = y - delta


def _shift_root_panels_down(
    panels: list[object],
    *,
    excluded_ids: frozenset[int],
    from_y: int,
    delta: int,
) -> None:
    for panel in _root_panels(panels):
        geometry = _panel_geometry(panel)
        if id(panel) in excluded_ids or geometry is None:
            continue
        grid, y, _ = geometry
        if y >= from_y:
            grid["y"] = y + delta


def _restore_minimum_first_window_heights(
    panels: list[object], *, current_uid: str
) -> None:
    minimums = _MINIMUM_FIRST_WINDOW_HEIGHTS.get(current_uid, {})
    by_id = {panel.get("id"): panel for panel in _root_panels(panels)}
    for panel_id, minimum_height in minimums.items():
        panel = by_id.get(panel_id)
        geometry = _panel_geometry(panel)
        if panel is None or geometry is None:
            raise SystemExit(
                f"{current_uid}: missing protected first-window panel id={panel_id}"
            )
        grid, y, height = geometry
        if height >= minimum_height:
            continue
        delta = minimum_height - height
        old_bottom = y + height
        grid["h"] = minimum_height
        _shift_root_panels_down(
            panels,
            excluded_ids=frozenset({id(panel)}),
            from_y=old_bottom,
            delta=delta,
        )


def _compact_shared_band(
    slack: dict[str, object],
    panels: list[object],
    *,
    nav: dict[str, object],
    overflow: int,
) -> None:
    geometry = _panel_geometry(slack)
    if geometry is None:  # pragma: no cover - candidates require geometry
        raise SystemExit("slack text rail is missing gridPos")
    _, y, height = geometry
    old_bottom = y + height
    band: list[dict[str, object]] = []
    for panel in _root_panels(panels):
        panel_geometry = _panel_geometry(panel)
        if panel is nav or panel.get("type") == "row" or panel_geometry is None:
            continue
        _, panel_y, panel_height = panel_geometry
        if panel_y == y and panel_y + panel_height == old_bottom:
            if panel_height - overflow < 3:
                raise SystemExit(
                    "navigation height expansion cannot compact a shared "
                    "first-window band below h=3"
                )
            band.append(panel)
    if not band:
        raise SystemExit("slack text rail has no compactable first-window band")
    for panel in band:
        panel_grid = _panel_grid(panel)
        if panel_grid is None:  # pragma: no cover - band requires geometry
            raise SystemExit("compactable first-window panel is missing gridPos")
        panel_grid["h"] = int(panel_grid["h"]) - overflow
    excluded = {id(nav)}
    excluded.update(id(panel) for panel in band)
    _shift_root_panels_up(
        panels,
        excluded_ids=frozenset(excluded),
        from_y=old_bottom,
        delta=overflow,
    )


def _compact_fallback_panel(
    panels: list[object], *, current_uid: str, overflow: int
) -> bool:
    minimums = _FALLBACK_COMPACTION_HEIGHTS.get(current_uid, {})
    for panel in _root_panels(panels):
        panel_id = panel.get("id")
        minimum_height = minimums.get(panel_id) if isinstance(panel_id, int) else None
        geometry = _panel_geometry(panel)
        if minimum_height is None or geometry is None:
            continue
        grid, y, height = geometry
        if y >= VIEWPORT_ROWS or y + height <= VIEWPORT_ROWS:
            continue
        if height - overflow < minimum_height:
            continue
        old_bottom = y + height
        grid["h"] = height - overflow
        _shift_root_panels_up(
            panels,
            excluded_ids=frozenset({id(panel)}),
            from_y=old_bottom,
            delta=overflow,
        )
        return True
    return False


def _normalize_collapsed_row_children(panels: list[object]) -> None:
    """Repair the one-row child drift left by legacy recursive nav shifts."""
    for row in _root_panels(panels):
        if row.get("type") != "row":
            continue
        children = row.get("panels")
        row_geometry = _panel_geometry(row)
        if not isinstance(children, list) or row_geometry is None:
            continue
        descendants = _walk_panels(children)
        child_geometries = [
            geometry
            for child in descendants
            if (geometry := _panel_geometry(child)) is not None
        ]
        if not child_geometries:
            continue
        _, row_y, _ = row_geometry
        offset = min(y for _, y, _ in child_geometries) - (row_y + 1)
        if offset not in {-1, 1}:
            continue
        for child_grid, child_y, _ in child_geometries:
            child_grid["y"] = child_y - offset


def _shift_panel_tree(panel: dict[str, object], *, delta: int) -> None:
    for descendant in _walk_panels([panel]):
        grid = _panel_grid(descendant)
        if grid is not None and isinstance(grid.get("y"), int):
            grid["y"] = int(grid["y"]) + delta


def _layout_control_plane_first_window(panels: list[object]) -> None:
    """Keep Trust density/readability while fitting the canonical h=4 nav."""
    root = _root_panels(panels)
    by_id = {panel.get("id"): panel for panel in root}
    missing = set(_CONTROL_PLANE_FIRST_WINDOW_GEOMETRY) - set(by_id)
    if missing:
        raise SystemExit(
            f"bioetl-control-plane-v1: missing layout panels {sorted(missing)}"
        )
    rows = [panel for panel in root if panel.get("type") == "row"]
    row_geometries = [
        geometry for row in rows if (geometry := _panel_geometry(row)) is not None
    ]
    if not row_geometries:
        raise SystemExit("bioetl-control-plane-v1: missing collapsed detail rows")
    first_row_y = min(y for _, y, _ in row_geometries)
    row_delta = _CONTROL_PLANE_FIRST_DETAIL_ROW_Y - first_row_y
    if row_delta:
        for panel in root:
            geometry = _panel_geometry(panel)
            if (
                geometry is None
                or panel.get("id") in _CONTROL_PLANE_FIRST_WINDOW_GEOMETRY
            ):
                continue
            _, y, _ = geometry
            if y >= first_row_y:
                _shift_panel_tree(panel, delta=row_delta)
    for panel_id, (x, y, width, height) in _CONTROL_PLANE_FIRST_WINDOW_GEOMETRY.items():
        grid = _panel_grid(by_id[panel_id])
        if grid is None:  # pragma: no cover - required panels have geometry
            raise SystemExit(
                f"bioetl-control-plane-v1: panel id={panel_id} missing gridPos"
            )
        grid.update({"x": x, "y": y, "w": width, "h": height})
    cta = by_id[906]
    cta["description"] = (
        "Next-step rail kept at readable h=3 on the first screen under the "
        "canonical h=4 navigation. Do not replay this run if its Trust status is "
        "INCOMPLETE or UNKNOWN. First-screen tables: Review Selected-Run Trust "
        "(9418) and Review Retention Compliance (9416). Review Lineage Validation "
        "is the first collapsed row (9419) and contains table 9415. Monitor Replay "
        "Readiness (9401) is current Prometheus for the pipeline, not this run."
    )


def _reclaim_first_window_overflow(
    nav: dict[str, object], panels: list[object], *, current_uid: str | None = None
) -> None:
    """Compact a safe first-window band so nav h=4 still fits the fold."""
    overflow = _first_window_overflow(panels)
    if overflow <= 0:
        return
    candidates = [
        candidate
        for panel in _root_panels(panels)
        if (candidate := _slack_candidate(panel, nav=nav, overflow=overflow))
        is not None
    ]
    if not candidates:
        if current_uid is not None and _compact_fallback_panel(
            panels, current_uid=current_uid, overflow=overflow
        ):
            return
        raise SystemExit(
            "navigation height expansion would overflow the first window and "
            "no protected layout band can reclaim the extra row"
        )
    _, slack = max(candidates, key=lambda item: item[0])
    _compact_shared_band(slack, panels, nav=nav, overflow=overflow)


def _expand_nav_height(
    nav: dict[str, object], panels: list[object], *, new_height: int
) -> None:
    grid_pos = nav.setdefault("gridPos", {})
    if not isinstance(grid_pos, dict):
        raise SystemExit("navigation panel gridPos must be an object")
    old_height = grid_pos.get("h")
    if not isinstance(old_height, int) or old_height >= new_height:
        return
    delta = new_height - old_height
    old_bottom = int(grid_pos.get("y", 0)) + old_height
    for panel in _root_panels(panels):
        if panel is nav:
            continue
        grid = panel.get("gridPos")
        if isinstance(grid, dict) and isinstance(grid.get("y"), int):
            if grid["y"] >= old_bottom:
                grid["y"] += delta


def apply_to_dashboard(path: Path, *, current_uid: str, check: bool = False) -> bool:
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    safe_path = ensure_path_within_root(path, DASH_DIR)
    payload = json.loads(
        safe_path.read_text(encoding="utf-8")  # NOSONAR - confined under DASH_DIR
    )
    _remove_obsolete_provider_handoff_variable(payload)
    _fail_closed_provider_handoffs(
        payload, provider_declared=current_uid in _PROVIDER_VARIABLE_UIDS
    )
    panels = payload.get("panels") or []
    nav = next((p for p in panels if p.get("id") == 1000), None)
    if nav is None:
        raise SystemExit(f"{safe_path.name}: missing panel id=1000")

    # Grafana 12 renders native panel headers at 14px and exposes no dashboard
    # JSON option for overriding that typography. Keep the native title empty
    # and render the operator-visible, accessible 19px title inside the
    # sanitizer-safe Text panel. Tooling reads bioetlDisplayTitle as metadata.
    nav["title"] = ""
    nav["type"] = "text"
    nav["description"] = NAV_DESCRIPTION
    _expand_nav_height(nav, panels, new_height=NAV_HEIGHT)
    # The inline 19px title plus the single-row, internally reflowing 16px chips
    # require four grid units at the normative 1366px viewport. Live geometry
    # validation guards clipping at 100% and 200% browser zoom.
    # Normalize all dashboards so content containment is an executable contract.
    grid_pos = nav["gridPos"]
    if not isinstance(grid_pos, dict):
        raise SystemExit("navigation panel gridPos must be an object")
    grid_pos["h"] = NAV_HEIGHT
    grid_pos.update({"w": 24, "x": 0, "y": 0})
    _restore_minimum_first_window_heights(panels, current_uid=current_uid)
    if current_uid == "bioetl-control-plane-v1":
        _layout_control_plane_first_window(panels)
    _reclaim_first_window_overflow(nav, panels, current_uid=current_uid)
    _normalize_collapsed_row_children(panels)
    nav["options"] = {
        "mode": "html",
        "bioetlDisplayTitle": NAV_DISPLAY_TITLE,
        "content": render_html(current_uid=current_uid),
    }
    bus_titles = {item["title"] for item in BUS}
    previous_links = nav.get("links") if isinstance(nav.get("links"), list) else []
    extra_links = [
        link
        for link in previous_links
        if isinstance(link, dict) and link.get("title") not in bus_titles
    ]
    nav["links"] = render_links(current_uid=current_uid) + extra_links
    # Drop stale transparent fields that confuse some exporters.
    nav.pop("transparent", None)

    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    current = safe_path.read_text(encoding="utf-8")
    if check:
        if current != serialized:
            print(f"drift {safe_path.name} current={current_uid!r}")
            return False
        print(f"ok {safe_path.name} current={current_uid!r}")
        return True
    write_path = ensure_path_within_root(safe_path, DASH_DIR)
    write_path.write_text(  # NOSONAR - write_path confined under DASH_DIR
        serialized,
        encoding="utf-8",
    )
    return True


def main(argv: list[str] | None = None) -> int:
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    _validate_action_route_uids()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when generated navigation differs without writing files",
    )
    args = parser.parse_args(argv)
    ok = True
    for item in BUS:
        uid = item["uid"]
        filename = FILE_BY_UID[uid]
        path = ensure_path_within_root(DASH_DIR / filename, DASH_DIR)
        if not path.exists():
            raise SystemExit(f"missing dashboard file: {path}")
        current_ok = apply_to_dashboard(path, current_uid=uid, check=args.check)
        ok = current_ok and ok
        if not args.check:
            print(f"updated {filename} current={item['title']!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
