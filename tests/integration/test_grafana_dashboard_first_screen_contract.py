# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportAny=false
# pyright: reportImplicitStringConcatenation=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""First-screen Grafana dashboard contracts for operator triage dashboards."""

from pathlib import Path

import pytest
import yaml

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    panel_declared_row_cap,
)
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_navigation_links,
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration

_DESIGN_SYSTEM_PATH = Path("docs/03-guides/dashboards/design-system.md")
_OBSERVABILITY_RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")
_DASHBOARD_DIR = Path("grafana/dashboards")


def _panels_overlap(
    left: dict[str, object],
    right: dict[str, object],
) -> bool:
    left_pos = left.get("gridPos", {})
    right_pos = right.get("gridPos", {})
    assert isinstance(left_pos, dict)
    assert isinstance(right_pos, dict)
    left_x = int(left_pos.get("x", 0))
    left_y = int(left_pos.get("y", 0))
    left_w = int(left_pos.get("w", 0))
    left_h = int(left_pos.get("h", 0))
    right_x = int(right_pos.get("x", 0))
    right_y = int(right_pos.get("y", 0))
    right_w = int(right_pos.get("w", 0))
    right_h = int(right_pos.get("h", 0))
    return (
        left_x < right_x + right_w
        and right_x < left_x + left_w
        and left_y < right_y + right_h
        and right_y < left_y + left_h
    )


def _root_empty_segments(panels: list[dict[str, object]]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for panel in panels:
        grid_pos = panel.get("gridPos", {})
        assert isinstance(grid_pos, dict)
        y = int(grid_pos.get("y", 0))
        h = int(grid_pos.get("h", 0))
        if h <= 0:
            continue
        end = y + h - 1
        nested = panel.get("panels")
        if panel.get("type") == "row" and isinstance(nested, list):
            nested_ends = []
            for child in nested:
                if not isinstance(child, dict):
                    continue
                child_grid = child.get("gridPos")
                if not isinstance(child_grid, dict):
                    continue
                child_y = int(child_grid.get("y", 0))
                child_h = int(child_grid.get("h", 0))
                if child_h > 0:
                    nested_ends.append(child_y + child_h - 1)
            if nested_ends:
                end = max(end, max(nested_ends))
        spans.append((y, end))

    if not spans:
        return []

    occupied: set[int] = set()
    for start, end in spans:
        occupied.update(range(start, end + 1))

    min_y = min(start for start, _ in spans)
    max_y = max(end for _, end in spans)
    gaps: list[tuple[int, int]] = []
    gap_start: int | None = None
    for row in range(min_y, max_y + 1):
        if row not in occupied:
            if gap_start is None:
                gap_start = row
        elif gap_start is not None:
            gaps.append((gap_start, row - 1))
            gap_start = None
    if gap_start is not None:
        gaps.append((gap_start, max_y))
    return gaps


def test_design_system_defines_first_screen_decision_matrix() -> None:
    """#3700: design docs must define first-screen responsibility explicitly."""
    text = _DESIGN_SYSTEM_PATH.read_text(encoding="utf-8")
    required_tokens = {
        "First-screen responsibility and panel decision matrix",
        "`bioetl-runtime`",
        "`bioetl-provider-health-v2`",
        "`bioetl-dq-v2`",
        "`bioetl_runtime_current_status_trusted`",
        "`bioetl_provider_current_status`",
        "`bioetl_dq_current_status`",
        "Selected-range count/rate/trend",
        "Provider Evidence uses the selected Run ID on Overview",
        "Layout grammar by dashboard role",
        "Visibility tiers and collapse policy",
        "L0 answer-first hub",
        "Forensic explorer",
        "`Tier 1`",
        "`Tier 4`",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        "dashboard design-system must preserve first-screen decision matrix; "
        f"missing={missing}"
    )


def test_primary_dashboards_expose_common_context_header_panels() -> None:
    specs = {
        "bioetl-control-plane-v1.json": (9400, 9422),
        "bioetl-overview-v2.json": (99, 9604),
        "bioetl-dq-v2.json": (9400,),
        "bioetl-incident-v1.json": (9400, 9401),
    }
    for filename, ids in specs.items():
        dashboard = load_dashboard(_DASHBOARD_DIR / filename)
        panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
        for pid in ids:
            panel = panels[pid]
            assert panel["gridPos"]["y"] == 2
            assert panel["gridPos"]["h"] == 3
        if filename == "bioetl-control-plane-v1.json":
            assert panels[9422]["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"
            assert "SELECT RUN" in panels[9422]["description"]
            assert "QUERY ERROR" in panels[9422]["description"]


def test_current_status_recording_rules_are_canonicalized() -> None:
    """#3698: Runtime/Provider/DQ current status belongs in recording rules."""
    payload = yaml.safe_load(_OBSERVABILITY_RULES_PATH.read_text(encoding="utf-8"))
    records: dict[str, list[dict[str, object]]] = {}
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            record = rule.get("record")
            if isinstance(record, str):
                records.setdefault(record, []).append(rule)

    required_records = {
        "bioetl_runtime_current_status",
        "bioetl_runtime_current_status_trusted",
        "bioetl_runtime_current_blocker_reason",
        "bioetl_provider_current_status",
        "bioetl_provider_current_cause",
        "bioetl_dq_current_status",
        "bioetl_dq_current_reason",
    }
    missing = sorted(record for record in required_records if record not in records)
    assert not missing, f"missing canonical current-status records: {missing}"

    for status_record in (
        "bioetl_runtime_current_status",
        "bioetl_runtime_current_status_trusted",
        "bioetl_provider_current_status",
        "bioetl_dq_current_status",
    ):
        expressions = [str(rule.get("expr", "")) for rule in records[status_record]]
        assert expressions
        assert all("$__range" not in expression for expression in expressions), (
            f"{status_record} must use fixed current windows/rules, not Grafana range"
        )


def test_runtime_provider_dq_first_screens_use_canonical_current_status() -> None:
    incident = load_dashboard(_DASHBOARD_DIR / "bioetl-incident-v1.json")
    current = next(p for p in get_dashboard_panels(incident) if p["id"] == 9401)
    assert "bioetl_workflow_scope_priority_by_input" in current["targets"][0]["expr"]
    assert "Run ID does not filter" in current["description"]
    for filename, pid in (
        ("bioetl-overview-v2.json", 9002),
        ("bioetl-dq-v2.json", 9406),
    ):
        dashboard = load_dashboard(_DASHBOARD_DIR / filename)
        panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == pid)
        assert panel["gridPos"]["y"] + panel["gridPos"]["h"] <= FIRST_WINDOW_Y
        assert all(
            "selected-run-status?" in t["url"] and "run_id=${run_id}" in t["url"]
            for t in panel["targets"]
        )
        assert all("expr" not in t for t in panel["targets"])
    overview = load_dashboard(_DASHBOARD_DIR / "bioetl-overview-v2.json")
    assert {9480, 9481}.issubset({p["id"] for p in overview["panels"]})


def test_dual_status_twins_are_removed_from_runtime_and_dq() -> None:
    assert not (_DASHBOARD_DIR / "bioetl-runtime.json").exists()
    dq = load_dashboard(_DASHBOARD_DIR / "bioetl-dq-v2.json")
    panels = {p["id"]: p for p in get_dashboard_panels(dq)}
    assert 9406 in panels and 9401 not in panels
    assert "Monitor Current DQ Status" not in {p["title"] for p in panels.values()}
    overview = load_dashboard(_DASHBOARD_DIR / "bioetl-overview-v2.json")
    # The headline reuses the same assessment rather than another independent status query.
    panels = {p["id"]: p for p in get_dashboard_panels(overview)}
    assert panels[9604]["targets"] == panels[9603]["targets"]


def test_overview_and_control_plane_first_screens_use_role_appropriate_queries() -> (
    None
):
    """Overview/Control Plane answer rows must stay on projected current-state or fixed-window evidence."""
    expectations = {
        "bioetl-overview-v2.json": {
            "Review Run Domains": "selected-run-status",
        },
        "bioetl-control-plane-v1.json": {
            "Review Exact Replay Readiness": "selected-run-status",
        },
    }

    for dashboard_name, panel_expectations in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, expected_metric in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"{dashboard_name} must expose first-screen panel {panel_title!r}"
            )
            # Overview answer cards sit at y<=11. Trust keeps Prom KPI cards on
            # the first window (y<18) below the named Review* tables at y=8.
            max_answer_y = (
                15 if dashboard_name == "bioetl-control-plane-v1.json" else 12
            )
            assert panel.get("gridPos", {}).get("y", 999) <= max_answer_y, (
                f"{dashboard_name}:{panel_title} must stay in the answer/evidence band"
            )
            expressions = [
                str(target.get("expr") or target.get("url") or "")
                for target in panel.get("targets", [])
                if isinstance(target, dict)
            ]
            assert any(expected_metric in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must consume {expected_metric}"
            )
            assert all("$__range" not in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must not use selected-range semantics"
            )


def test_current_status_and_current_cause_panels_do_not_use_zero_fallback() -> None:
    """Fail-closed current-status surfaces must not hide missing telemetry behind or vector(0)."""
    expectations = {
        "bioetl-incident-v1.json": [
            "Review Runtime Blockers",
        ],
        "bioetl-overview-v2.json": [],
        "bioetl-dq-v2.json": [],
    }

    for dashboard_name, panel_titles in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"{dashboard_name} must expose current panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert expressions, (
                f"{dashboard_name}:{panel_title} must define query expressions"
            )
            assert all("or vector(0)" not in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must preserve UNKNOWN instead of zero fallback"
            )


def test_required_trust_markers_stay_visible_on_target_dashboards() -> None:
    """Runtime coverage must say missing telemetry is not proof of delivery."""
    expectations = {
        "bioetl-incident-v1.json": (
            "Monitor Coverage",
            ("evidence confidence",),
        ),
    }

    for dashboard_name, (panel_title, required_tokens) in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        panel = panels.get(panel_title)
        assert panel is not None, (
            f"{dashboard_name} must expose required trust marker {panel_title!r}"
        )
        fleet_row = next(row for row in dashboard["panels"] if row.get("id") == 8808)
        assert fleet_row["collapsed"] is True
        assert panel["id"] in {p["id"] for p in get_dashboard_panels(fleet_row)}
        assert panel.get("fieldConfig", {}).get("defaults", {}).get("noValue") == (
            "UNKNOWN"
        )
        description = str(panel.get("description", "")).lower()
        for token in required_tokens:
            assert token in description, (
                f"{dashboard_name}:{panel_title} description must mention {token!r}"
            )


def test_dashboard_top_level_grid_positions_do_not_overlap() -> None:
    """Shipped dashboards must not hide cards under navigation/scope rows."""
    for dashboard_path in sorted(_DASHBOARD_DIR.glob("*.json")):
        dashboard = load_dashboard(dashboard_path)
        panels = [
            panel
            for panel in dashboard.get("panels", [])
            if isinstance(panel, dict) and isinstance(panel.get("gridPos"), dict)
        ]
        overlaps: list[str] = []
        for index, left in enumerate(panels):
            for right in panels[index + 1 :]:
                if not _panels_overlap(left, right):
                    continue
                overlaps.append(
                    f"{left.get('id')}:{left.get('title')} overlaps "
                    f"{right.get('id')}:{right.get('title')}"
                )

        assert not overlaps, (
            f"{dashboard_path.name} has overlapping top-level grid positions: "
            f"{overlaps}"
        )


def test_dashboard_top_level_grid_positions_do_not_leave_root_gaps() -> None:
    """Top-level layout bands must pack cleanly unless a dashboard documents an exception."""
    for dashboard_path in sorted(_DASHBOARD_DIR.glob("*.json")):
        dashboard = load_dashboard(dashboard_path)
        panels = [
            panel
            for panel in dashboard.get("panels", [])
            if isinstance(panel, dict) and isinstance(panel.get("gridPos"), dict)
        ]
        gaps = _root_empty_segments(panels)
        # 1fee6a viewport-fit: DQ 9406 h4 y13 bottom17 leaves row 17 empty
        # before collapsed row at y18; incident keeps bottom17 with y13 h4.
        # Allow the documented single-row gap for dq-v2.
        if dashboard_path.name == "bioetl-dq-v2.json" and gaps == [(17, 17)]:
            continue
        assert not gaps, (
            f"{dashboard_path.name} has unexplained empty root row gaps: {gaps}"
        )


def test_control_plane_exact_readiness_shares_selected_run_row() -> None:
    """The exact-replay verdict sits beside, not below, the selected-run rail."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {panel.get("id"): panel for panel in dashboard.get("panels", [])}
    selected_run = panels[9400]["gridPos"]
    exact_readiness = panels[9422]["gridPos"]

    assert exact_readiness["y"] == selected_run["y"]
    assert selected_run["x"] == 0
    assert exact_readiness["x"] == selected_run["w"]
    assert selected_run["w"] + exact_readiness["w"] == 24


def test_provider_and_dq_range_evidence_panels_are_below_first_screen() -> None:
    assert not (_DASHBOARD_DIR / "bioetl-provider-health-v2.json").exists()
    incident = load_dashboard(_DASHBOARD_DIR / "bioetl-incident-v1.json")
    row = next(p for p in incident["panels"] if p["id"] == 8808)
    assert row["collapsed"] and row["gridPos"]["y"] >= FIRST_WINDOW_Y
    ids = {p["id"] for p in get_dashboard_panels(row)}
    assert {111, 205, 9101, 9102, 9996, 9997}.issubset(ids)
    for filename in ("bioetl-overview-v2.json", "bioetl-dq-v2.json"):
        dashboard = load_dashboard(_DASHBOARD_DIR / filename)
        first = [
            p
            for p in dashboard["panels"]
            if p["type"] != "row" and p["gridPos"]["y"] < FIRST_WINDOW_Y
        ]
        assert first
        assert all("expr" not in t for p in first for t in p.get("targets", []))


def test_first_screen_scope_and_cta_panels_document_role_and_scope() -> None:
    specs = {
        "bioetl-control-plane-v1.json": (9400, "SELECTED RUN"),
        "bioetl-overview-v2.json": (99, "SELECTED RUN"),
        "bioetl-dq-v2.json": (9400, "SELECTED RUN"),
        "bioetl-incident-v1.json": (9400, "CURRENT"),
    }
    for filename, (pid, badge) in specs.items():
        dashboard = load_dashboard(_DASHBOARD_DIR / filename)
        panel = next(p for p in dashboard["panels"] if p["id"] == pid)
        assert badge in panel["description"]
        content = panel["options"]["content"]
        assert badge in content or (badge == "SELECTED RUN" and "${run_id}" in content)
        assert panel["gridPos"]["y"] <= 4
        assert "overflow:hidden" not in panel["options"]["content"]


def test_navigation_bus_panels_document_handoff_policy() -> None:
    """Top navigation text panels should expose machine-readable handoff semantics."""
    required_tokens = (
        "same-tab",
        "current time range",
        "scope",
    )
    tracing_tokens = (
        "optional tracing profile",
        "available only for traced runs",
    )

    for dashboard_path in get_dashboard_files():
        # Run Explorer is a browse surface: it has no dashboard-bus panel.
        if dashboard_path.name == "bioetl-run-explorer-v1.json":
            continue
        dashboard = load_dashboard(dashboard_path)
        navigation_links = get_dashboard_navigation_links(dashboard)
        has_explore_traces = any(
            str(link.get("title", "")) == "Explore Traces" for link in navigation_links
        )
        panel = next(
            (
                candidate
                for candidate in get_dashboard_panels(dashboard)
                if candidate.get("id") == 1000
            ),
            None,
        )
        assert panel is not None, (
            f"{dashboard_path.name} must expose top navigation guidance panel"
        )
        assert panel.get("gridPos", {}).get("y", 999) == 0, (
            f"{dashboard_path.name}:navigation panel must remain at y=0"
        )
        description = str(panel.get("description", "")).lower()
        assert description, (
            f"{dashboard_path.name}:navigation panel must define "
            "machine-readable description text"
        )
        if dashboard_path.name in {
            "bioetl-control-plane-v1.json",
            "bioetl-overview-v2.json",
            "bioetl-runtime.json",
        }:
            for token in required_tokens:
                normalized_description = description.replace("same tab", "same-tab")
                assert token in normalized_description, (
                    f"{dashboard_path.name}:navigation panel description "
                    f"must mention {token!r}"
                )
        if has_explore_traces:
            assert any(token in description for token in tracing_tokens), (
                f"{dashboard_path.name}:navigation panel description "
                "must document traced-run-only Explore Traces semantics"
            )


def test_current_status_headlines_use_instant_queries() -> None:
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-incident-v1.json")
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    for pid in (9401, 18940):
        panel = panels[pid]
        assert panel["targets"]
        assert all(t.get("instant") is True for t in panel["targets"])
        assert all("$__range" not in t["expr"] for t in panel["targets"])


def test_run_explorer_shows_ten_rows_and_only_the_browse_surface() -> None:
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-run-explorer-v1.json")
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    assert len(panels) == 2
    assert 1000 not in panels
    assert 9450 not in panels
    assert not ({3098, 3099, 3011, 3012, 3013, 3014, 3020, 3022, 3023} & panels.keys())
    browse = panels[3010]
    grid = browse["gridPos"]
    assert grid["y"] + grid["h"] <= FIRST_WINDOW_Y
    assert panel_declared_row_cap(browse) == 10
    assert browse["options"]["footer"]["enablePagination"] is False
    assert browse["options"]["cellHeight"] == "sm"
    assert "last 10" in browse["title"]


def test_run_explorer_first_screen_empty_copy_has_no_selector_dollars() -> None:
    """Selected-run first screen must not leak `$pipeline` / `$run_id` into noValue."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-run-explorer-v1.json")
    panels = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    for panel_id in (3010,):
        no_value = str(
            panels[panel_id]
            .get("fieldConfig", {})
            .get("defaults", {})
            .get("noValue", "")
        )
        assert no_value, f"panel {panel_id} missing noValue"
        assert "$" not in no_value, (
            f"panel {panel_id} noValue still interpolates a selector: {no_value!r}"
        )


def test_overview_alerts_row_is_collapsed() -> None:
    """#11268: fleet alert row is not on Overview when Run ID is always selected."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-overview-v2.json")
    assert all(panel.get("id") != 9600 for panel in dashboard.get("panels", []))


def test_incident_domain_suspect_row_is_collapsed() -> None:
    """#8752: Domain Suspect Details stays T4 until ranked-suspect triage needs it."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-incident-v1.json")
    row = next(
        panel for panel in dashboard.get("panels", []) if panel.get("id") == 2099
    )
    assert row.get("collapsed") is True
    nested_ids = {child.get("id") for child in (row.get("panels") or [])}
    assert {2002, 2003, 2004} <= nested_ids


def test_incident_alert_evidence_is_collapsed_below_the_fold() -> None:
    """#10254: alerts stay on the first screen; history/impact stay collapsed."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-incident-v1.json")
    root = [panel for panel in dashboard.get("panels", []) if isinstance(panel, dict)]
    root_ids = {panel.get("id") for panel in root}
    assert 2005 in root_ids
    assert 2006 not in root_ids
    assert 2007 not in root_ids
    alerts = next(panel for panel in root if panel.get("id") == 2005)
    assert alerts.get("gridPos") == {"h": 5, "w": 24, "x": 0, "y": 12}
    row = next(panel for panel in root if panel.get("id") == 2020)
    assert row.get("type") == "row"
    assert row.get("collapsed") is True
    assert row["gridPos"]["y"] in {FIRST_WINDOW_Y - 1, FIRST_WINDOW_Y}
    nested_ids = {child.get("id") for child in (row.get("panels") or [])}
    assert nested_ids == {2006, 2007}
