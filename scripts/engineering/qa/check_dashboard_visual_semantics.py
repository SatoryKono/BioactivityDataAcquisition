#!/usr/bin/env python3
"""Validate Grafana dashboard visual-semantics invariants."""

from __future__ import annotations

import json
from pathlib import Path

DASHBOARDS_DIR = Path("grafana/dashboards")
EXPECTED_STEPS = [
    {"color": "green", "value": None},
    {"color": "orange", "value": 1},
    {"color": "red", "value": 2},
]
EXPECTED_STEPS_BY_PANEL = {
    ("bioetl-runtime.json", "Monitor Runtime Blockers"): [
        {"color": "green", "value": None},
        {"color": "red", "value": 1},
    ],
    ("bioetl-runtime.json", "Runtime Error Rate"): [
        {"color": "green", "value": None},
        {"color": "orange", "value": 0.05},
        {"color": "red", "value": 0.2},
    ],
    ("bioetl-runtime.json", "Worst Stage Lag"): [
        {"color": "green", "value": None},
        {"color": "orange", "value": 300},
        {"color": "red", "value": 900},
    ],
}
EXPECTED_UNKNOWN_MAPPING = {
    "type": "special",
    "options": {"match": "null", "result": {"text": "UNKNOWN", "color": "gray"}},
}
L0_DASHBOARD_FILES = {
    "bioetl-overview-v2.json",
}
FORBIDDEN_L0_TERMS = {"DEGRADED", "BROKEN", "HEALTHY"}
STATUS_PANEL_TOKENS = ("status", "state", "severity", "health")
STANDARD_SEVERITY_TITLE_TOKENS = (
    "Current Status",
    "Telemetry Gap",
    "Threshold State",
)
BACKGROUND_SEVERITY_STAT_PANELS = {
    ("bioetl-overview-v2.json", "Status"),
    ("bioetl-runtime.json", "Runtime Status"),
    ("bioetl-runtime.json", "Runtime Telemetry Gap"),
    ("bioetl-runtime.json", "Monitor Runtime Blockers"),
    ("bioetl-runtime.json", "Failed Runs"),
    ("bioetl-runtime.json", "Runtime Error Rate"),
    ("bioetl-runtime.json", "Worst Stage Lag"),
    ("bioetl-dq-v2.json", "Monitor DQ Current Status"),
    ("bioetl-dq-v2.json", "Monitor DQ Threshold State"),
    ("bioetl-control-plane-v1.json", "Monitor: Replay Safety State"),
    ("bioetl-control-plane-v1.json", "Monitor: Manifest / Ledger Integrity"),
    ("bioetl-control-plane-v1.json", "Inspect: Telemetry Missing"),
}
SCALAR_TREND_TIMESERIES_PANELS = {
    ("bioetl-dq-v2.json", "Track: Data Quality Score Trend (Volume-weighted)"),
    ("bioetl-dq-v2.json", "Track: DQ Threshold Events in Range Trend"),
    ("bioetl-overview-v2.json", "Runtime Blockers Trend"),
    ("bioetl-overview-v2.json", "DQ Status Trend"),
    ("bioetl-overview-v2.json", "Gold Lifecycle Trend"),
}
ALLOWED_TABLE_CELL_OPTION_TYPES = {"auto", "color-background", "color-text"}
EXPLICIT_VALUE_MAPPING_STAT_PANELS = {
    ("bioetl-overview-v2.json", "Status"): {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
        "3": {"text": "UNKNOWN", "color": "gray"},
    },
    ("bioetl-runtime.json", "Runtime Status"): {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
        "3": {"text": "INCOMPLETE", "color": "gray"},
    },
    ("bioetl-runtime.json", "Runtime Telemetry Gap"): {
        "0": {"text": "SCRAPING", "color": "green"},
        "1": {"text": "SCRAPE/RULE GAP", "color": "orange"},
        "2": {"text": "SCRAPE+RULE GAP", "color": "red"},
    },
    ("bioetl-dq-v2.json", "Monitor DQ Current Status"): {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
        "3": {"text": "INCOMPLETE", "color": "gray"},
    },
    ("bioetl-dq-v2.json", "Monitor DQ Threshold State"): {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
    },
    ("bioetl-control-plane-v1.json", "Monitor: Replay Safety State"): {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
    },
    ("bioetl-control-plane-v1.json", "Monitor: Manifest / Ledger Integrity"): {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
    },
    ("bioetl-control-plane-v1.json", "Inspect: Telemetry Missing"): {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
    },
}
FAIL_CLOSED_NO_ZERO_FALLBACK_PANELS = {
    ("bioetl-overview-v2.json", "Status"): "UNKNOWN",
    ("bioetl-runtime.json", "Runtime Status"): "UNKNOWN",
    ("bioetl-runtime.json", "Runtime Telemetry Gap"): "UNKNOWN",
    ("bioetl-runtime.json", "Monitor Runtime Blockers"): "UNKNOWN",
    ("bioetl-runtime.json", "Runtime Error Rate"): "UNKNOWN",
    ("bioetl-runtime.json", "Worst Stage Lag"): "UNKNOWN",
    ("bioetl-runtime.json", "Monitor Memory Pressure Active"): "UNKNOWN",
    ("bioetl-provider-health-v2.json", "Monitor GLOBAL Provider Severity Matrix"): None,
    ("bioetl-provider-health-v2.json", "Inspect Provider Top Causes"): None,
    ("bioetl-dq-v2.json", "Monitor DQ Current Status"): "UNKNOWN",
    ("bioetl-dq-v2.json", "Monitor DQ Threshold State"): "UNKNOWN",
    ("bioetl-control-plane-v1.json", "Monitor: Replay Safety State"): "UNKNOWN",
    ("bioetl-control-plane-v1.json", "Monitor: Manifest / Ledger Integrity"): "UNKNOWN",
    ("bioetl-control-plane-v1.json", "Inspect: Telemetry Missing"): "UNKNOWN",
}
REQUIRED_TRUST_MARKER_PANELS = {
    "bioetl-runtime.json": {"Runtime Telemetry Gap"},
    "bioetl-control-plane-v1.json": {"Inspect: Telemetry Missing"},
}


def _grid_pos(panel: dict) -> dict:
    grid_pos = panel.get("gridPos", {})
    return grid_pos if isinstance(grid_pos, dict) else {}


def _grid_rectangles_overlap(left: dict, right: dict) -> bool:
    left_grid = _grid_pos(left)
    right_grid = _grid_pos(right)
    left_x = int(left_grid.get("x", 0))
    left_y = int(left_grid.get("y", 0))
    left_w = int(left_grid.get("w", 0))
    left_h = int(left_grid.get("h", 0))
    right_x = int(right_grid.get("x", 0))
    right_y = int(right_grid.get("y", 0))
    right_w = int(right_grid.get("w", 0))
    right_h = int(right_grid.get("h", 0))
    x_overlap = left_x < right_x + right_w and right_x < left_x + left_w
    y_overlap = left_y < right_y + right_h and right_y < left_y + left_h
    return x_overlap and y_overlap


def _collapsed_row_grid_overlap_errors(
    dashboard_path: Path, row_panel: dict
) -> list[str]:
    nested_panels = [
        panel for panel in row_panel.get("panels", []) if isinstance(panel, dict)
    ]
    errors: list[str] = []
    for index, left in enumerate(nested_panels):
        for right in nested_panels[index + 1 :]:
            if _grid_rectangles_overlap(left, right):
                errors.append(
                    f"{dashboard_path}: collapsed row '{row_panel.get('title')}' "
                    f"has overlapping nested panels "
                    f"{left.get('id')}:{left.get('title')} and "
                    f"{right.get('id')}:{right.get('title')}"
                )
    return errors


def iter_panels(panels: list[dict]) -> list[dict]:
    collected: list[dict] = []
    for panel in panels:
        if panel.get("type") == "row" and isinstance(panel.get("panels"), list):
            collected.extend(iter_panels(panel["panels"]))
        else:
            collected.append(panel)
    return collected


def _stat_color_mode_error(dashboard_path: Path, title: str, defaults: dict) -> str | None:
    if defaults.get("color", {}).get("mode") == "thresholds":
        return None
    return f"{dashboard_path}: panel '{title}' must use color.mode=thresholds"


def _stat_threshold_steps_error(
    dashboard_path: Path, title: str, defaults: dict
) -> str | None:
    expected_steps = _expected_threshold_steps(dashboard_path, str(title))
    steps = defaults.get("thresholds", {}).get("steps")
    if expected_steps is None or steps == expected_steps:
        return None
    return f"{dashboard_path}: panel '{title}' must use standardized threshold steps"


def _stat_unknown_mapping_error(
    dashboard_path: Path, title: str, panel: dict, mappings: list
) -> str | None:
    if not _requires_unknown_mapping(panel):
        return None
    if EXPECTED_UNKNOWN_MAPPING in mappings:
        return None
    return f"{dashboard_path}: panel '{title}' must map null to UNKNOWN/gray"


def _stat_background_color_mode_error(
    dashboard_path: Path, title: str, panel: dict
) -> str | None:
    if (dashboard_path.name, str(title)) not in BACKGROUND_SEVERITY_STAT_PANELS:
        return None
    if panel.get("options", {}).get("colorMode") == "background":
        return None
    return f"{dashboard_path}: panel '{title}' must use options.colorMode=background"


def _stat_value_mapping_error(
    dashboard_path: Path, title: str, mappings: list
) -> str | None:
    expected_value_mapping = EXPLICIT_VALUE_MAPPING_STAT_PANELS.get(
        (dashboard_path.name, str(title))
    )
    if expected_value_mapping is None:
        return None
    value_mapping = next(
        (mapping for mapping in mappings if mapping.get("type") == "value"),
        None,
    )
    if (
        value_mapping is not None
        and value_mapping.get("options") == expected_value_mapping
    ):
        return None
    return (
        f"{dashboard_path}: panel '{title}' must use explicit canonical value mappings"
    )


def _stat_panel_visual_semantics_errors(dashboard_path: Path, panel: dict) -> list[str]:
    title = panel.get("title", "<untitled>")
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    mappings = defaults.get("mappings", [])
    candidates = (
        _stat_color_mode_error(dashboard_path, title, defaults),
        _stat_threshold_steps_error(dashboard_path, title, defaults),
        _stat_unknown_mapping_error(dashboard_path, title, panel, mappings),
        _stat_background_color_mode_error(dashboard_path, title, panel),
        _stat_value_mapping_error(dashboard_path, title, mappings),
    )
    return [error for error in candidates if error is not None]


def _gauge_panel_visual_semantics_errors(
    dashboard_path: Path, panel: dict
) -> list[str]:
    title = panel.get("title", "<untitled>")
    options = panel.get("options", {})
    errors: list[str] = []

    if options.get("showThresholdMarkers") is not True:
        errors.append(
            f"{dashboard_path}: gauge panel '{title}' must show threshold markers"
        )
    if options.get("showThresholdLabels") is not False:
        errors.append(
            f"{dashboard_path}: gauge panel '{title}' must hide threshold labels"
        )

    return errors


def _table_panel_visual_semantics_errors(
    dashboard_path: Path, panel: dict
) -> list[str]:
    title = panel.get("title", "<untitled>")
    field_config = panel.get("fieldConfig", {})
    errors: list[str] = []

    default_cell_options = (
        field_config.get("defaults", {}).get("custom", {}).get("cellOptions")
    )
    if isinstance(default_cell_options, dict):
        cell_type = default_cell_options.get("type")
        if cell_type not in ALLOWED_TABLE_CELL_OPTION_TYPES:
            errors.append(
                f"{dashboard_path}: table panel '{title}' has unsupported default cellOptions.type={cell_type!r}"
            )

    for override in field_config.get("overrides", []):
        matcher = override.get("matcher", {}).get("options", "<unknown>")
        for prop in override.get("properties", []):
            if prop.get("id") != "custom.cellOptions":
                continue
            value = prop.get("value")
            cell_type = value.get("type") if isinstance(value, dict) else None
            if cell_type not in ALLOWED_TABLE_CELL_OPTION_TYPES:
                errors.append(
                    f"{dashboard_path}: table panel '{title}' override {matcher!r} "
                    f"has unsupported cellOptions.type={cell_type!r}"
                )

    return errors


def _timeseries_panel_visual_semantics_errors(
    dashboard_path: Path, panel: dict
) -> list[str]:
    title = str(panel.get("title", "<untitled>"))
    tooltip = panel.get("options", {}).get("tooltip", {})
    is_scalar_trend = (dashboard_path.name, title) in SCALAR_TREND_TIMESERIES_PANELS
    expected_mode = "single" if is_scalar_trend else "multi"
    expected_sort = "none" if is_scalar_trend else "desc"
    actual_sort = tooltip.get("sort", "none")
    errors: list[str] = []

    if tooltip.get("mode") != expected_mode:
        errors.append(
            f"{dashboard_path}: timeseries panel '{title}' must use tooltip.mode={expected_mode!r}"
        )
    if actual_sort != expected_sort:
        errors.append(
            f"{dashboard_path}: timeseries panel '{title}' must use tooltip.sort={expected_sort!r}"
        )

    return errors


def _expected_threshold_steps(dashboard_path: Path, title: str) -> list[dict] | None:
    custom_steps = EXPECTED_STEPS_BY_PANEL.get((dashboard_path.name, title))
    if custom_steps is not None:
        return custom_steps
    if any(token in title for token in STANDARD_SEVERITY_TITLE_TOKENS):
        return EXPECTED_STEPS
    return None


def _requires_unknown_mapping(panel: dict) -> bool:
    title = str(panel.get("title", ""))
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    return defaults.get("noValue") == "UNKNOWN" or any(
        token in title for token in STANDARD_SEVERITY_TITLE_TOKENS
    )


def _l0_terminology_errors(dashboard_path: Path, panel: dict) -> list[str]:
    if dashboard_path.name not in L0_DASHBOARD_FILES:
        return []

    title = panel.get("title", "<untitled>")
    text_fields = [str(title), str(panel.get("description", ""))]
    return [
        f"{dashboard_path}: panel '{title}' uses '{term}' in L0 dashboard; "
        "use OK/WARN/CRIT/UNKNOWN terminology"
        for term in FORBIDDEN_L0_TERMS
        if any(term in text.upper() for text in text_fields)
    ]


def _is_status_like_panel(panel: dict) -> bool:
    title = str(panel.get("title", "")).lower()
    description = str(panel.get("description", "")).lower()
    return any(token in title or token in description for token in STATUS_PANEL_TOKENS)


def _stat_threshold_color_errors(dashboard_path: Path, panel: dict) -> list[str]:
    if panel.get("type") != "stat":
        return []

    title = str(panel.get("title", ""))
    color_mode = (
        panel.get("fieldConfig", {}).get("defaults", {}).get("color", {}).get("mode")
    )
    if color_mode == "thresholds":
        return []
    return [f"{dashboard_path}: stat panel '{title}' must use color.mode=thresholds"]


def _status_panel_errors(dashboard_path: Path, panel: dict) -> list[str]:
    if panel.get("type") not in {"stat", "gauge"} or not _is_status_like_panel(panel):
        return []
    return _stat_panel_visual_semantics_errors(
        dashboard_path, panel
    ) + _l0_terminology_errors(dashboard_path, panel)


def _panel_type_errors(dashboard_path: Path, panel: dict) -> list[str]:
    panel_type = panel.get("type")
    if panel_type == "gauge":
        return _gauge_panel_visual_semantics_errors(dashboard_path, panel)
    if panel_type == "table":
        return _table_panel_visual_semantics_errors(dashboard_path, panel)
    if panel_type == "timeseries":
        return _timeseries_panel_visual_semantics_errors(dashboard_path, panel)
    return []


def _panel_expressions(panel: dict) -> list[str]:
    return [
        str(target.get("expr", ""))
        for target in panel.get("targets", [])
        if isinstance(target, dict) and isinstance(target.get("expr"), str)
    ]


def _fail_closed_panel_errors(
    dashboard_path: Path, panel: dict, expected_no_value: str | None
) -> list[str]:
    if expected_no_value is None:
        return []

    title = str(panel.get("title", ""))
    errors: list[str] = []
    if any("or vector(0)" in expr for expr in _panel_expressions(panel)):
        errors.append(
            f"{dashboard_path}: panel '{title}' must preserve UNKNOWN instead of zero fallback"
        )

    no_value = panel.get("fieldConfig", {}).get("defaults", {}).get("noValue")
    if no_value != expected_no_value:
        errors.append(
            f"{dashboard_path}: panel '{title}' must use noValue={expected_no_value!r}"
        )
    return errors


def _panel_errors(dashboard_path: Path, panel: dict) -> list[str]:
    title = str(panel.get("title", ""))
    panel_key = (dashboard_path.name, title)
    expected_no_value = FAIL_CLOSED_NO_ZERO_FALLBACK_PANELS.get(panel_key)
    return (
        _stat_threshold_color_errors(dashboard_path, panel)
        + _status_panel_errors(dashboard_path, panel)
        + _panel_type_errors(dashboard_path, panel)
        + _fail_closed_panel_errors(dashboard_path, panel, expected_no_value)
    )


def _collapsed_row_errors(dashboard_path: Path, panels: list) -> list[str]:
    return [
        error
        for panel in panels
        if panel.get("type") == "row" and isinstance(panel.get("panels"), list)
        for error in _collapsed_row_grid_overlap_errors(dashboard_path, panel)
    ]


def _trust_marker_is_above_fold(panel: dict) -> bool:
    grid_pos = panel.get("gridPos", {})
    # Trust markers must stay on the first screen, including the dedicated
    # first-screen evidence row used by the Runtime dashboard at y=23.
    return isinstance(grid_pos, dict) and int(grid_pos.get("y", 999)) <= 23


def _trust_marker_panel_errors(dashboard_path: Path, panels: list) -> list[str]:
    required_panels = REQUIRED_TRUST_MARKER_PANELS.get(dashboard_path.name, set())
    if not required_panels:
        return []
    top_level_panels = {str(panel.get("title", "")): panel for panel in panels}
    errors: list[str] = []
    for title in required_panels:
        panel = top_level_panels.get(title)
        if panel is None:
            errors.append(
                f"{dashboard_path}: required trust marker panel '{title}' is missing"
            )
            continue
        if not _trust_marker_is_above_fold(panel):
            errors.append(
                f"{dashboard_path}: trust marker panel '{title}' must stay above fold"
            )
    return errors


def _dashboard_errors(dashboard_path: Path) -> list[str]:
    payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = payload.get("panels", [])
    errors = [
        error
        for panel in iter_panels(panels)
        for error in _panel_errors(dashboard_path, panel)
    ]
    errors.extend(_collapsed_row_errors(dashboard_path, panels))
    errors.extend(_trust_marker_panel_errors(dashboard_path, panels))
    return errors


def _report_errors(errors: list[str]) -> int:
    if not errors:
        print("Dashboard visual semantics check passed.")
        return 0

    print("Dashboard visual semantics check failed:")
    for error in errors:
        print(f"- {error}")
    return 1


def main() -> int:
    errors = [
        error
        for dashboard_path in sorted(DASHBOARDS_DIR.glob("*.json"))
        for error in _dashboard_errors(dashboard_path)
    ]
    return _report_errors(errors)


if __name__ == "__main__":
    raise SystemExit(main())
