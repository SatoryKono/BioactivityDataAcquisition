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
"""Geometry & purpose regression locks for shipped Grafana dashboards.

Enforced: DASH-LAYOUT-003/004, DASH-FIT-001/002/003, DASH-COPY-003/004/005/006/007,
DASH-PERF-003.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml

from tests.integration._dashboard_layout_budgets import (
    BANNED_TITLE_TOKENS,
    CANONICAL_ACTION_VERBS,
    DATA_PANEL_TYPES,
    FIRST_LOAD_Y_MAX,
    FIRST_WINDOW_Y,
    MIN_HEIGHT_ALLOWLIST,
    PENDING_ACTION_VERBS,
    PERFORMANCE_BUDGETS_PATH,
    SCALAR_DENSITY_ALLOWLIST,
    SCALAR_DENSITY_ENFORCED_UIDS,
    SCALAR_DENSITY_TYPES,
    SHELL_TITLES,
    STRADDLE_ALLOWLIST,
    VIEWPORT_ROWS,
    answer_panels,
    is_first_window_verdict_card,
    min_height_for,
    title_leading_verb,
    trust_gate_keys,
)
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
    panel_base_title,
)

from scripts.engineering.qa import report_dashboard_scalar_density as scalar_report

pytestmark = pytest.mark.integration

_RANGE_RE = re.compile(r"\$__range|\$\{__range")


def _grid(panel: dict[str, Any]) -> dict[str, Any]:
    grid = panel.get("gridPos")
    return grid if isinstance(grid, dict) else {}


def _has_live_target(panel: dict[str, Any]) -> bool:
    for target in panel.get("targets", []) or []:
        if not isinstance(target, dict) or target.get("hide") is True:
            continue
        for key in ("expr", "url", "rawSql"):
            value = target.get(key)
            if isinstance(value, str) and value.strip():
                return True
    return False


def _walk_with_parent(panels: list[Any], parent: dict[str, Any] | None = None):
    for panel in panels or []:
        if not isinstance(panel, dict):
            continue
        yield panel, parent
        if panel.get("type") == "row":
            nested = panel.get("panels") or []
            if isinstance(nested, list):
                yield from _walk_with_parent(nested, panel)


def _uses_grafana_range(panel: dict[str, Any]) -> bool:
    for target in panel.get("targets", []) or []:
        if not isinstance(target, dict):
            continue
        expr = target.get("expr")
        if isinstance(expr, str) and _RANGE_RE.search(expr):
            return True
    return False


# --- DASH-LAYOUT-003: row header height is exactly 1 -----------------------


def test_row_headers_are_single_grid_unit() -> None:
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "row":
                continue
            height = _grid(panel).get("h")
            assert height == 1, (
                f"{dashboard_path.name}: row {panel.get('title')!r} must have "
                f"gridPos.h == 1 (Grafana row header), got {height!r}"
            )


# --- DASH-LAYOUT-004: type-aware minimum height ----------------------------


def test_panels_meet_type_aware_minimum_height() -> None:
    violations: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel, parent in _walk_with_parent(dashboard.get("panels") or []):
            panel_type = panel.get("type")
            if not isinstance(panel_type, str):
                continue
            nested = parent is not None
            minimum = min_height_for(panel_type, nested=nested)
            if minimum is None:
                continue
            key = (dashboard_path.name, panel.get("id"))
            if key in MIN_HEIGHT_ALLOWLIST:
                continue
            height = _grid(panel).get("h")
            if not isinstance(height, int) or height < minimum:
                scope = "nested" if nested else "root"
                violations.append(
                    f"{dashboard_path.name}: {panel.get('title')!r} "
                    f"(id={panel.get('id')}, type={panel_type}, {scope}) "
                    f"h={height!r} < {minimum}"
                )
    assert not violations, "type-aware minimum height failures:\n" + "\n".join(
        violations
    )


# --- DASH-COPY-005a: unique panel titles within a dashboard -----------------


def test_panel_titles_are_unique_within_each_dashboard() -> None:
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        seen: dict[str, int] = {}
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") == "row":
                continue
            title = panel.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            base = panel_base_title(panel)
            assert base not in seen, (
                f"{dashboard_path.name}: duplicate panel title {base!r} "
                f"(ids {seen.get(base)} and {panel.get('id')}) — ambiguous purpose"
            )
            seen[base] = panel.get("id")


# --- DASH-COPY-005b: non-empty, non-placeholder titles ----------------------


def test_content_panels_have_meaningful_titles() -> None:
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") in {"row", "text"}:
                continue
            title = panel.get("title")
            assert isinstance(title, str) and title.strip(), (
                f"{dashboard_path.name}: panel id={panel.get('id')} must have a "
                "non-empty title"
            )
            assert panel_base_title(panel).strip().lower() not in BANNED_TITLE_TOKENS, (
                f"{dashboard_path.name}: panel id={panel.get('id')} uses a generic "
                f"placeholder title {title!r}"
            )


# --- DASH-COPY-007: data-typed panels must carry a live target --------------


def test_data_panels_declare_a_live_target() -> None:
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") not in DATA_PANEL_TYPES:
                continue
            assert _has_live_target(panel), (
                f"{dashboard_path.name}: {panel.get('title')!r} (id={panel.get('id')}, "
                f"type={panel.get('type')}) must declare >=1 live target "
                "(non-empty expr or Infinity url, hide != true)"
            )


# --- DASH-FIT-002: no root panel straddles the first-window fold ------------


def test_no_root_panel_straddles_the_fold() -> None:
    """Strict straddle: ``y < FIRST_WINDOW_Y < y + h`` (bottom == fold is allowed)."""
    violations: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in dashboard.get("panels", []):
            if not isinstance(panel, dict) or panel.get("type") == "row":
                continue
            grid = _grid(panel)
            y = grid.get("y")
            h = grid.get("h")
            if not isinstance(y, int) or not isinstance(h, int):
                continue
            if not (y < FIRST_WINDOW_Y < y + h):
                continue
            key = (dashboard_path.name, panel.get("id"))
            if key in STRADDLE_ALLOWLIST:
                continue
            violations.append(
                f"{dashboard_path.name}: {panel.get('title')!r} (id={panel.get('id')}) "
                f"straddles the fold (y={y}, h={h}, bottom={y + h} > {FIRST_WINDOW_Y})"
            )
    assert not violations, "first-window fold straddles:\n" + "\n".join(violations)


# --- DASH-FIT-003: canonical answer panels are root + first-window ----------


def test_canonical_answer_panels_are_root_first_window() -> None:
    expected = answer_panels()
    shipped = {path.name for path in get_dashboard_files()}
    missing_maps = sorted(name for name in expected if name not in shipped)
    assert not missing_maps, f"answer map refers to missing dashboards: {missing_maps}"

    for dashboard_path in get_dashboard_files():
        specs = expected.get(dashboard_path.name)
        assert specs, f"{dashboard_path.name} missing from answer-panel map"
        dashboard = load_dashboard(dashboard_path)
        root_by_id = {
            panel.get("id"): panel
            for panel in dashboard.get("panels") or []
            if isinstance(panel, dict)
        }
        for spec in specs:
            panel_id = spec.get("id")
            title = spec.get("title")
            panel = root_by_id.get(panel_id)
            assert panel is not None, (
                f"{dashboard_path.name}: answer panel id={panel_id} "
                f"({title!r}) must be a root panel"
            )
            assert panel.get("type") != "row", (
                f"{dashboard_path.name}: answer panel id={panel_id} must not be a row"
            )
            assert panel.get("title") == title, (
                f"{dashboard_path.name}: answer panel id={panel_id} title "
                f"{panel.get('title')!r} != {title!r}"
            )
            y = _grid(panel).get("y")
            assert isinstance(y, int) and y < FIRST_WINDOW_Y, (
                f"{dashboard_path.name}: {title!r} (id={panel_id}) must sit in "
                f"the first window (y < {FIRST_WINDOW_Y}), got y={y!r}"
            )


# --- DASH-COPY-004: first-window Monitor* must not use $__range -------------


def test_first_window_monitor_panels_do_not_use_grafana_range() -> None:
    violations: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in dashboard.get("panels") or []:
            if not isinstance(panel, dict) or panel.get("type") == "row":
                continue
            y = _grid(panel).get("y")
            if not isinstance(y, int) or y >= FIRST_WINDOW_Y:
                continue
            title = str(panel.get("title") or "")
            if title_leading_verb(title) != "Monitor":
                continue
            if _uses_grafana_range(panel):
                violations.append(
                    f"{dashboard_path.name}: {title!r} (id={panel.get('id')}) "
                    "is a first-window Monitor panel and must not use $__range"
                )
    assert not violations, "Monitor+$__range on first window:\n" + "\n".join(violations)


# --- DASH-COPY-006: first-window verdict cards state the palette ------------


def test_first_window_verdict_cards_state_interpretation() -> None:
    required = ("OK", "WARN", "CRIT", "UNKNOWN")
    gates = trust_gate_keys()
    violations: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in dashboard.get("panels") or []:
            if not isinstance(panel, dict):
                continue
            y = _grid(panel).get("y")
            if not isinstance(y, int) or y >= FIRST_WINDOW_Y:
                continue
            if not is_first_window_verdict_card(panel):
                continue
            description = str(panel.get("description") or "").upper()
            missing = [token for token in required if token not in description]
            if (dashboard_path.name, panel.get("id")) in gates:
                if "INCOMPLETE" not in description:
                    missing.append("INCOMPLETE")
            if missing:
                violations.append(
                    f"{dashboard_path.name}: {panel.get('title')!r} "
                    f"(id={panel.get('id')}) description missing {missing}"
                )
    assert not violations, "verdict-card description gaps:\n" + "\n".join(violations)


# --- DASH-FIT-001: always-visible non-row stack fits the viewport -----------


def test_always_visible_nonrow_stack_fits_viewport() -> None:
    """DASH-FIT-001: max(y+h) of root non-row panels <= VIEWPORT_ROWS.

    Collapsed row headers may sit on/after the fold. The Provider 9104
    straddle remains a governed exception (same allowlist as DASH-FIT-002).
    """
    assert VIEWPORT_ROWS is not None
    violations: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        bottoms: list[int] = []
        for panel in dashboard.get("panels") or []:
            if not isinstance(panel, dict) or panel.get("type") == "row":
                continue
            if (dashboard_path.name, panel.get("id")) in STRADDLE_ALLOWLIST:
                continue
            grid = _grid(panel)
            y = grid.get("y")
            h = grid.get("h")
            if isinstance(y, int) and isinstance(h, int):
                bottoms.append(y + h)
        bottom = max(bottoms, default=0)
        if bottom > VIEWPORT_ROWS:
            violations.append(
                f"{dashboard_path.name}: always-visible non-row bottom "
                f"{bottom} > VIEWPORT_ROWS={VIEWPORT_ROWS}"
            )
    assert not violations, "DASH-FIT-001 viewport overflows:\n" + "\n".join(violations)


# --- DASH-COPY-003 exclusive: canonical action-first verbs ------------------


def test_content_panel_titles_use_canonical_action_verbs() -> None:
    """Exclusive allowlist. Text, row, and shared-shell titles are exempt."""
    assert not PENDING_ACTION_VERBS
    violations: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") in {"row", "text"}:
                continue
            title = panel_base_title(panel).strip()
            if not title or title in SHELL_TITLES:
                continue
            verb = title_leading_verb(title)
            if verb not in CANONICAL_ACTION_VERBS:
                violations.append(
                    f"{dashboard_path.name}: {title!r} (id={panel.get('id')}) "
                    f"starts with {verb!r}, not a canonical action verb"
                )
    assert not violations, "DASH-COPY-003 exclusive verb failures:\n" + "\n".join(
        violations
    )


# --- DASH-PERF-003: the two folds stay distinct and named -------------------


def test_fold_constants_are_distinct_and_named() -> None:
    assert FIRST_WINDOW_Y == 18
    assert FIRST_LOAD_Y_MAX == 28
    assert FIRST_WINDOW_Y != FIRST_LOAD_Y_MAX, (
        "answer fold (FIRST_WINDOW_Y) and PromQL/HTTP budget window "
        "(FIRST_LOAD_Y_MAX) are different concepts and must remain separate"
    )
    perf = yaml.safe_load(PERFORMANCE_BUDGETS_PATH.read_text(encoding="utf-8"))
    assert int(perf["first_screen_y_max"]) == FIRST_LOAD_Y_MAX, (
        "layout-budgets.yaml:first_load_y_max must equal "
        "performance-budgets.yaml:first_screen_y_max"
    )
    assert VIEWPORT_ROWS == 18
    assert 1 <= VIEWPORT_ROWS <= FIRST_LOAD_Y_MAX


def test_allowlists_carry_governance_metadata() -> None:
    for name, allowlist in (
        ("straddle", STRADDLE_ALLOWLIST),
        ("min_height", MIN_HEIGHT_ALLOWLIST),
    ):
        assert allowlist, f"{name} allowlist must not be empty while exceptions exist"
        for key, meta in allowlist.items():
            for field in ("owner", "rationale", "retire_when"):
                assert meta.get(field, "").strip(), f"{name} {key} missing {field}"


# --- DASH-DENSITY-002: scalar information density (values/area) -------------


def test_scalar_density_types_match_contract() -> None:
    """The survey tool and the layout contract must agree on scalar types + fold."""
    assert scalar_report.SCALAR_TYPES == SCALAR_DENSITY_TYPES
    assert scalar_report.FIRST_WINDOW_Y == FIRST_WINDOW_Y


def test_scalar_density_survey_runs_on_shipped_dashboards() -> None:
    """Report-only smoke: DASH-DENSITY-002 machinery runs on the real suite."""
    surveyed = 0
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        result = scalar_report.survey_dashboard(dashboard)
        assert isinstance(result.get("groups"), list)
        surveyed += 1
    assert surveyed >= 7


def test_group_scalar_density_exceeds_first_screen_where_enforced() -> None:
    """DASH-DENSITY-002 gate. Enforced per-uid (opt-in) after scalar remediation.

    The enforced set is intentionally empty until a dashboard's scalar groups are
    remediated to out-densify its first screen (see layout-budgets.yaml and
    ``report_dashboard_scalar_density --check``); the mechanism ships now.
    """
    shipped = {load_dashboard(path).get("uid") for path in get_dashboard_files()}
    assert SCALAR_DENSITY_ENFORCED_UIDS <= shipped, (
        "scalar_density_enforced_uids must reference shipped dashboards"
    )
    violations: list[str] = []
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        uid = dashboard.get("uid")
        if uid not in SCALAR_DENSITY_ENFORCED_UIDS:
            continue
        result = scalar_report.survey_dashboard(dashboard)
        for group in result["groups"]:
            if (
                group["passes"] is False
                and (
                    dashboard_path.name,
                    group["row_id"],
                )
                not in SCALAR_DENSITY_ALLOWLIST
            ):
                violations.append(
                    f"{uid}::{group['row_title']} rho={group['density']} "
                    f"<= first-screen {result['first_screen_density']}"
                )
    assert not violations, (
        "DASH-DENSITY-002 group scalar density below first screen:\n"
        + "\n".join(violations)
    )
