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
"""First-screen Grafana dashboard contracts for operator triage dashboards."""

from pathlib import Path

import pytest
import yaml

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    panel_declared_row_cap,
)
from tests.integration._grafana_test_support import (
    get_row_child_panels,
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
        "Provider Health first screen uses current-status gauges only; range evidence is collapsed (epic #6572)",
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
    """Primary dashboards keep Status shell on first paint; Run context is lazy (#6573/DRM-R)."""
    # Contract (not frozen pixels): context band follows the four-unit
    # navigation surface required by the 19px/16px typography contract.
    header_ids = (9400, 9401)
    lazy_shell_ids = (9402, 9403)
    dashboard_names = {
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
    }

    for dashboard_name in dashboard_names:
        dashboard = load_dashboard(_DASHBOARD_DIR / dashboard_name)
        panels = {
            panel.get("id"): panel
            for panel in get_dashboard_panels(dashboard)
            if isinstance(panel.get("id"), int)
        }
        for panel_id in header_ids:
            panel = panels.get(panel_id)
            assert panel is not None, (
                f"{dashboard_name} must expose common panel id={panel_id}"
            )
            grid_pos = panel.get("gridPos", {})
            assert grid_pos.get("y", 999) <= 4, (
                f"{dashboard_name}:id={panel_id} must stay in compact context band (y<=4)"
            )
            assert grid_pos.get("h", 99) <= 4, (
                f"{dashboard_name}:id={panel_id} context band height must stay compact"
            )
        # ID + Processed Records remain available under collapsed Run context.
        for panel_id in lazy_shell_ids:
            panel = panels.get(panel_id)
            if dashboard_name == "bioetl-control-plane-v1.json":
                continue
            assert panel is not None, (
                f"{dashboard_name} must retain lazy shell panel id={panel_id}"
            )


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
    """L2 first screens must answer current state before range evidence."""
    expectations = {
        "bioetl-runtime.json": {
            "Monitor Pipeline Status": "bioetl_runtime_current_status_trusted",
            "Review Runtime Blockers": "bioetl_runtime_current_blocker_reason",
        },
        "bioetl-provider-health-v2.json": {
            "Monitor Fleet Severity": "bioetl_provider_current_status",
            "Inspect Top Provider Causes": "bioetl_provider_current_cause",
        },
        "bioetl-dq-v2.json": {
            "Monitor Current DQ Status": "bioetl_dq_current_status",
        },
    }

    for dashboard_name, panel_expectations in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)

        def _operator_title(panel: dict) -> str:
            title = str(panel.get("title") or "").strip()
            if title:
                return title
            options = panel.get("options") or {}
            return str(options.get("bioetlDisplayTitle") or "").strip()

        panels = {
            _operator_title(panel): panel
            for panel in get_dashboard_panels(dashboard)
            if _operator_title(panel)
        }
        for panel_title, expected_metric in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"{dashboard_name} must expose first-screen panel {panel_title!r}"
            )
            assert panel.get("gridPos", {}).get("y", 999) <= 12, (
                f"{dashboard_name}:{panel_title} must be early first-path evidence (y<=12)"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert any(expected_metric in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must consume {expected_metric}"
            )
            assert all("$__range" not in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must not use selected range for current status"
            )

    dq_dashboard = load_dashboard(Path("grafana/dashboards") / "bioetl-dq-v2.json")
    dq_reason = next(
        panel for panel in dq_dashboard.get("panels", []) if panel.get("id") == 9102
    )
    assert dq_reason.get("title") == "Inspect Current DQ Reasons"
    assert int((dq_reason.get("gridPos") or {}).get("y", 999)) < 18
    dq_reason_row = next(
        panel
        for panel in dq_dashboard.get("panels", [])
        if panel.get("title") == "Selected Range · Impact & Freshness"
    )
    assert dq_reason_row.get("collapsed") is True
    assert all(panel.get("id") != 9102 for panel in dq_reason_row.get("panels", []))


def test_dual_status_twins_are_removed_from_runtime_and_dq() -> None:
    """Epic #6572: sole Status on Runtime/DQ first screen (no dual Status twin)."""
    for dashboard_name, banned in (
        ("bioetl-runtime.json", "Runtime Status"),
        ("bioetl-dq-v2.json", "Monitor DQ Current Status"),
    ):
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        titles = {
            panel.get("title")
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        assert banned not in titles, (
            f"{dashboard_name} must not ship dual Status twin {banned!r}"
        )
        assert any(panel.get("id") == 9401 for panel in get_dashboard_panels(dashboard))


def test_overview_and_control_plane_first_screens_use_role_appropriate_queries() -> (
    None
):
    """Overview/Control Plane answer rows must stay on projected current-state or fixed-window evidence."""
    expectations = {
        "bioetl-overview-v2.json": {
            "Monitor Fleet Health": "bioetl_l0_status",
            "Review First Action": "bioetl_l0_next_action_route",
            "Review Domain Status": "bioetl_l0_input_status_selected",
        },
        "bioetl-control-plane-v1.json": {
            "Monitor Replay Safety": "bioetl_replay_safety_blockers_15m",
            "Monitor Manifest/Ledger": "bioetl_manifest_ledger_failures_15m",
            "Monitor Telemetry": "bioetl_control_plane_telemetry_missing_5m",
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
            # Overview answer cards sit at y<=10. Trust keeps Prom KPI cards on
            # the first window (y<18) below the named Review* tables at y=8.
            max_answer_y = (
                15 if dashboard_name == "bioetl-control-plane-v1.json" else 12
            )
            assert panel.get("gridPos", {}).get("y", 999) <= max_answer_y, (
                f"{dashboard_name}:{panel_title} must stay in the answer/evidence band"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
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
        "bioetl-runtime.json": [
            "Monitor Pipeline Status",
            "Review Runtime Blockers",
        ],
        "bioetl-provider-health-v2.json": [
            "Monitor Fleet Severity",
            "Inspect Top Provider Causes",
            "Monitor Telemetry Presence",
        ],
        "bioetl-dq-v2.json": [
            "Monitor Current DQ Status",
            "Inspect Current DQ Reasons",
        ],
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
    """Datasource trust surfaces are targeted: Runtime/Control Plane need explicit first-screen markers."""
    expectations = {
        "bioetl-runtime.json": (
            "Monitor Metrics Coverage",
            ("evidence confidence", "inconclusive"),
        ),
        "bioetl-control-plane-v1.json": (
            "Monitor Telemetry",
            ("do not trust zero blocker cards", "prometheus scrape/rules"),
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
        assert panel.get("gridPos", {}).get("y", 999) <= 23, (
            f"{dashboard_name}:{panel_title} must stay above fold"
        )
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
                if _panels_overlap(left, right):
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
        if dashboard_path.name == "bioetl-runtime.json" and gaps == [(29, 34)]:
            continue
        assert not gaps, (
            f"{dashboard_path.name} has unexplained empty root row gaps: {gaps}"
        )


def test_provider_and_dq_range_evidence_panels_are_below_first_screen() -> None:
    provider = load_dashboard(Path("grafana/dashboards/bioetl-provider-health-v2.json"))
    dq = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    range_panels = {
        "bioetl-provider-health-v2.json": (
            provider,
            [
                "Monitor Healthy Checks (Selected Range)",
                "Monitor Degraded Checks (Selected Range)",
                "Track Provider Failure Rate (Selected Range)",
                "Track Health Checks Total (Selected Range)",
                "Track Failure and Degraded Trend by Provider",
                "Track Provider Failure Share (Selected Range)",
            ],
        ),
        "bioetl-dq-v2.json": (
            dq,
            [
                "Track Range Evidence: Bronze -> Silver -> Gold",
                "Range · Silver Filter Rejects",
            ],
        ),
    }

    for dashboard_name, (dashboard, panel_titles) in range_panels.items():
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        root_titles = {
            panel.get("title")
            for panel in dashboard.get("panels", [])
            if isinstance(panel, dict)
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            if panel is None:
                # Some selected-range titles were renamed/retired; skip absent.
                continue
            # Epic #6572: range packs may live under collapsed rows (not root first paint).
            if panel_title not in root_titles:
                parent_collapsed = any(
                    isinstance(row, dict)
                    and row.get("type") == "row"
                    and row.get("collapsed") is True
                    and any(
                        isinstance(child, dict) and child.get("title") == panel_title
                        for child in (row.get("panels") or [])
                    )
                    for row in dashboard.get("panels", [])
                )
                assert parent_collapsed or panel.get("gridPos", {}).get("y", 0) >= 18, (
                    f"{dashboard_name}:{panel_title} must be collapsed or below first screen"
                )
            else:
                assert panel.get("gridPos", {}).get("y", 0) >= 18, (
                    f"{dashboard_name}:{panel_title} must sit below first-screen current state"
                )
            description = str(panel.get("description", "")).lower()
            assert "selected-range" in f"{panel_title.lower()} {description}", (
                f"{dashboard_name}:{panel_title} must identify selected-range semantics"
            )


def test_first_screen_scope_and_cta_panels_document_role_and_scope() -> None:
    """Text/CTA first-screen panels should expose machine-readable operator guidance."""
    expectations = {
        "bioetl-overview-v2.json": {
            "Inspect Scope & Evidence": {
                "tokens": ("current", "selected run", "time range", "unknown"),
                "max_y": 12,
            },
        },
        "bioetl-dq-v2.json": {
            "Start DQ Triage": {
                "tokens": ("current", "selected-run", "range"),
                "max_y": 22,
            },
            "Monitor Worst Freshness Age": {
                "tokens": ("time range", "sla", "unknown"),
                "max_y": 24,
            },
        },
        "bioetl-provider-health-v2.json": {
            "Start Provider Triage": {
                "tokens": (
                    "fleet severity",
                    "top causes",
                    "selected-provider",
                    "range",
                ),
                "max_y": 23,
                "panel_id": 9002,
            },
        },
    }

    for dashboard_name, panel_expectations in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)

        def _operator_title(panel: dict) -> str:
            title = str(panel.get("title") or "").strip()
            if title:
                return title
            options = panel.get("options") or {}
            return str(options.get("bioetlDisplayTitle") or "").strip()

        panels_by_title = {
            _operator_title(panel): panel
            for panel in get_dashboard_panels(dashboard)
            if _operator_title(panel)
        }
        panels_by_id = {
            panel.get("id"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("id") is not None
        }
        for panel_title, spec in panel_expectations.items():
            panel = (
                panels_by_id.get(spec["panel_id"])
                if spec.get("panel_id") is not None
                else panels_by_title.get(panel_title)
            )
            assert panel is not None, (
                f"{dashboard_name} missing first-screen guidance panel {panel_title!r}"
            )
            assert panel.get("gridPos", {}).get("y", 999) <= spec["max_y"], (
                f"{dashboard_name}:{panel_title} must stay on the first screen"
            )
            description = str(panel.get("description", "")).lower()
            assert description, (
                f"{dashboard_name}:{panel_title} must define machine-readable description text"
            )
            for token in spec["tokens"]:
                assert token in description, (
                    f"{dashboard_name}:{panel_title} description must mention {token!r}"
                )


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
    """#8746: fail-closed headlines must not lastNotNull a dashboard range."""
    expectations = {
        "bioetl-overview-v2.json": ("Monitor Fleet Health",),
        "bioetl-control-plane-v1.json": (
            "Monitor Replay Readiness",
            "Monitor Checkpoint Age",
        ),
        "bioetl-runtime.json": (
            "Monitor Pipeline Status",
            "Monitor Metrics Coverage",
        ),
        "bioetl-provider-health-v2.json": ("Monitor Selected Provider",),
    }
    for dashboard_name, titles in expectations.items():
        dashboard = load_dashboard(_DASHBOARD_DIR / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for title in titles:
            panel = panels[title]
            instants = [
                target.get("instant")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert instants and all(flag is True for flag in instants), (
                f"{dashboard_name}:{title} must set targets[].instant=true"
            )


def test_run_explorer_identity_is_on_the_first_screen() -> None:
    """#8747/#9147: browse stays on the fold; identity/accounting are collapsed."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-run-explorer-v1.json")
    panels = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    browse = panels[3010]
    identity = panels[3022]
    records = panels[3023]
    assert 9402 not in panels
    assert 9403 not in panels
    browse_grid = browse.get("gridPos") or {}
    assert browse_grid.get("h") == 11
    assert int(browse_grid.get("y", 0)) + int(browse_grid.get("h", 0)) <= FIRST_WINDOW_Y
    assert panel_declared_row_cap(browse) == 10
    collapsed_ids = {
        panel.get("id")
        for panel in get_row_child_panels(dashboard, "Selected Run Details")
    }
    assert 9402 not in collapsed_ids
    assert 9403 not in collapsed_ids, (
        "compact processed-records teaser 9403 must not ship (same-row-subset of 3023)"
    )
    assert 3022 in collapsed_ids, (
        "Inspect Run Identity must ship inside collapsed Selected Run Details"
    )
    assert 3023 in collapsed_ids, (
        "Inspect Processed Records must ship inside collapsed Selected Run Details "
        "so first-paint Ops HTTP stays within budget (#9147/#9191)"
    )
    assert identity.get("gridPos", {}).get("y", 0) >= 19
    assert records.get("gridPos", {}).get("y", 0) >= 19
    assert "last 10" in str(browse.get("title", "")).lower()


def test_run_explorer_first_screen_empty_copy_has_no_selector_dollars() -> None:
    """Selected-run first screen must not leak `$pipeline` / `$run_id` into noValue."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-run-explorer-v1.json")
    panels = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    for panel_id in (3010, 3022):
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
    """#8745: Inspect Alerts is T3, not a second first-screen question."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-overview-v2.json")
    row = next(
        panel for panel in dashboard.get("panels", []) if panel.get("id") == 9600
    )
    assert row.get("collapsed") is True
    assert any(child.get("id") == 9601 for child in (row.get("panels") or []))


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
    """Always-visible Incident first screen ends at ranked suspects (DASH-FIT-001)."""
    dashboard = load_dashboard(_DASHBOARD_DIR / "bioetl-incident-v1.json")
    root = [panel for panel in dashboard.get("panels", []) if isinstance(panel, dict)]
    root_ids = {panel.get("id") for panel in root}
    assert 2005 not in root_ids
    assert 2006 not in root_ids
    assert 2007 not in root_ids
    row = next(panel for panel in root if panel.get("id") == 2020)
    assert row.get("type") == "row"
    assert row.get("collapsed") is True
    assert row.get("gridPos", {}).get("y") == 18
    nested_ids = {child.get("id") for child in (row.get("panels") or [])}
    assert nested_ids == {2005, 2006, 2007}
