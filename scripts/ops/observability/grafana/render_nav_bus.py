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

from scripts.ops.observability.grafana._latest_complete_run_panel import (
    stamp_latest_complete_run_panel,
)
from scripts.ops.observability.grafana._selected_run_panels import (
    stamp_selected_run_panels,
    stamp_selector_columns,
)
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
CUSTOM_WIDTH = "custom.width"

# Full portfolio bus (order is normative).
BUS: list[dict[str, str]] = [
    {
        "uid": "bioetl-run-explorer-v1",
        "title": "0. Run Explorer",
        "path": "bioetl-run-explorer-v1",
    },
    {
        "uid": "bioetl-control-plane-v1",
        "title": "1. Trust",
        "path": "bioetl-control-plane-v1",
    },
    {
        "uid": "bioetl-overview-v2",
        "title": "2. Overview",
        "path": "bioetl-overview-v2",
    },
    {
        "uid": "bioetl-runtime",
        "title": "3. Pipeline Diagnostics",
        "path": "bioetl-runtime",
    },
    {
        "uid": "bioetl-provider-health-v2",
        "title": "4. Provider Health",
        "path": "bioetl-provider-health-v2",
    },
    {
        "uid": "bioetl-dq-v2",
        "title": "5. Data Quality",
        "path": "bioetl-dq-v2",
    },
    {
        "uid": "bioetl-incident-v1",
        "title": "6. Incident Workspace",
        "path": "bioetl-incident-v1",
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
NAV_HEIGHT = 2
# Shared link-only band reserves two wrapped rows with native 16px links.
# Verify narrow/200% reflow in the browser after Grafana sanitization.
# layout-budgets.yaml first_window_y / viewport_rows. Expanding nav must not
# push always-visible first-window panels past this fold.
VIEWPORT_ROWS = 18
# 1366x768 kiosk pixel fold fits non-row bottoms at y+h <= 17. A panel that
# ends on 18 is on the grid fold but overflows the measured first viewport.
FIRST_WINDOW_PANEL_BOTTOM = 17
# First-window copy that was explicitly designed and tested at h=3 must not be
# sacrificed when the shared navigation grows to its canonical h=4.
_MINIMUM_FIRST_WINDOW_HEIGHTS: dict[str, dict[int, int]] = {
    "bioetl-run-explorer-v1": {1: 3, 3010: 12},
    "bioetl-incident-v1": {2005: 4, 2010: 4},
    "bioetl-dq-v2": {9102: 4, 9406: 4},
    "bioetl-control-plane-v1": {9418: 7, 9416: 7},
}
# Donors used when the provenance text rail is already at h=3. Values are the
# minimum height after reclaiming one native-zoom nav row.
_FALLBACK_COMPACTION_HEIGHTS: dict[str, dict[int, int]] = {
    "bioetl-run-explorer-v1": {3010: 10},
    "bioetl-overview-v2": {215: 5, 9002: 5},
    "bioetl-provider-health-v2": {9101: 4, 9107: 4},
}
_CONTROL_PLANE_FIRST_WINDOW_GEOMETRY: dict[int, tuple[int, int, int, int]] = {
    9400: (0, 3, 16, 3),
    9401: (16, 3, 8, 3),
    9418: (0, 6, 12, 7),
    9416: (12, 6, 12, 7),
    891: (0, 13, 6, 4),
    892: (6, 13, 6, 4),
    893: (12, 13, 6, 4),
    907: (18, 13, 6, 4),
}
_CONTROL_PLANE_FIRST_DETAIL_ROW_Y = 17
_INCIDENT_FIRST_WINDOW_GEOMETRY: dict[int, tuple[int, int, int, int]] = {
    2001: (0, 6, 24, 2),
    2010: (0, 8, 24, 5),
    2005: (0, 13, 24, 4),
}
_DQ_FIRST_WINDOW_GEOMETRY: dict[int, tuple[int, int, int, int]] = {
    9101: (0, 8, 8, 4),
    9102: (8, 8, 16, 4),
    9406: (0, 12, 24, 5),
}
_RECOVERY_ACTION_HTML = (
    '<div style="padding:4px 10px;border-left:4px solid #6b7280;line-height:1.2;'
    'font-size:16px;white-space:normal;overflow-wrap:anywhere;max-width:96ch">'
    "CURRENT · Pipeline / Run Type readiness is shown at right.<br>"
    "SELECTED RUN · Do not replay while Trust is INCOMPLETE or UNKNOWN. "
    "Check retention below.</div>"
)
CHIP_BASE = (
    "box-sizing:border-box;flex:1 1 auto;min-width:0;text-align:center;padding:0 8px;"
    "border-radius:3px;font-weight:600;line-height:1.05;overflow-wrap:anywhere"
)
# Theme-safe chips: slate link surface works on dark and light Grafana themes.
LINK_STYLE = (
    f"{CHIP_BASE};color:#f8fafc;background:#334155;"
    "border:2px solid #94a3b8;text-decoration:none"
)
# Current chip: blue fill + cyan border + underline (not color-only).
# Rendered as <a aria-disabled> so Grafana HTML sanitizer keeps styles
# (bare <span aria-current> may lose attributes/styles in text panels).
CURRENT_STYLE = (
    f"{CHIP_BASE};color:#ffffff;background:#1d4ed8;border:2px solid #7dd3fc;"
    "cursor:default;text-decoration:underline;pointer-events:none"
)
CONTAINER_STYLE = (
    "display:flex;gap:8px;flex-wrap:wrap;align-items:center;"
    "padding:0 2px;overflow:visible;white-space:normal;font-size:16px"
)
_PROVIDER_VARIABLE_UIDS = {"bioetl-provider-health-v2", "bioetl-incident-v1"}
_STAGE_TARGET_UIDS = {"bioetl-runtime", "bioetl-dq-v2"}
_PRESERVE_SCOPE_TOOLTIP = "Preserves selected scope and time range."

NAV_DESCRIPTION = (
    "Sanitizer-compatible navigation bus with native keyboard focus. "
    "Shared link-only bus 0–6: Run Explorer / Trust / Overview / "
    "Pipeline Diagnostics / Provider Health / Data Quality / Incident Workspace. "
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
            resets.append("provider=All")
        preserved.append("pipeline context")
    if target_uid in _STAGE_TARGET_UIDS:
        resets.append("stage=All")
    if source_uid == "bioetl-provider-health-v2" and target_uid != (
        "bioetl-provider-health-v2"
    ):
        preserved.append("visible pipeline selection")
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
            f"{item['title']}</a>"
        )
    tooltip = nav_link_tooltip(source_uid=source_uid, target=item)
    title_attr = html.escape(tooltip, quote=True)
    href = _html_href(_url_for(item, source_uid=source_uid))
    return (
        f'<a class="bioetl-nav-link" style="{LINK_STYLE}" title="{title_attr}" '
        f'href="{href}">{item["title"]}</a>'
    )


def render_html(*, current_uid: str) -> str:
    """Render the full seven-destination bus as reflowing flex rows."""
    parts: list[str] = [
        f'<div class="bioetl-nav" role="navigation" '
        f'aria-label="BioETL dashboards" '
        f'style="{CONTAINER_STYLE}">',
    ]
    for item in BUS:
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
_PROVIDER_HANDOFF_UNKNOWN = "var-provider=All"


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
            overflow = max(overflow, y + height - FIRST_WINDOW_PANEL_BOTTOM)
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


def _fallback_compaction_anchor(
    panel: dict[str, object],
    *,
    minimums: dict[int, int],
    overflow: int,
) -> tuple[int, int] | None:
    panel_id = panel.get("id")
    minimum_height = minimums.get(panel_id) if isinstance(panel_id, int) else None
    geometry = _panel_geometry(panel)
    if minimum_height is None or geometry is None:
        return None
    _, y, height = geometry
    if y >= VIEWPORT_ROWS or height - overflow < minimum_height:
        return None
    return y, y + height


def _fallback_sibling_joins_band(
    sibling: dict[str, object],
    *,
    band_y: int,
    old_bottom: int,
    overflow: int,
    minimums: dict[int, int],
) -> bool:
    if sibling.get("type") == "row":
        return False
    sibling_geometry = _panel_geometry(sibling)
    if sibling_geometry is None:
        return False
    _, sibling_y, sibling_height = sibling_geometry
    if sibling_y != band_y or sibling_y + sibling_height != old_bottom:
        return False
    sibling_id = sibling.get("id")
    sibling_min = minimums.get(sibling_id) if isinstance(sibling_id, int) else None
    compacted = sibling_height - overflow
    if sibling_min is not None:
        return compacted >= sibling_min
    return compacted >= 3


def _fallback_compaction_band(
    panels: list[object],
    *,
    y: int,
    old_bottom: int,
    overflow: int,
    minimums: dict[int, int],
) -> list[dict[str, object]]:
    return [
        sibling
        for sibling in _root_panels(panels)
        if _fallback_sibling_joins_band(
            sibling,
            band_y=y,
            old_bottom=old_bottom,
            overflow=overflow,
            minimums=minimums,
        )
    ]


def _apply_fallback_compaction(
    panels: list[object],
    band: list[dict[str, object]],
    *,
    old_bottom: int,
    overflow: int,
) -> None:
    for sibling in band:
        sibling_grid = _panel_grid(sibling)
        if sibling_grid is None:
            raise SystemExit("fallback compaction panel is missing gridPos")
        sibling_grid["h"] = int(sibling_grid["h"]) - overflow
    _shift_root_panels_up(
        panels,
        excluded_ids=frozenset({id(sibling) for sibling in band}),
        from_y=old_bottom,
        delta=overflow,
    )


def _compact_fallback_panel(
    panels: list[object], *, current_uid: str, overflow: int
) -> bool:
    minimums = _FALLBACK_COMPACTION_HEIGHTS.get(current_uid, {})
    for panel in _root_panels(panels):
        anchor = _fallback_compaction_anchor(
            panel, minimums=minimums, overflow=overflow
        )
        if anchor is None:
            continue
        y, old_bottom = anchor
        band = _fallback_compaction_band(
            panels,
            y=y,
            old_bottom=old_bottom,
            overflow=overflow,
            minimums=minimums,
        )
        if not band:
            continue
        _apply_fallback_compaction(
            panels, band, old_bottom=old_bottom, overflow=overflow
        )
        return True
    return False


def _organize_control_plane_status_columns(panel: dict[str, object]) -> None:
    panel_id = panel.get("id")
    for transform in panel.get("transformations", []):
        if transform.get("id") != "organize":
            continue
        options = transform.setdefault("options", {})
        # Keep one result column; checkpoint Result retains MISMATCH/MISSING/N/A.
        duplicate = "status" if panel_id in {9405, 9407} else "ui_status"
        options.setdefault("excludeByName", {})[duplicate] = True
        if panel_id in {9405, 9407}:
            options.setdefault("renameByName", {})["drilldown_label"] = "Action"
            options.setdefault("indexByName", {})["drilldown_label"] = 3


def _layout_control_plane_detail_panels(panels: list[object]) -> None:
    """Fill the operator-reviewed gaps using row-relative, repeatable geometry."""
    for panel in _walk_panels(panels):
        if panel.get("id") in {9405, 9406, 9407, 9408, 9409}:
            _organize_control_plane_status_columns(panel)
    layouts = {
        902: {134: (0, 11, 12), 5: (12, 11, 12), 135: (0, 17, 24)},
        903: {4: (0, 0, 12), 136: (12, 0, 12)},
        905: {
            9408: (0, 38, 24),
            9406: (0, 42, 24),
            9409: (0, 46, 24),
            139: (0, 50, 24),
        },
        9412: {9402: (0, 0, 24)},
    }
    for row in _root_panels(panels):
        layout = layouts.get(row.get("id"))
        if layout is None:
            continue
        base_y = row["gridPos"]["y"] + 1
        children = row.get("panels", [])
        for child in children:
            if (position := layout.get(child.get("id"))) is not None:
                x, offset, width = position
                child["gridPos"].update(x=x, y=base_y + offset, w=width)
        children.sort(key=lambda child: (child["gridPos"]["y"], child["gridPos"]["x"]))


def _normalize_overview_domain_snapshots(panels: list[object]) -> None:
    """Keep CURRENT detail verdicts aligned with the evidence-qualified summary."""
    domains = {
        9003: "runtime",
        9004: "dq",
        9005: "gold",
        9006: "control_plane",
        9013: "workflow",
    }
    for panel in _walk_panels(panels):
        domain = domains.get(panel.get("id"))
        if domain is None:
            continue
        panel["targets"] = [
            {
                "expr": (
                    "max by (pipeline) (bioetl_l0_input_status_selected{"
                    f'input="{domain}",pipeline=~"$pipeline",run_type=~"$run_type"'
                    '}) or label_replace(vector(3), "pipeline", "$pipeline", "", "")'
                ),
                "refId": "A",
                "format": "table",
                "instant": True,
            }
        ]
        panel["description"] = (
            "CURRENT snapshot · Same evidence-qualified domain verdict as Review Domain Status "
            "for the selected Pipeline and Run Type. Values are 0=OK, 1=WARN, 2=CRIT, "
            "and null/3=UNKNOWN. Missing coverage cannot be replaced by an unqualified "
            "L1 OK. Run ID does not filter CURRENT. Historical lifecycle tracks remain "
            "separate; this is not selected-run trust."
        )
    for panel in _walk_panels(panels):
        if panel.get("id") == 9031:
            panel["description"] = str(panel.get("description", "")).replace(
                "four-row Review Domain Status", "six-domain Review Domain Status"
            )


def _normalize_runtime_record_delta_scope(panels: list[object]) -> None:
    """Distinguish observed counter increases from persisted selected-run totals."""
    for panel in _walk_panels(panels):
        if panel.get("id") == 241:
            panel["description"] = (
                "TIME RANGE · Observed selected-range processed-record counter increases by Stage and Run Type "
                "for the selected Pipeline and Stage. Run ID does not filter this query. "
                "Prometheus increase estimates changes between scraped samples; the initial "
                "counter value is not an observed increase. These values can differ from "
                "persisted selected-run totals. Use Run Explorer for exact-run counts. "
                "An empty chart means no matching samples or unavailable telemetry, not "
                "successful processing. TELEMETRY MISSING is not a zero and not VALID EMPTY."
            )


def _layout_overview_detail_panels(panels: list[object]) -> None:
    """Keep small status tables compact while retaining all rows in scroll views."""
    layouts = {
        9600: {9601: (0, 0, 24, 4)},
        9030: {
            9031: (0, 0, 12, 7),
            9018: (12, 0, 12, 7),
            9019: (0, 7, 24, 6),
            9020: (0, 13, 24, 6),
        },
        9009: {
            9010: (0, 0, 12, 4),
            9011: (12, 0, 12, 4),
            9015: (0, 4, 24, 3),
        },
        9012: {
            9006: (0, 0, 12, 4),
            9003: (12, 0, 12, 4),
            9004: (0, 4, 12, 4),
            9007: (12, 4, 12, 4),
            9005: (0, 8, 12, 4),
            9013: (0, 12, 24, 4),
            9021: (0, 16, 24, 3),
        },
        30215: {20215: (0, 0, 24, 6)},
    }
    for row in _root_panels(panels):
        if (layout := layouts.get(row.get("id"))) is None:
            continue
        base_y = row["gridPos"]["y"] + 1
        children = row.get("panels", [])
        for child in children:
            if (position := layout.get(child.get("id"))) is not None:
                x, offset, width, height = position
                child["gridPos"].update(x=x, y=base_y + offset, w=width, h=height)
        children.sort(key=lambda child: (child["gridPos"]["y"], child["gridPos"]["x"]))


def _clear_run_column_width(child: dict[str, object]) -> None:
    for override in child["fieldConfig"]["overrides"]:
        if override.get("matcher", {}).get("options") in {"Run", "run_id"}:
            override["properties"] = [
                prop
                for prop in override["properties"]
                if prop["id"] != CUSTOM_WIDTH
            ]


def _stamp_duration_quantile(child: dict[str, object]) -> None:
    for target in child.get("targets", []):
        expr = target.get("expr", "")
        if expr and not expr.endswith(" >= 0"):
            target["expr"] = f"({expr}) >= 0"
    field_config = child.setdefault("fieldConfig", {})
    defaults = field_config.setdefault("defaults", {})
    custom = defaults.setdefault("custom", {})
    custom["showPoints"] = "always"
    child["description"] = (
        "TIME RANGE · Duration quantiles require observed histogram increments "
        "within the rate interval. An empty chart is UNKNOWN, not zero duration "
        "or a failed run. NaN quantiles are omitted; isolated valid observations "
        "are shown as points."
    )


def _layout_runtime_detail_panels(panels: list[object]) -> None:
    """Fill detail rows and preserve explicit absence of duration observations."""
    layouts = {
        252: {220: (0, 22, 24, 3)},
        253: {9991: (0, 12, 24, 2)},
        254: {
            230: (0, 3, 8, 4),
            236: (8, 3, 8, 4),
            21: (16, 3, 8, 4),
            4: (0, 10, 8, 4),
            5: (8, 10, 8, 4),
            6: (16, 10, 8, 4),
            259: (0, 14, 12, 4),
            7: (12, 14, 12, 4),
        },
        9992: {237: (0, 0, 8, 4), 16: (8, 0, 8, 4), 205: (16, 0, 8, 4)},
        9993: {9998: (0, 6, 24, 4)},
        9994: {9996: (0, 0, 12, 4), 9997: (12, 0, 12, 4)},
        32460: {22460: (0, 0, 24, 6), 2461: (0, 6, 24, 6)},
    }
    for row in _root_panels(panels):
        layout = layouts.get(row.get("id"))
        if layout is None:
            continue
        base_y = row["gridPos"]["y"] + 1
        children = row.get("panels", [])
        for child in children:
            if position := layout.get(child.get("id")):
                x, offset, width, height = position
                child["gridPos"].update(x=x, y=base_y + offset, w=width, h=height)
            if child.get("id") == 9998:
                _clear_run_column_width(child)
            if child.get("id") in {207, 239}:
                _stamp_duration_quantile(child)
        children.sort(key=lambda child: (child["gridPos"]["y"], child["gridPos"]["x"]))


def _layout_dq_detail_panels(panels: list[object]) -> None:
    """Keep paired DQ evidence panels aligned during Grafana grid compaction."""
    layouts = {
        220: {
            152: (0, 0, 24, 3),
            121: (0, 3, 12, 6),
            122: (12, 3, 12, 6),
            118: (0, 9, 12, 6),
            156: (12, 9, 12, 6),
        },
        221: {
            12: (0, 9, 12, 4),
            151: (12, 9, 12, 4),
            10: (0, 13, 12, 6),
            11: (12, 13, 12, 6),
            155: (0, 19, 12, 6),
            153: (12, 19, 12, 6),
            116: (0, 25, 24, 4),
            150: (0, 29, 24, 4),
        },
    }
    for row in _root_panels(panels):
        layout = layouts.get(row.get("id"))
        if layout is None:
            continue
        base_y = row["gridPos"]["y"] + 1
        children = row.get("panels", [])
        for child in children:
            if position := layout.get(child.get("id")):
                x, offset, width, height = position
                child["gridPos"].update(x=x, y=base_y + offset, w=width, h=height)
        children.sort(key=lambda child: (child["gridPos"]["y"], child["gridPos"]["x"]))


def _layout_incident_detail_panels(panels: list[object]) -> None:
    """Keep incident detail tables compact and the run column flexible."""
    for row in _root_panels(panels):
        for child in row.get("panels", []):
            if child.get("id") in {22005, 22010}:
                child["gridPos"]["h"] = 6
            if child.get("id") == 2101:
                _clear_run_column_width(child)


def _clarify_manifest_counter_evidence(panels: list[object]) -> None:
    """Distinguish observed counter snapshots from sampled counter increments."""
    for row in _root_panels(panels):
        if row.get("id") != 901:
            continue
        base = row["gridPos"]["y"] + 1
        positions = {
            908: (0, 4),
            2: (4, 3),
            1: (4, 3),
            132: (4, 3),
            133: (4, 3),
            131: (7, 7),
            7: (14, 7),
            9414: (21, 6),
        }
        for child in row.get("panels", []):
            ident = child.get("id")
            if ident in positions:
                offset, height = positions[ident]
                child["gridPos"].update(y=base + offset, h=height)
            if ident == 908:
                child["title"] = "Review Observed Terminal Counters"
                child["description"] = (
                    "TIME RANGE · Selected range: last observed terminal counter by status, "
                    "summed across matching series. Pipeline applies; Run ID and Run Type do "
                    "not. This is a counter snapshot, not an exact-run verdict or a count of "
                    "events within the range. A first sample of 1 followed by 1 has observed "
                    "value 1 but measured increase 0. No matching series is a valid empty "
                    "state (UNKNOWN), not a zero. TELEMETRY MISSING is not a zero."
                )
                child["targets"][0].update(
                    expr='sum by (terminal_status) (last_over_time(bioetl_control_plane_terminal_events_total{pipeline=~"$pipeline"}[$__range]))',
                    format="table",
                    instant=True,
                )
                child["transformations"] = [
                    {
                        "id": "organize",
                        "options": {
                            "excludeByName": {"Time": True, "__name__": True},
                            "renameByName": {
                                "terminal_status": "Terminal status",
                                "Value": "Observed counter",
                            },
                        },
                    }
                ]
                child["fieldConfig"]["overrides"] = []
                child["fieldConfig"]["defaults"]["decimals"] = 0
            if ident == 131:
                child["title"] = "Track Observed Manifest Write Increments"
                child["description"] = (
                    "TIME RANGE · Sampled counter increase per interval, by run type and status. "
                    "Pipeline and Run Type apply; Run ID does not. Zero means no increase "
                    "between available samples, not no manifest writes. An event already "
                    "included in the first sample cannot be counted by increase(). Inspect "
                    "persisted run evidence for exact-run outcomes. Empty chart is UNKNOWN "
                    "telemetry, not a healthy zero. TELEMETRY MISSING is not a zero."
                )
                defaults = child["fieldConfig"]["defaults"]
                defaults.update(min=0, decimals=0)
                defaults.setdefault("custom", {}).update(
                    axisSoftMax=1, showPoints="always"
                )
                child["options"]["legend"]["calcs"] = ["lastNotNull", "max"]
        row["panels"].sort(
            key=lambda child: (child["gridPos"]["y"], child["gridPos"]["x"])
        )


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
        if offset == 0:
            continue
        for child_grid, child_y, _ in child_geometries:
            child_grid["y"] = child_y - offset


def _shift_panel_tree(panel: dict[str, object], *, delta: int) -> None:
    for descendant in _walk_panels([panel]):
        grid = _panel_grid(descendant)
        if grid is not None and isinstance(grid.get("y"), int):
            grid["y"] = int(grid["y"]) + delta


def _shift_control_plane_detail_rows(
    root: list[dict[str, object]], *, first_row_y: int
) -> None:
    row_delta = _CONTROL_PLANE_FIRST_DETAIL_ROW_Y - first_row_y
    if not row_delta:
        return
    protected = set(_CONTROL_PLANE_FIRST_WINDOW_GEOMETRY)
    for panel in root:
        geometry = _panel_geometry(panel)
        if geometry is None or panel.get("id") in protected:
            continue
        _, y, _ = geometry
        if y >= first_row_y:
            _shift_panel_tree(panel, delta=row_delta)


def _stamp_control_plane_recovery_cta(cta: dict[str, object]) -> None:
    cta["transparent"] = True
    options = cta.get("options")
    if not isinstance(options, dict):
        options = {}
        cta["options"] = options
    options["mode"] = "html"
    options["bioetlDisplayTitle"] = "Review Recovery Action"
    options["content"] = _RECOVERY_ACTION_HTML
    cta["description"] = (
        "Next-step rail kept at readable h=3 full width on the first screen under "
        "the canonical h=4 navigation. Trust/Retention tables compact to h=4 so "
        "the CTA does not share cells with the KPI strip. Do not replay this run "
        "if its Trust status is "
        "INCOMPLETE or UNKNOWN. First-screen tables: Review Selected-Run Trust "
        "(9418) and Review Retention Compliance (9416). Review Lineage Validation "
        "is the first collapsed row (9419) and contains table 9415. Monitor Current "
        "Readiness (9401) is current Prometheus for the pipeline, not this run."
    )


def _stamp_control_plane_counts(by_id: dict[object, dict[str, object]]) -> None:
    for panel_id in (891, 893, 907):
        if (count_panel := by_id.get(panel_id)) is None:
            continue
        for target in count_panel.get("targets", []):
            expression = target.get("expr", "")
            if expression and not expression.startswith("clamp_max("):
                target["expr"] = f"clamp_max({expression}, 2)"
        count_note = (
            " Counts map to 0=OK, 1=WARN, >=2=CRIT; absent evidence remains UNKNOWN."
        )
        description = count_panel.get("description", "")
        if count_note not in description:
            count_panel["description"] = description + count_note


def _stamp_recovery_copy(by_id: dict[object, dict[str, object]]) -> None:
    if 9400 not in by_id:
        return
    options = by_id[9400].setdefault("options", {})
    options["content"] = _RECOVERY_ACTION_HTML
    by_id[9400]["description"] = (
        "CURRENT readiness is pipeline/run_type telemetry. SELECTED RUN Trust "
        "and retention tables are exact-run persisted evidence. An incomplete "
        "selected run cannot be replayed even when current readiness is OK. "
        "Run coverage: IN RANGE / OUT OF RANGE / UNKNOWN. Set range to run when "
        "OUT OF RANGE. Effective refresh: 60s · timezone: browser."
    )


def _stamp_current_readiness(by_id: dict[object, dict[str, object]]) -> None:
    if 9401 not in by_id:
        return
    readiness = by_id[9401]
    readiness["title"] = "Monitor Current Readiness"
    field_config = readiness.setdefault("fieldConfig", {})
    defaults = field_config.setdefault("defaults", {})
    defaults["displayName"] = "Monitor Current Readiness"
    readiness["description"] = (
        "CURRENT · Latest fresh pipeline/run_type telemetry. Run ID does not filter "
        "this panel. Palette: 0=OK, 1=WARN, 2=CRIT, 3=INCOMPLETE, "
        "null=UNKNOWN. This CURRENT "
        "verdict is not exact-run processing_status or trust_status. OK here does "
        "not authorize replay: selected-run trust_status INCOMPLETE or UNKNOWN "
        "still blocks replay."
    )


def _stamp_retention_copy(by_id: dict[object, dict[str, object]]) -> None:
    if 9416 not in by_id:
        return
    retention = by_id[9416]
    note = (
        " Archive N/A means a referenced policy does not require archiving; "
        "it is not proof of an archive. Archive verified means local copies "
        "and restore evidence passed current hash and identity checks."
    )
    if note not in retention.get("description", ""):
        retention["description"] = retention.get("description", "") + note
    for override in retention.get("fieldConfig", {}).get("overrides", []):
        if override.get("matcher", {}).get("options") != "reason":
            continue
        for prop in override.get("properties", []):
            if prop.get("id") == "mappings":
                prop["value"][0]["options"].update(
                    {
                        "archive_not_applicable": {"text": "N/A: policy"},
                        "archive_restore_verified": {"text": "Archive verified"},
                        "archive_identity_mismatch": {"text": "Identity mismatch"},
                        "archive_checksum_mismatch": {"text": "Checksum mismatch"},
                        "archive_inventory_mismatch": {"text": "Files mismatch"},
                        "archive_source_mismatch": {"text": "Source changed"},
                        "archive_evidence_invalid": {"text": "Archive invalid"},
                        "archive_index_invalid": {"text": "Index invalid"},
                        "snapshot_lifecycle_evidence_present": {
                            "text": "Snapshots present"
                        },
                    }
                )


def _stamp_aggregate_trust(by_id: dict[object, dict[str, object]]) -> None:
    if 9418 not in by_id:
        return
    panel = by_id[9418]
    for link in panel.get("links", []):
        if "viewPanel=9414" in str(link.get("url", "")):
            link["title"] = "Inspect manifest checks"
    for target in panel.get("targets", []):
        url = target.get("url")
        if isinstance(url, str):
            target["url"] = url.replace("/manifest-validation?", "/trust-summary?")
            if (
                "/trust-summary?" in target["url"]
                and "error_as_row=" not in target["url"]
            ):
                target["url"] += "&error_as_row=1"
    panel["description"] = (
        "SELECTED RUN · Aggregate Trust includes manifest, lineage and retention "
        "evidence for this run. ERROR wins; missing evidence is INCOMPLETE. "
        "processing_status success does not imply trust_status OK. Inspect each "
        "validation table for details. No selected run is a valid empty state "
        "(UNKNOWN). Backend unavailable means QUERY ERROR; deadline_exceeded "
        "means the backend timed out, not that the run selection is missing. "
        "Result is the ETL processing outcome; Observed is the manifest "
        "creation time and is unavailable when the query fails."
    )
    for transform in panel.get("transformations", []):
        if transform.get("id") == "organize":
            transform.setdefault("options", {}).setdefault("renameByName", {}).update(
                {"processing_status": "Result", "evidence_observed_at": "Observed"}
            )
    options = panel.setdefault("options", {})
    footer = options.setdefault("footer", {})
    footer["enablePagination"] = True
    field_config = panel.setdefault("fieldConfig", {})
    field_config.setdefault("defaults", {})["noValue"] = (
        "Trust response unavailable. Check the panel error and run selection."
    )
    for override in field_config.setdefault("overrides", []):
        _stamp_trust_override(override)


def _set_override_value(override: dict[str, object], prop_id: str, value: object) -> None:
    for prop in override.get("properties", []):
        if prop.get("id") == prop_id:
            prop["value"] = value
            return


def _stamp_trust_override(override: dict[str, object]) -> None:
    matcher = override.get("matcher", {})
    field = matcher.get("options") if isinstance(matcher, dict) else None
    field = {"Processing": "Result", "Observed at": "Observed"}.get(field, field)
    if isinstance(matcher, dict):
        matcher["options"] = field
    if field == "processing_status":
        _set_override_value(override, "displayName", "Result")
    width = {"Result": 80, "Trust": 130, "Observed": 90}.get(field)
    if width is not None:
        _set_override_value(override, CUSTOM_WIDTH, width)
    if field == "reasons_text":
        _set_override_value(override, "noValue", "—")


def _layout_uid_detail_panels(panels: list[object], *, current_uid: str) -> None:
    if current_uid == "bioetl-runtime":
        _normalize_runtime_record_delta_scope(panels)
        _layout_runtime_detail_panels(panels)
        return
    if current_uid == "bioetl-control-plane-v1":
        _layout_control_plane_detail_panels(panels)
        _clarify_manifest_counter_evidence(panels)
        stamp_latest_complete_run_panel(panels)
        return
    if current_uid == "bioetl-overview-v2":
        _layout_overview_detail_panels(panels)
        _normalize_overview_domain_snapshots(panels)
        return
    if current_uid == "bioetl-dq-v2":
        _layout_dq_detail_panels(panels)
        return
    if current_uid == "bioetl-incident-v1":
        _layout_incident_detail_panels(panels)


def _layout_control_plane_first_window(panels: list[object]) -> None:
    """Keep Trust density/readability while fitting the canonical h=4 nav."""
    root = _root_panels(panels)
    rows = [panel for panel in root if panel.get("type") == "row"]
    row_geometries = [
        geometry for row in rows if (geometry := _panel_geometry(row)) is not None
    ]
    if not row_geometries:
        raise SystemExit("bioetl-control-plane-v1: missing collapsed detail rows")
    first_row_y = min(y for _, y, _ in row_geometries)
    _shift_control_plane_detail_rows(root, first_row_y=first_row_y)
    _apply_first_window_geometry(
        panels, _CONTROL_PLANE_FIRST_WINDOW_GEOMETRY, uid="bioetl-control-plane-v1"
    )
    by_id = {panel.get("id"): panel for panel in root}
    _stamp_control_plane_counts(by_id)
    _stamp_recovery_copy(by_id)
    _stamp_current_readiness(by_id)
    _stamp_retention_copy(by_id)
    _stamp_aggregate_trust(by_id)
    if 906 in by_id:
        _stamp_control_plane_recovery_cta(by_id[906])


def _apply_first_window_geometry(
    panels: list[object],
    spec: dict[int, tuple[int, int, int, int]],
    *,
    uid: str,
) -> None:
    root = _root_panels(panels)
    by_id = {panel.get("id"): panel for panel in root}
    missing = set(spec) - set(by_id)
    if missing:
        raise SystemExit(f"{uid}: missing layout panels {sorted(missing)}")
    for panel_id, (x, y, width, height) in spec.items():
        grid = _panel_grid(by_id[panel_id])
        if grid is None:  # pragma: no cover - required panels have geometry
            raise SystemExit(f"{uid}: panel id={panel_id} missing gridPos")
        grid.update({"x": x, "y": y, "w": width, "h": height})


def _pin_collapsed_rows_from(
    panels: list[object],
    *,
    target_y: int,
    protected_ids: set[int],
    uid: str,
) -> None:
    root = _root_panels(panels)
    rows = [panel for panel in root if panel.get("type") == "row"]
    row_geometries = [
        geometry for row in rows if (geometry := _panel_geometry(row)) is not None
    ]
    if not row_geometries:
        raise SystemExit(f"{uid}: missing collapsed detail rows")
    first_row_y = min(y for _, y, _ in row_geometries)
    row_delta = target_y - first_row_y
    if not row_delta:
        return
    for panel in root:
        geometry = _panel_geometry(panel)
        if geometry is None or panel.get("id") in protected_ids:
            continue
        _, y, _ = geometry
        if y >= first_row_y:
            grid = _panel_grid(panel)
            if grid is None:  # pragma: no cover - geometry requires gridPos
                continue
            grid["y"] = y + row_delta


def _layout_uid_first_window(panels: list[object], *, current_uid: str) -> None:
    if current_uid == "bioetl-provider-health-v2":
        for panel in _root_panels(panels):
            if panel.get("id") == 9107:
                panel["description"] = (
                    "CURRENT · Remote API evidence. Cached Bronze replay does not "
                    "exercise the API and proves neither outage nor health. "
                    "missing_health_status = no observation; stale_health_status = "
                    "observation is not fresh. Both are UNKNOWN, never healthy. "
                    "GLOBAL: independent of selected run."
                )
    if current_uid == "bioetl-control-plane-v1":
        _layout_control_plane_first_window(panels)
        return
    if current_uid == "bioetl-incident-v1":
        _apply_first_window_geometry(
            panels, _INCIDENT_FIRST_WINDOW_GEOMETRY, uid=current_uid
        )
        _pin_collapsed_rows_from(
            panels,
            target_y=17,
            protected_ids=set(_INCIDENT_FIRST_WINDOW_GEOMETRY),
            uid=current_uid,
        )
        return
    if current_uid == "bioetl-dq-v2":
        _apply_first_window_geometry(panels, _DQ_FIRST_WINDOW_GEOMETRY, uid=current_uid)
        _pin_collapsed_rows_from(
            panels,
            target_y=18,
            protected_ids=set(_DQ_FIRST_WINDOW_GEOMETRY),
            uid=current_uid,
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
    if not isinstance(old_height, int) or old_height == new_height:
        return
    delta = new_height - old_height
    old_bottom = int(grid_pos.get("y", 0)) + old_height
    for panel in _root_panels(panels):
        if panel is nav:
            continue
        grid = panel.get("gridPos")
        if (
            isinstance(grid, dict)
            and isinstance(grid.get("y"), int)
            and grid["y"] >= old_bottom
            and not (delta < 0 and panel.get("type") == "row")
        ):
            grid["y"] += delta


def _stamp_nav_panel(nav: dict[str, object], panels: list[object]) -> None:
    # The link-only navigation has no visible heading on any dashboard.
    # Keep its inventory name as metadata; links retain visible names and tooltips.
    nav["title"] = ""
    nav["type"] = "text"
    nav["description"] = NAV_DESCRIPTION
    _expand_nav_height(nav, panels, new_height=NAV_HEIGHT)
    grid_pos = nav["gridPos"]
    if not isinstance(grid_pos, dict):
        raise SystemExit("navigation panel gridPos must be an object")
    grid_pos["h"] = NAV_HEIGHT
    grid_pos.update({"w": 24, "x": 0, "y": 0})


def _attach_nav_bus(nav: dict[str, object], *, current_uid: str) -> None:
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
    nav.pop("transparent", None)


def apply_to_dashboard(
    path: Path, *, current_uid: str, check: bool = False, state_followup: bool = False
) -> bool:
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    safe_path = ensure_path_within_root(path, DASH_DIR)
    payload = json.loads(
        safe_path.read_text(encoding="utf-8")  # NOSONAR - confined under DASH_DIR
    )
    # Remove generated details before earlier layout passes measure bottom rows.
    payload["panels"] = [
        panel for panel in payload.get("panels", []) if panel.get("id") != 9450
    ]
    from scripts.ops.observability.grafana.dashboard_context_links import (
        normalize_dashboard_actions,
    )

    if state_followup:
        from scripts.ops.observability.grafana._dashboard_state_followup import (
            apply_dashboard,
            clean_links,
        )

        apply_dashboard(payload)
        clean_links(payload)
    normalize_dashboard_actions(payload)
    _remove_obsolete_provider_handoff_variable(payload)
    _fail_closed_provider_handoffs(
        payload, provider_declared=current_uid in _PROVIDER_VARIABLE_UIDS
    )
    panels = payload.get("panels") or []
    nav = next((p for p in panels if p.get("id") == 1000), None)
    if nav is None:
        raise SystemExit(f"{safe_path.name}: missing panel id=1000")
    _stamp_nav_panel(nav, panels)
    _restore_minimum_first_window_heights(panels, current_uid=current_uid)
    _layout_uid_first_window(panels, current_uid=current_uid)
    _reclaim_first_window_overflow(nav, panels, current_uid=current_uid)
    _layout_uid_first_window(panels, current_uid=current_uid)
    _normalize_collapsed_row_children(panels)
    _layout_uid_detail_panels(panels, current_uid=current_uid)
    _attach_nav_bus(nav, current_uid=current_uid)
    stamp_selector_columns(payload)
    stamp_selected_run_panels(payload)
    from scripts.ops.observability.grafana._visual_usability import apply_visual_usability

    apply_visual_usability(payload)
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
    parser.add_argument(
        "--state-followup",
        action="store_true",
        help="Apply the state, evidence-table and navigation follow-up before rendering; combine with --check to verify without writing",
    )
    args = parser.parse_args(argv)
    ok = True
    for item in BUS:
        uid = item["uid"]
        filename = FILE_BY_UID[uid]
        path = ensure_path_within_root(DASH_DIR / filename, DASH_DIR)
        if not path.exists():
            raise SystemExit(f"missing dashboard file: {path}")
        current_ok = apply_to_dashboard(
            path, current_uid=uid, check=args.check, state_followup=args.state_followup
        )
        ok = current_ok and ok
        if not args.check:
            print(f"updated {filename} current={item['title']!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
