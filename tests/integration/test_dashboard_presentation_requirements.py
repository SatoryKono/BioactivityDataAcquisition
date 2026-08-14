"""Executable contract for dashboard density, typography, and area fills."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import pytest

from tests.integration._dashboard_layout_budgets import FIRST_WINDOW_Y

pytestmark = pytest.mark.integration

DASHBOARD_DIR = Path("grafana/dashboards")
REQUIREMENTS_PATH = Path("docs/01-requirements/DASHBOARD_REQUIREMENTS.md")
RULES_PATH = Path("docs/00-project/RULES.md")
REQUIREMENTS_INDEX_PATH = Path("docs/01-requirements/REQUIREMENTS.md")
DASHBOARD_DOCS_INDEX_PATH = Path("docs/03-guides/dashboards/README.md")

FIRST_WINDOW_Y_EXCLUSIVE = FIRST_WINDOW_Y
MIN_DATA_AREA_DENSITY = 0.60
MIN_DATA_COUNT_DENSITY = 0.50
MIN_BODY_FONT_PX = 16.0
MIN_PANEL_TITLE_FONT_PX = 14.0 * 4.0 / 3.0

_FONT_SIZE_DECLARATION = re.compile(
    r"font-size\s*:\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>px|pt|rem)\b",
    flags=re.IGNORECASE,
)
_ANY_FONT_SIZE_DECLARATION = re.compile(r"font-size\s*:", flags=re.IGNORECASE)
_CSS_BACKGROUND_DECLARATION = re.compile(
    r"(?:^|;)\s*background(?:-color)?\s*:", flags=re.IGNORECASE
)
_AREA_COLOR_MODES = {"background", "backgroundSolid"}


def _load_dashboards() -> list[tuple[Path, dict[str, Any]]]:
    return [
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(DASHBOARD_DIR.glob("*.json"))
    ]


def _panel_area(panel: dict[str, Any]) -> int:
    grid = panel.get("gridPos")
    if not isinstance(grid, dict):
        return 0
    width = grid.get("w")
    height = grid.get("h")
    if not isinstance(width, int) or not isinstance(height, int):
        return 0
    return width * height


def _is_data_bearing(panel: dict[str, Any]) -> bool:
    targets = panel.get("targets")
    if not isinstance(targets, list):
        return False
    return any(
        isinstance(target, dict) and target.get("hide") is not True
        for target in targets
    )


def _row_density(row: dict[str, Any]) -> tuple[float, float]:
    children = [
        panel
        for panel in row.get("panels", [])
        if isinstance(panel, dict) and panel.get("type") != "row"
    ]
    if not children:
        return 0.0, 0.0
    areas = [_panel_area(panel) for panel in children]
    total_area = sum(areas)
    if total_area <= 0 or any(area <= 0 for area in areas):
        return 0.0, 0.0
    data_panels = [panel for panel in children if _is_data_bearing(panel)]
    data_area = sum(_panel_area(panel) for panel in data_panels)
    return data_area / total_area, len(data_panels) / len(children)


def _font_size_px(value: float, unit: str) -> float:
    normalized_unit = unit.lower()
    if normalized_unit == "px":
        return value
    if normalized_unit == "pt":
        return value * 4.0 / 3.0
    if normalized_unit == "rem":
        return value * 16.0
    raise AssertionError(f"unsupported font unit: {unit}")


def _authored_font_sizes_px(content: str) -> list[float]:
    matches = list(_FONT_SIZE_DECLARATION.finditer(content))
    assert len(matches) == len(_ANY_FONT_SIZE_DECLARATION.findall(content)), (
        "every authored font-size must use a reviewable px, pt, or rem literal"
    )
    return [
        _font_size_px(float(match.group("value")), match.group("unit"))
        for match in matches
    ]


def _cell_option_types(panel: dict[str, Any]) -> list[str]:
    field_config = panel.get("fieldConfig")
    if not isinstance(field_config, dict):
        return []
    collected: list[str] = []
    defaults = field_config.get("defaults")
    if isinstance(defaults, dict):
        custom = defaults.get("custom")
        if isinstance(custom, dict):
            cell_options = custom.get("cellOptions")
            if isinstance(cell_options, dict) and isinstance(
                cell_options.get("type"), str
            ):
                collected.append(cell_options["type"])
    overrides = field_config.get("overrides")
    if not isinstance(overrides, list):
        return collected
    for override in overrides:
        if not isinstance(override, dict):
            continue
        properties = override.get("properties")
        if not isinstance(properties, list):
            continue
        for prop in properties:
            if not isinstance(prop, dict) or prop.get("id") != "custom.cellOptions":
                continue
            value = prop.get("value")
            if isinstance(value, dict) and isinstance(value.get("type"), str):
                collected.append(value["type"])
    return collected


def _area_fill_violations(panel: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    options = panel.get("options")
    if isinstance(options, dict) and options.get("colorMode") in _AREA_COLOR_MODES:
        violations.append(f"colorMode={options['colorMode']}")
    if isinstance(options, dict) and options.get("graphMode") == "area":
        violations.append("graphMode=area")

    field_config = panel.get("fieldConfig")
    defaults = field_config.get("defaults") if isinstance(field_config, dict) else None
    custom = defaults.get("custom") if isinstance(defaults, dict) else None
    if isinstance(custom, dict):
        fill_opacity = custom.get("fillOpacity", 0)
        if isinstance(fill_opacity, (int, float)) and fill_opacity > 0:
            violations.append(f"fillOpacity={fill_opacity}")
        gradient_mode = custom.get("gradientMode")
        if gradient_mode not in {None, "none"}:
            violations.append(f"gradientMode={gradient_mode}")

    overrides = field_config.get("overrides") if isinstance(field_config, dict) else None
    if isinstance(overrides, list):
        for override in overrides:
            properties = override.get("properties") if isinstance(override, dict) else None
            if not isinstance(properties, list):
                continue
            for prop in properties:
                if not isinstance(prop, dict):
                    continue
                prop_id = prop.get("id")
                value = prop.get("value")
                if prop_id == "custom.fillOpacity" and isinstance(
                    value, (int, float)
                ) and value > 0:
                    violations.append(f"override fillOpacity={value}")
                if prop_id == "custom.gradientMode" and value not in {None, "none"}:
                    violations.append(f"override gradientMode={value}")

    if "color-background" in _cell_option_types(panel):
        violations.append("cellOptions=color-background")

    if panel.get("type") == "text" and isinstance(options, dict):
        content = options.get("content")
        if isinstance(content, str) and _CSS_BACKGROUND_DECLARATION.search(content):
            violations.append("authored CSS background")
    return violations


def test_dashboard_requirements_are_normatively_routed() -> None:
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    rules = RULES_PATH.read_text(encoding="utf-8")
    requirements_index = REQUIREMENTS_INDEX_PATH.read_text(encoding="utf-8")
    dashboard_index = DASHBOARD_DOCS_INDEX_PATH.read_text(encoding="utf-8")

    for token in (
        "REQ-DASH-001",
        "REQ-DASH-002",
        "REQ-DASH-003",
        "D_area = A_data / A_total",
        "12pt = 16px",
        "14pt = 18.6667px",
        "FIRST_WINDOW_Y",
        "FIRST_LOAD_Y_MAX",
    ):
        assert token in requirements
    for routed_doc in (rules, requirements_index, dashboard_index):
        assert "DASHBOARD_REQUIREMENTS.md" in routed_doc
    assert "REQ-DASH-001" in rules
    assert "REQ-DASH-002" in rules
    assert "REQ-DASH-003" in rules


def test_additional_panel_groups_meet_data_density_floor() -> None:
    observed_rows = 0
    violations: list[str] = []
    for path, dashboard in _load_dashboards():
        root_panels = dashboard.get("panels")
        assert isinstance(root_panels, list), f"{path.name}: panels must be a list"
        for row in root_panels:
            if not isinstance(row, dict) or row.get("type") != "row":
                continue
            observed_rows += 1
            area_density, count_density = _row_density(row)
            if (
                area_density < MIN_DATA_AREA_DENSITY
                or count_density < MIN_DATA_COUNT_DENSITY
            ):
                violations.append(
                    f"{path.name}:{row.get('title')} "
                    f"area={area_density:.3f} count={count_density:.3f}"
                )
    assert observed_rows > 0
    assert not violations, "additional panel groups are too sparse:\n" + "\n".join(
        violations
    )


def test_authored_text_font_sizes_meet_body_floor() -> None:
    violations: list[str] = []
    for path, dashboard in _load_dashboards():
        stack = list(dashboard.get("panels", []))
        while stack:
            panel = stack.pop()
            if not isinstance(panel, dict):
                continue
            nested = panel.get("panels")
            if isinstance(nested, list):
                stack.extend(nested)
            if panel.get("type") != "text":
                continue
            options = panel.get("options")
            content = options.get("content") if isinstance(options, dict) else None
            if not isinstance(content, str):
                continue
            for size in _authored_font_sizes_px(content):
                if size + 1e-9 < MIN_BODY_FONT_PX:
                    violations.append(
                        f"{path.name}:{panel.get('id')}:{panel.get('title')}={size:g}px"
                    )
    assert not violations, "authored text below 12pt/16px:\n" + "\n".join(
        violations
    )


def test_area_fills_are_confined_to_first_window() -> None:
    violations: list[str] = []
    for path, dashboard in _load_dashboards():
        root_panels = dashboard.get("panels")
        assert isinstance(root_panels, list)
        for panel in root_panels:
            if not isinstance(panel, dict):
                continue
            if panel.get("type") == "row":
                for child in panel.get("panels", []):
                    if not isinstance(child, dict):
                        continue
                    for violation in _area_fill_violations(child):
                        violations.append(
                            f"{path.name}:{panel.get('title')}:{child.get('id')} "
                            f"{violation}"
                        )
                continue
            grid = panel.get("gridPos")
            y = grid.get("y") if isinstance(grid, dict) else None
            if not isinstance(y, int) or y < FIRST_WINDOW_Y_EXCLUSIVE:
                continue
            for violation in _area_fill_violations(panel):
                violations.append(f"{path.name}:{panel.get('id')} {violation}")
    assert not violations, "area fills outside first window:\n" + "\n".join(
        violations
    )


def test_contract_helpers_fail_closed_on_sparse_or_filled_examples() -> None:
    sparse_row = {
        "panels": [
            {"type": "text", "gridPos": {"w": 12, "h": 4}},
            {
                "type": "timeseries",
                "gridPos": {"w": 12, "h": 4},
                "targets": [{"hide": True}],
            },
        ]
    }
    assert _row_density(sparse_row) == (0.0, 0.0)
    assert _area_fill_violations(
        {
            "type": "table",
            "fieldConfig": {
                "defaults": {"custom": {"cellOptions": {"type": "color-background"}}}
            },
        }
    ) == ["cellOptions=color-background"]
    assert _area_fill_violations(
        {"type": "stat", "options": {"graphMode": "area"}}
    ) == ["graphMode=area"]
    assert _area_fill_violations(
        {
            "type": "timeseries",
            "fieldConfig": {
                "overrides": [
                    {
                        "properties": [
                            {"id": "custom.fillOpacity", "value": 20},
                            {"id": "custom.gradientMode", "value": "opacity"},
                        ]
                    }
                ]
            },
        }
    ) == ["override fillOpacity=20", "override gradientMode=opacity"]
    assert _font_size_px(14.0, "pt") == pytest.approx(MIN_PANEL_TITLE_FONT_PX)
