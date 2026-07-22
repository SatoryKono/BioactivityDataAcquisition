"""First-screen Grafana dashboard contracts for operator triage dashboards."""

from pathlib import Path

import pytest
import yaml

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
        spans.append((y, y + h - 1))

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
        "Provider Health MAY use `$__range` for sparse provider-current telemetry",
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
    """Primary dashboards must expose the shared context shell before domain details."""
    expected = {
        "Provenance": {"id": 9400, "x": 0, "y": 3, "w": 16, "h": 4},
        "Status": {"id": 9401, "x": 16, "y": 3, "w": 8, "h": 4},
        "ID": {"id": 9402, "x": 0, "y": 7, "w": 10},
        "Processed Records": {"id": 9403, "x": 10, "y": 7, "w": 6},
    }
    dashboard_names = {
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-workflow-overview.json",
    }

    for dashboard_name in dashboard_names:
        dashboard = load_dashboard(_DASHBOARD_DIR / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for title, placement in expected.items():
            panel = panels.get(title)
            assert panel is not None, (
                f"{dashboard_name} must expose common panel {title!r}"
            )
            assert panel.get("id") == placement["id"]
            grid_pos = panel.get("gridPos", {})
            for key in ("x", "y", "w"):
                assert grid_pos.get(key) == placement[key], (
                    f"{dashboard_name}:{title} must keep common {key} placement"
                )
            if title in {"ID", "Processed Records"}:
                assert grid_pos.get("h") in {6, 10}, (
                    f"{dashboard_name}:{title} must keep reviewed header height"
                )
            else:
                assert grid_pos.get("h") == placement["h"], (
                    f"{dashboard_name}:{title} must keep common h placement"
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
            "Runtime Status": "bioetl_runtime_current_status_trusted",
            "Runtime Blockers": "bioetl_runtime_current_blocker_reason",
        },
        "bioetl-provider-health-v2.json": {
            "Monitor GLOBAL Provider Severity Matrix": "bioetl_provider_current_status",
            "Inspect Provider Top Causes": "bioetl_provider_current_cause",
        },
        "bioetl-dq-v2.json": {
            "Monitor DQ Current Status": "bioetl_dq_current_status",
            "Inspect DQ Current Reasons": "bioetl_dq_current_reason",
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
            assert panel.get("gridPos", {}).get("y", 999) <= 20, (
                f"{dashboard_name}:{panel_title} must be visible before range evidence"
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


def test_expanded_current_status_panels_are_documented_as_mirrors() -> None:
    """Expanded first-screen status panels must not look like independent verdicts."""
    expectations = {
        "bioetl-runtime.json": ("Status", "Runtime Status"),
        "bioetl-dq-v2.json": ("Status", "Monitor DQ Current Status"),
    }

    for dashboard_name, (compact_title, expanded_title) in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        compact_description = str(panels[compact_title].get("description", "")).lower()
        expanded_description = str(
            panels[expanded_title].get("description", "")
        ).lower()

        assert "expanded first-screen mirror" in compact_description
        assert "expanded mirror" in expanded_description
        assert "not an independent second" in expanded_description


def test_overview_and_control_plane_first_screens_use_role_appropriate_queries() -> (
    None
):
    """Overview/Control Plane answer rows must stay on projected current-state or fixed-window evidence."""
    expectations = {
        "bioetl-overview-v2.json": {
            "Status": "bioetl_l0_status",
            "First Action": "bioetl_l0_next_action_route",
            "Inputs": "bioetl_l0_input_status_selected",
        },
        "bioetl-control-plane-v1.json": {
            "Monitor: Replay Safety State": "bioetl_replay_safety_blockers_15m",
            "Monitor: Manifest / Ledger Integrity": "bioetl_manifest_ledger_failures_15m",
            "Inspect: Telemetry Missing": "bioetl_control_plane_telemetry_missing_5m",
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
            max_answer_y = 26 if dashboard_name == "bioetl-overview-v2.json" else 21
            assert panel.get("gridPos", {}).get("y", 999) <= max_answer_y, (
                f"{dashboard_name}:{panel_title} must stay in the answer row"
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
            "Runtime Status",
            "Runtime Blockers",
        ],
        "bioetl-provider-health-v2.json": [
            "Monitor GLOBAL Provider Severity Matrix",
            "Inspect Provider Top Causes",
            "Monitor Provider Telemetry Freshness",
        ],
        "bioetl-dq-v2.json": [
            "Monitor DQ Current Status",
            "Inspect DQ Current Reasons",
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
            "Runtime Telemetry Gap",
            ("treat zero count panels as inconclusive", "prometheus targets"),
        ),
        "bioetl-control-plane-v1.json": (
            "Inspect: Telemetry Missing",
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
                "Track: Silver Filter Rejects in Range",
            ],
        ),
    }

    for dashboard_name, (dashboard, panel_titles) in range_panels.items():
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, f"{dashboard_name} missing {panel_title!r}"
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
            "Provenance": {
                "tokens": ("primary question", "scope", "provenance"),
                "max_y": 12,
            },
        },
        "bioetl-dq-v2.json": {
            "Review: First Action": {
                "tokens": ("crit", "warn", "selected-range"),
                "max_y": 22,
            },
            "Time Range · Worst Freshness Age (hours; SLA 24/72)": {
                "tokens": ("time range", "sla", "unknown"),
                "max_y": 24,
            },
        },
        "bioetl-provider-health-v2.json": {
            "First Action": {
                "tokens": ("current", "top causes", "selected-range"),
                "max_y": 23,
            },
        },
    }

    for dashboard_name, panel_expectations in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, spec in panel_expectations.items():
            panel = panels.get(panel_title)
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
            str(link.get("title", "")) == "Explore Traces"
            for link in navigation_links
        )
        panel = next(
            (
                candidate
                for candidate in get_dashboard_panels(dashboard)
                if candidate.get("id") == 1000
                and candidate.get("title")
                in {"Review Dashboard Navigation", "Navigation"}
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
        for token in required_tokens:
            assert token in description, (
                f"{dashboard_path.name}:navigation panel description "
                f"must mention {token!r}"
            )
        if has_explore_traces:
            assert any(token in description for token in tracing_tokens), (
                f"{dashboard_path.name}:navigation panel description "
                "must document traced-run-only Explore Traces semantics"
            )
