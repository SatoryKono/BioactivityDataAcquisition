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
"""Mandatory DASH-FIT-004 gate: no internal scroll on any first-window panel.

Required on every code, test, or documentation change (dedicated CI workflow
``dashboard-first-window-noscroll.yml``, Tests semantic gate, and pre-push).
Applies to every root non-row panel with ``gridPos.y < FIRST_WINDOW_Y``, not
only text/stat/table. Overflow-clip is not a fix. Allowlist must stay empty.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_CONTAINMENT_TYPES,
    FIRST_WINDOW_OVERFLOW_ALLOWLIST,
    FIRST_WINDOW_Y,
    HORIZONTAL_SCROLL_ALLOWLIST,
    is_first_window_panel,
    select_first_window_panels,
)
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_OVERFLOW_RE = re.compile(r"overflow(?:-[xy])?\s*:\s*(auto|scroll|hidden)", re.I)
_NAV_MARKERS = ("bioetl-nav", "Navigate Dashboards")
_WORKFLOW = Path(".github/workflows/dashboard-first-window-noscroll.yml")
_TESTS_WORKFLOW = Path(".github/workflows/tests.yml")
_PRE_COMMIT = Path(".pre-commit-config.yaml")
_THIS_TEST = "tests/integration/test_dashboard_first_window_noscroll.py"


def _root_panels(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    return [panel for panel in dashboard.get("panels") or [] if isinstance(panel, dict)]


def _html_content(panel: dict[str, Any]) -> str:
    options = panel.get("options")
    if not isinstance(options, dict):
        return ""
    content = options.get("content")
    return content if isinstance(content, str) else ""


def _is_nav_panel(panel: dict[str, Any]) -> bool:
    html = _html_content(panel)
    title = str(panel.get("title") or "")
    return any(marker in html or marker in title for marker in _NAV_MARKERS)


def _is_nav_spacer(kind: str, html: str, match_start: int, match_end: int) -> bool:
    window = html[max(0, match_start - 120) : match_end + 80]
    compact = re.sub(r"\s+", "", window)
    return (
        kind == "hidden"
        and "height:0" in compact
        and ("aria-hidden" in window or "flex:11 100%" in compact)
    )


def _json_overflow_hits(payload: object, prefix: str) -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}"
            key_l = str(key).lower()
            if "overflow" in key_l and str(value).lower() in {
                "auto",
                "scroll",
                "hidden",
            }:
                hits.append(f"{path}={value}")
            hits.extend(_json_overflow_hits(value, path))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            hits.extend(_json_overflow_hits(item, f"{prefix}[{index}]"))
    return hits


def _first_window_scroll_violations(path: Path, dashboard: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    first_window = select_first_window_panels(_root_panels(dashboard))
    if not first_window:
        return [f"{path.name}: no first-window panels"]
    for panel in first_window:
        panel_id = panel.get("id")
        grid = panel.get("gridPos") or {}
        bottom = int(grid.get("y", 0)) + int(grid.get("h", 0))
        if bottom > FIRST_WINDOW_Y:
            violations.append(
                f"{path.name}:id={panel_id} first-window bottom "
                f"{bottom} > FIRST_WINDOW_Y={FIRST_WINDOW_Y}"
            )
        html = _html_content(panel)
        for match in _OVERFLOW_RE.finditer(html):
            kind = match.group(1).lower()
            if _is_nav_spacer(kind, html, match.start(), match.end()):
                continue
            violations.append(
                f"{path.name}:id={panel_id} first-window overflow:{kind} "
                f"at html[{match.start()}]"
            )
        if html and "white-space:nowrap" in html and not _is_nav_panel(panel):
            violations.append(
                f"{path.name}:id={panel_id} first-window nowrap risks scroll"
            )
        for hit in _json_overflow_hits(
            {
                "options": panel.get("options"),
                "fieldConfig": panel.get("fieldConfig"),
            },
            "panel",
        ):
            if "overflow" in hit and "hidden" in hit.lower():
                violations.append(
                    f"{path.name}:id={panel_id} overflow-clip is not a FIT-004 fix: {hit}"
                )
            elif "overflow" in hit:
                violations.append(
                    f"{path.name}:id={panel_id} first-window JSON overflow: {hit}"
                )
    return violations


@pytest.mark.parametrize(
    "dashboard_path",
    get_dashboard_files(),
    ids=lambda path: path.stem,
)
def test_first_window_has_no_internal_scroll(dashboard_path: Path) -> None:
    """Every first-window panel on this dashboard must not declare internal scroll."""
    dashboard = load_dashboard(dashboard_path)
    first_window = select_first_window_panels(_root_panels(dashboard))
    assert first_window, f"{dashboard_path.name} has no first-window panels"
    assert all(is_first_window_panel(panel) for panel in first_window)
    violations = _first_window_scroll_violations(dashboard_path, dashboard)
    assert not violations, "first-window scroll:\n" + "\n".join(violations)


def test_first_window_overflow_allowlists_stay_empty() -> None:
    assert FIRST_WINDOW_OVERFLOW_ALLOWLIST == {}
    assert HORIZONTAL_SCROLL_ALLOWLIST == {}


def test_containment_types_cover_every_shipped_first_window_panel() -> None:
    present: set[str] = set()
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in select_first_window_panels(_root_panels(dashboard)):
            present.add(str(panel.get("type") or ""))
    missing = sorted(present.difference(FIRST_WINDOW_CONTAINMENT_TYPES))
    assert not missing, (
        "first_window_containment_types must include every first-window panel "
        f"type: {missing}"
    )


def test_first_window_noscroll_gate_is_required_on_code_tests_and_docs() -> None:
    """The gate must run on code, test, and documentation changes — not only JSON."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    tests_workflow = _TESTS_WORKFLOW.read_text(encoding="utf-8")
    pre_commit = _PRE_COMMIT.read_text(encoding="utf-8")
    assert _WORKFLOW.is_file(), "dedicated no-scroll workflow is missing"
    assert "paths-ignore:" not in workflow
    assert "paths:" not in workflow.split("jobs:", maxsplit=1)[0]
    assert _THIS_TEST.replace("\\", "/") in workflow
    assert "test_dashboard_first_window_noscroll.py" in tests_workflow
    assert "check-dashboard-first-window-noscroll" in pre_commit
    assert "test_dashboard_first_window_noscroll.py" in pre_commit
    hook = pre_commit[pre_commit.index("check-dashboard-first-window-noscroll") :]
    hook = hook.split("- id:", maxsplit=1)[0]
    assert "src/" in hook
    assert "tests/" in hook
    assert "docs/" in hook
