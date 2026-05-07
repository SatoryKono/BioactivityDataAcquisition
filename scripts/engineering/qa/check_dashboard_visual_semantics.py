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
    ("bioetl-runtime.json", "Monitor Runtime Error Rate"): [
        {"color": "green", "value": None},
        {"color": "orange", "value": 0.05},
        {"color": "red", "value": 0.2},
    ],
    ("bioetl-runtime.json", "Monitor Worst Stage Lag"): [
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


def iter_panels(panels: list[dict]) -> list[dict]:
    collected: list[dict] = []
    for panel in panels:
        if panel.get("type") == "row" and isinstance(panel.get("panels"), list):
            collected.extend(iter_panels(panel["panels"]))
        else:
            collected.append(panel)
    return collected


def _stat_panel_visual_semantics_errors(dashboard_path: Path, panel: dict) -> list[str]:
    title = panel.get("title", "<untitled>")
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    errors: list[str] = []

    color_mode = defaults.get("color", {}).get("mode")
    if color_mode != "thresholds":
        errors.append(
            f"{dashboard_path}: panel '{title}' must use color.mode=thresholds"
        )

    expected_steps = _expected_threshold_steps(dashboard_path, str(title))
    steps = defaults.get("thresholds", {}).get("steps")
    if expected_steps is not None and steps != expected_steps:
        errors.append(
            f"{dashboard_path}: panel '{title}' must use standardized threshold steps"
        )

    mappings = defaults.get("mappings", [])
    if _requires_unknown_mapping(panel) and EXPECTED_UNKNOWN_MAPPING not in mappings:
        errors.append(
            f"{dashboard_path}: panel '{title}' must map null to UNKNOWN/gray"
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


def _panel_errors(dashboard_path: Path, panel: dict) -> list[str]:
    if panel.get("type") not in {"stat", "gauge"}:
        return []
    if not _is_status_like_panel(panel):
        return []
    return [
        *_stat_panel_visual_semantics_errors(dashboard_path, panel),
        *_l0_terminology_errors(dashboard_path, panel),
    ]


def _dashboard_errors(dashboard_path: Path) -> list[str]:
    payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    return [
        error
        for panel in iter_panels(payload.get("panels", []))
        for error in _panel_errors(dashboard_path, panel)
    ]


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
