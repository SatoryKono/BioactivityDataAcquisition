#!/usr/bin/env python3
"""Apply VIS-20260908 stream-2 layout fixes (#10247, #10248, #10252, #10257)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH_DIR = ROOT / "grafana" / "dashboards"

_ANCHOR_INTERNAL = (
    "Time",
    "copy",
    "copy_mode",
    "copy_value",
    "drilldown",
    "drilldown_type",
    "drilldown_target",
    "source",
    "source_type",
    "source_quality",
    "format",
    "why",
    "rendering",
    "missing_severity",
    "identity_gap",
    "present",
    "priority",
    "name",
    "value_full",
    "current_value_full",
    "checkpoint_value_full",
)


def _walk(panels: list[Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    stack = list(panels)
    while stack:
        panel = stack.pop(0)
        if not isinstance(panel, dict):
            continue
        found.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            stack[0:0] = [item for item in nested if isinstance(item, dict)]
    return found


def _load(name: str) -> dict[str, Any]:
    path = DASH_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(name: str, payload: dict[str, Any]) -> None:
    path = DASH_DIR / name
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _panel_by_id(payload: dict[str, Any], panel_id: int) -> dict[str, Any]:
    for panel in _walk(payload.get("panels") or []):
        if panel.get("id") == panel_id:
            return panel
    raise KeyError(panel_id)


def _override(field: str, properties: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "matcher": {"id": "byName", "options": field},
        "properties": properties,
    }


def _hidden(field: str) -> dict[str, Any]:
    return _override(field, [{"id": "custom.hidden", "value": True}])


def _rename_width(
    field: str, display: str, *, width: int, inspect: bool = False
) -> dict[str, Any]:
    props: list[dict[str, Any]] = [
        {"id": "displayName", "value": display},
        {"id": "custom.width", "value": width},
        {
            "id": "custom.cellOptions",
            "value": {"type": "auto", "wrapText": False},
        },
    ]
    if inspect:
        props.append({"id": "custom.inspect", "value": True})
    return _override(field, props)


def _set_organize(
    panel: dict[str, Any],
    *,
    exclude: tuple[str, ...],
    index: dict[str, int],
    rename: dict[str, str],
) -> None:
    transforms = panel.setdefault("transformations", [])
    organize = next((item for item in transforms if item.get("id") == "organize"), None)
    if organize is None:
        organize = {"id": "organize", "options": {}}
        transforms.append(organize)
    options = organize.setdefault("options", {})
    excluded = dict(options.get("excludeByName") or {})
    for name in exclude:
        excluded[name] = True
    options["excludeByName"] = excluded
    options["indexByName"] = dict(index)
    renamed = dict(options.get("renameByName") or {})
    renamed.update(rename)
    options["renameByName"] = renamed


def _shrink_and_pack(siblings: list[Any], panel: dict[str, Any], new_h: int) -> None:
    grid = panel.setdefault("gridPos", {})
    old_h = int(grid.get("h") or new_h)
    if old_h <= new_h:
        grid["h"] = new_h
        return
    y = int(grid.get("y") or 0)
    old_bottom = y + old_h
    delta = old_h - new_h
    grid["h"] = new_h
    for sibling in siblings:
        if sibling is panel or not isinstance(sibling, dict):
            continue
        sibling_grid = sibling.get("gridPos")
        if not isinstance(sibling_grid, dict):
            continue
        sibling_y = sibling_grid.get("y")
        if isinstance(sibling_y, int) and sibling_y >= old_bottom:
            sibling_grid["y"] = sibling_y - delta


def _apply_anchor_table(
    panel: dict[str, Any],
    *,
    visible: list[tuple[str, str, int, bool]],
) -> None:
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    custom = defaults.setdefault("custom", {})
    custom["align"] = "left"
    custom["inspect"] = True
    custom.setdefault("cellOptions", {})["wrapText"] = False
    overrides = [_hidden(name) for name in _ANCHOR_INTERNAL]
    overrides.extend(
        _rename_width(field, display, width=width, inspect=inspect)
        for field, display, width, inspect in visible
    )
    panel["fieldConfig"]["overrides"] = overrides
    _set_organize(
        panel,
        exclude=_ANCHOR_INTERNAL,
        index={field: index for index, (field, _, _, _) in enumerate(visible)},
        rename={field: display for field, display, _, _ in visible},
    )
    options = panel.setdefault("options", {})
    options["showHeader"] = True
    options["cellHeight"] = "sm"
    options["footer"] = {"show": False}


def patch_control_plane(payload: dict[str, Any]) -> None:
    identity = _panel_by_id(payload, 9407)
    _apply_anchor_table(
        identity,
        visible=[
            ("label", "Parameter", 160, False),
            ("value_short", "Current", 220, True),
            ("ui_status", "Result", 90, False),
        ],
    )
    parent = next(
        panel
        for panel in _walk(payload.get("panels") or [])
        if any(
            isinstance(child, dict) and child.get("id") == 9407
            for child in (panel.get("panels") or [])
        )
    )
    _shrink_and_pack(parent.get("panels") or [], identity, 8)

    gaps = _panel_by_id(payload, 9405)
    _apply_anchor_table(
        gaps,
        visible=[
            ("label", "Parameter", 160, False),
            ("value_short", "Current", 220, True),
            ("ui_status", "Result", 90, False),
        ],
    )
    gaps_parent = next(
        panel
        for panel in _walk(payload.get("panels") or [])
        if any(
            isinstance(child, dict) and child.get("id") == 9405
            for child in (panel.get("panels") or [])
        )
    )
    _shrink_and_pack(gaps_parent.get("panels") or [], gaps, 8)

    compare = _panel_by_id(payload, 9406)
    _apply_anchor_table(
        compare,
        visible=[
            ("anchor", "Parameter", 140, False),
            ("current_value_short", "Current", 140, True),
            ("checkpoint_value_short", "Checkpoint", 140, True),
            ("status", "Result", 90, False),
        ],
    )

    required = _panel_by_id(payload, 9408)
    _apply_anchor_table(
        required,
        visible=[
            ("label", "Parameter", 150, False),
            ("value_short", "Current", 160, True),
            ("status", "Result", 90, False),
            ("drilldown_label", "Action", 110, False),
        ],
    )
    extra = _panel_by_id(payload, 9409)
    _apply_anchor_table(
        extra,
        visible=[
            ("label", "Parameter", 150, False),
            ("value_short", "Current", 160, True),
            ("status", "Result", 90, False),
            ("drilldown_label", "Action", 110, False),
        ],
    )

    latency = _panel_by_id(payload, 111)
    latency["description"] = (
        "TIME RANGE · Default p95 read latency by store and operation; change "
        "Read latency to p50 or p99. Excludes failed reads (status!=\"failed\"). "
        "Filters do not apply. No data means no latency samples were recorded "
        "in the selected range. TELEMETRY MISSING is not a zero and not VALID EMPTY."
    )
    latency["targets"] = [
        {
            "expr": (
                "histogram_quantile($read_latency_quantile, "
                "sum by (le, store, operation) "
                "(increase(bioetl_control_plane_read_duration_seconds_bucket"
                '{status!="failed"}[$__range])))'
            ),
            "legendFormat": "{{store}} / {{operation}}",
            "refId": "A",
        }
    ]
    field_defaults = latency.setdefault("fieldConfig", {}).setdefault("defaults", {})
    field_defaults["unit"] = "s"
    field_defaults["color"] = {"mode": "palette-classic"}
    field_defaults["custom"] = {
        **(field_defaults.get("custom") or {}),
        "axisLabel": "seconds",
    }
    latency["fieldConfig"]["overrides"] = []
    latency["options"] = {
        "legend": {
            "calcs": ["lastNotNull", "max"],
            "displayMode": "table",
            "placement": "bottom",
            "showLegend": True,
        },
        "tooltip": {"mode": "multi", "sort": "desc"},
    }
    latency_parent = next(
        panel
        for panel in _walk(payload.get("panels") or [])
        if any(
            isinstance(child, dict) and child.get("id") == 111
            for child in (panel.get("panels") or [])
        )
    )
    _shrink_and_pack(latency_parent.get("panels") or [], latency, 8)

    reads = _panel_by_id(payload, 6)
    reads["description"] = (
        str(reads.get("description") or "")
        + " Axis: reads per Grafana interval ($__interval); K is thousands of reads."
    ).strip()
    reads_defaults = reads.setdefault("fieldConfig", {}).setdefault("defaults", {})
    reads_defaults["unit"] = "short"
    reads_defaults["custom"] = {
        **(reads_defaults.get("custom") or {}),
        "axisLabel": "reads / $__interval",
    }
    reads["options"] = {
        **(reads.get("options") or {}),
        "legend": {
            "calcs": ["lastNotNull", "max"],
            "displayMode": "table",
            "placement": "right",
            "showLegend": True,
        },
    }

    templating = payload.setdefault("templating", {}).setdefault("list", [])
    if not any(
        isinstance(item, dict) and item.get("name") == "read_latency_quantile"
        for item in templating
    ):
        templating.append(
            {
                "current": {"selected": True, "text": "p95", "value": "0.95"},
                "hide": 0,
                "includeAll": False,
                "label": "Read latency",
                "multi": False,
                "name": "read_latency_quantile",
                "options": [
                    {"selected": False, "text": "p50", "value": "0.50"},
                    {"selected": True, "text": "p95", "value": "0.95"},
                    {"selected": False, "text": "p99", "value": "0.99"},
                ],
                "query": "p50 : 0.50, p95 : 0.95, p99 : 0.99",
                "skipUrlSync": False,
                "type": "custom",
            }
        )


def _set_width(panel: dict[str, Any], field: str, width: int) -> None:
    overrides = panel.setdefault("fieldConfig", {}).setdefault("overrides", [])
    for item in overrides:
        matcher = item.get("matcher") or {}
        if matcher.get("options") != field:
            continue
        props = item.setdefault("properties", [])
        width_prop = next((prop for prop in props if prop.get("id") == "custom.width"), None)
        if width_prop is None:
            props.append({"id": "custom.width", "value": width})
        else:
            width_prop["value"] = width
        min_width = next(
            (prop for prop in props if prop.get("id") == "custom.minWidth"), None
        )
        if field in {"Value", "Severity", "bioetl_provider_current_status"}:
            if min_width is None:
                props.append({"id": "custom.minWidth", "value": width})
            else:
                min_width["value"] = width
        cell = next(
            (prop for prop in props if prop.get("id") == "custom.cellOptions"), None
        )
        if field in {"Value", "Severity", "bioetl_provider_current_status"}:
            value = {"type": "color-background", "mode": "basic", "wrapText": False}
            if cell is None:
                props.append({"id": "custom.cellOptions", "value": value})
            else:
                existing = cell.get("value")
                if isinstance(existing, dict):
                    existing["wrapText"] = False
                    existing.setdefault("type", "color-background")
                else:
                    cell["value"] = value
        return
    overrides.append(
        _override(
            field,
            [
                {"id": "custom.width", "value": width},
                {"id": "custom.minWidth", "value": width},
            ],
        )
    )


def patch_provider(payload: dict[str, Any]) -> None:
    for panel_id in (9101, 9102, 9103, 9111, 9112, 9113):
        try:
            panel = _panel_by_id(payload, panel_id)
        except KeyError:
            continue
        if panel.get("type") != "table":
            continue
        _set_width(panel, "provider", 130)
        _set_width(panel, "Provider", 130)
        _set_width(panel, "Value", 160)
        _set_width(panel, "Severity", 160)
        _set_width(panel, "bioetl_provider_current_status", 160)
    non_ok = _panel_by_id(payload, 9102)
    non_ok["description"] = (
        str(non_ok.get("description") or "")
        + " First-screen Monitor Fleet Severity is the compact summary; this "
        "table is the Non-OK expander (status>=1), not a second copy of OK rows."
    ).strip()


def compact_status_stats(payload: dict[str, Any]) -> None:
    for panel in _walk(payload.get("panels") or []):
        if panel.get("type") != "stat":
            continue
        options = panel.setdefault("options", {})
        if options.get("colorMode") != "background":
            continue
        options["colorMode"] = "value"
        options["textMode"] = "value_and_name"
        options["graphMode"] = "none"
        options["text"] = {"titleSize": 14, "valueSize": 20}


def main() -> int:
    control = _load("bioetl-control-plane-v1.json")
    patch_control_plane(control)
    compact_status_stats(control)
    _dump("bioetl-control-plane-v1.json", control)

    provider = _load("bioetl-provider-health-v2.json")
    patch_provider(provider)
    compact_status_stats(provider)
    _dump("bioetl-provider-health-v2.json", provider)

    for name in (
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
        "bioetl-dq-v2.json",
        "bioetl-incident-v1.json",
        "bioetl-run-explorer-v1.json",
    ):
        payload = _load(name)
        compact_status_stats(payload)
        _dump(name, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
