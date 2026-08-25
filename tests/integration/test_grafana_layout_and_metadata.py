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
"""Grafana dashboard layout and metadata integration contracts."""

from pathlib import Path
import re

import pytest
import yaml
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    get_row_child_panels,
    index_panels_by_base_title,
    load_dashboard,
    panel_display_title,
)

pytestmark = pytest.mark.integration

NAVIGATION_CONTRACT_PATH = Path(
    "docs/03-guides/dashboards/contracts/navigation-links.yaml"
)


def _load_navigation_contract() -> dict:
    payload = yaml.safe_load(NAVIGATION_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), (
        "navigation-links contract must deserialize into a mapping"
    )
    return payload


def _assert_panels_stay_in_grid_without_overlap(
    panels: list[dict], *, context: str
) -> None:
    """Require positive 24-column geometry with no pairwise intersections."""
    overlaps: list[str] = []
    for index, left in enumerate(panels):
        left_grid = left.get("gridPos", {})
        left_x = left_grid.get("x", -1)
        left_y = left_grid.get("y", -1)
        left_w = left_grid.get("w", 0)
        left_h = left_grid.get("h", 0)
        assert left_x >= 0 and left_y >= 0
        assert left_w > 0 and left_h > 0
        assert left_x + left_w <= 24
        for right in panels[index + 1 :]:
            right_grid = right.get("gridPos", {})
            right_x = right_grid.get("x", -1)
            right_y = right_grid.get("y", -1)
            right_w = right_grid.get("w", 0)
            right_h = right_grid.get("h", 0)
            x_overlap = left_x < right_x + right_w and right_x < left_x + left_w
            y_overlap = left_y < right_y + right_h and right_y < left_y + left_h
            if x_overlap and y_overlap:
                overlaps.append(
                    f"{left.get('id')}:{left.get('title')} overlaps "
                    f"{right.get('id')}:{right.get('title')}"
                )
    assert not overlaps, f"{context} panels overlap:\n" + "\n".join(overlaps)


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_dashboard_titles_do_not_expose_fixed_window_suffixes(
    dashboard_path: Path,
) -> None:
    """Shipped dashboards should rely on Grafana window controls, not fixed time suffixes."""
    dashboard = load_dashboard(dashboard_path)
    titles = [
        panel.get("title", "")
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("title"), str)
    ]
    fixed_window_suffix_re = re.compile(
        r"(?:\((24h|30m|15m|1h|5m)\)|/\s*(24h|30m|15m|1h|5m))$"
    )
    allowed_fixed_window_ids = {132, 133, 136}
    offenders = [
        panel.get("title", "")
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("title"), str)
        and fixed_window_suffix_re.search(panel["title"])
        and panel.get("id") not in allowed_fixed_window_ids
    ]
    assert not offenders, (
        f"Dashboard {dashboard_path.name} still contains fixed-window titles: {offenders}"
    )


def test_runtime_top_fold_text_panels_do_not_overlap() -> None:
    """Runtime first-fold text blocks must keep a readable, non-overlapping layout."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    text_panels = [
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("type") == "text" and panel.get("gridPos", {}).get("y", 999) <= 20
    ]

    overlaps = []
    for index, left in enumerate(text_panels):
        left_grid = left.get("gridPos", {})
        left_x = left_grid.get("x", 0)
        left_y = left_grid.get("y", 0)
        left_w = left_grid.get("w", 0)
        left_h = left_grid.get("h", 0)
        for right in text_panels[index + 1 :]:
            right_grid = right.get("gridPos", {})
            right_x = right_grid.get("x", 0)
            right_y = right_grid.get("y", 0)
            right_w = right_grid.get("w", 0)
            right_h = right_grid.get("h", 0)
            x_overlap = left_x < right_x + right_w and right_x < left_x + left_w
            y_overlap = left_y < right_y + right_h and right_y < left_y + left_h
            if x_overlap and y_overlap:
                overlaps.append(
                    f"{left.get('id')}:{left.get('title')} overlaps {right.get('id')}:{right.get('title')}"
                )

    assert not overlaps, "Runtime top-fold text panels overlap:\n" + "\n".join(overlaps)


@pytest.mark.parametrize("dashboard_path", get_dashboard_files(), ids=lambda p: p.name)
def test_root_panels_including_rows_do_not_overlap(dashboard_path: Path) -> None:
    """DASH-LAYOUT-001: root data panels and collapsed row headers must not share cells."""
    dashboard = load_dashboard(dashboard_path)
    _assert_panels_stay_in_grid_without_overlap(
        list(dashboard.get("panels") or []),
        context=f"{dashboard_path.name} root layout",
    )


def test_runtime_detect_row_stays_below_first_window_tables() -> None:
    """#9172: row 252 must sit at or below y=16 and remain collapsed."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    detect_row = next(
        (panel for panel in dashboard.get("panels", []) if panel.get("id") == 252),
        None,
    )
    assert detect_row is not None
    assert detect_row.get("collapsed") is True
    assert int((detect_row.get("gridPos") or {}).get("y", -1)) >= 16
    blockers = next(
        (panel for panel in dashboard.get("panels", []) if panel.get("id") == 9101),
        None,
    )
    coverage = next(
        (panel for panel in dashboard.get("panels", []) if panel.get("id") == 9102),
        None,
    )
    assert blockers is not None and coverage is not None
    _assert_panels_stay_in_grid_without_overlap(
        [blockers, coverage, detect_row],
        context="Runtime first-window tables vs Detect row",
    )


def test_runtime_redundant_guidance_panels_stay_out_of_root_layout() -> None:
    """Runtime detail guidance stays under the collapsed Detect row group."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    detect_row = next(
        (panel for panel in dashboard.get("panels", []) if panel.get("id") == 252),
        None,
    )
    assert detect_row is not None, "Runtime dashboard must keep Detect row"
    assert detect_row.get("collapsed") is True
    detect_panels = get_row_child_panels(dashboard, "Inspect Detection Signals")
    detail_panel = next(
        panel
        for panel in detect_panels
        if panel.get("title") == "Inspect Active Runtime Blocker Detail"
    )
    assert detail_panel.get("gridPos", {}).get("y", 0) > detect_row.get(
        "gridPos", {}
    ).get("y", 0)
    detect_titles = {
        panel.get("title")
        for panel in detect_panels
        if isinstance(panel.get("title"), str)
    }
    assert "Inspect Active Runtime Blocker Detail" in detect_titles
    _assert_panels_stay_in_grid_without_overlap(
        detect_panels, context="Runtime Detect disclosure"
    )


def test_runtime_first_screen_grid_uses_shared_panel_reference_sizes() -> None:
    """Runtime First Action stays on first paint; ID/Processed Records stay below triage."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    root_panels = index_panels_by_base_title(
        [panel for panel in dashboard.get("panels", []) if isinstance(panel, dict)]
    )

    first_action_grid = root_panels["Start Pipeline Triage"]["gridPos"]
    assert first_action_grid["y"] <= 8
    assert first_action_grid["w"] >= 8
    context_row = next(
        panel for panel in dashboard["panels"] if panel.get("id") == 9993
    )
    assert context_row.get("collapsed") is True
    assert context_row["gridPos"]["y"] > first_action_grid["y"]
    context_titles = {
        panel_display_title(panel)
        for panel in get_row_child_panels(dashboard, "Inspect Run Context")
    }
    assert {"Inspect Pipeline Identity", "Inspect Processed Records"}.issubset(
        context_titles
    )


def test_runtime_telemetry_gap_panel_keeps_readable_first_screen_width() -> None:
    """Runtime trust marker stays on first paint; failed-run KPI stays secondary."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    root = {
        panel.get("title"): panel
        for panel in dashboard.get("panels", [])
        if isinstance(panel.get("title"), str)
    }

    panel = root["Monitor Metrics Coverage"]
    grid = panel.get("gridPos", {})
    assert grid["y"] <= 23
    assert grid["w"] >= 4, (
        "Monitor Metrics Coverage must reserve readable width on the first screen"
    )
    secondary_row = next(
        panel for panel in dashboard["panels"] if panel.get("id") == 9992
    )
    assert secondary_row.get("collapsed") is True
    assert secondary_row["gridPos"]["y"] > grid["y"]
    secondary_titles = {
        child.get("title")
        for child in get_row_child_panels(
            dashboard, "Inspect Secondary Runtime Indicators"
        )
    }
    assert "Monitor Failed Runs" in secondary_titles


def test_control_plane_root_layout_keeps_range_evidence_and_rows_non_overlapping() -> (
    None
):
    """Control Plane root layout must not overlap the selected-range blocker panel with diagnostic rows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    root_panels = [
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("id") not in {1000, 890}
    ]

    overlaps = []
    for index, left in enumerate(root_panels):
        left_grid = left.get("gridPos", {})
        left_x = left_grid.get("x", 0)
        left_y = left_grid.get("y", 0)
        left_w = left_grid.get("w", 0)
        left_h = left_grid.get("h", 0)
        for right in root_panels[index + 1 :]:
            right_grid = right.get("gridPos", {})
            right_x = right_grid.get("x", 0)
            right_y = right_grid.get("y", 0)
            right_w = right_grid.get("w", 0)
            right_h = right_grid.get("h", 0)
            x_overlap = left_x < right_x + right_w and right_x < left_x + left_w
            y_overlap = left_y < right_y + right_h and right_y < left_y + left_h
            if x_overlap and y_overlap:
                overlaps.append(
                    f"{left.get('id')}:{left.get('title')} overlaps {right.get('id')}:{right.get('title')}"
                )

    assert not overlaps, "Control Plane root panels overlap:\n" + "\n".join(overlaps)


def test_control_plane_row_sequence_matches_operator_flow() -> None:
    """Collapsed Control Plane diagnostics preserve the operator flow order."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row_panels = [
        panel for panel in dashboard.get("panels", []) if panel.get("type") == "row"
    ]
    row_pairs = [
        (panel.get("id"), panel.get("title"))
        for panel in sorted(
            row_panels, key=lambda panel: panel.get("gridPos", {}).get("y", 0)
        )
    ]
    expected_prefix = [
        (9419, "Review Lineage Validation"),
        (902, "Inspect Replay & Checkpoint Evidence"),
        (901, "Inspect Manifest & Ledger Evidence"),
        (903, "Inspect Global Store Reliability"),
        (904, "Inspect Audit & Lineage Evidence"),
        (905, "Inspect Run Identity Evidence"),
    ]
    assert row_pairs[: len(expected_prefix)] == expected_prefix, (
        f"Control Plane row order/title drifted: {row_pairs}"
    )
    assert any(panel_id == 9412 for panel_id, _ in row_pairs), (
        f"Control Plane must keep collapsed Run context row: {row_pairs}"
    )
    assert all(panel.get("collapsed") is True for panel in row_panels)
    assert all(panel.get("panels") for panel in row_panels)


def test_control_plane_named_review_surfaces_are_findable() -> None:
    """Operator-named Review* surfaces must not hide inside a differently named row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    root = {
        panel.get("id"): panel
        for panel in dashboard.get("panels", [])
        if isinstance(panel, dict)
    }
    trust = root[9418]
    retention = root[9416]
    lineage_row = root[9419]
    assert trust.get("title") == "Review Selected-Run Trust"
    assert retention.get("title") == "Review Retention Compliance"
    assert lineage_row.get("title") == "Review Lineage Validation"
    assert lineage_row.get("type") == "row"
    assert lineage_row.get("collapsed") is True
    assert trust.get("gridPos", {}).get("y", 99) < 18
    assert retention.get("gridPos", {}).get("y", 99) < 18
    assert lineage_row.get("gridPos", {}).get("y") == 18
    child_ids = [child.get("id") for child in lineage_row.get("panels") or []]
    assert 9415 in child_ids
    lineage = next(
        child for child in lineage_row.get("panels") or [] if child.get("id") == 9415
    )
    assert lineage.get("title") == "Review Lineage Validation"
    audit_ids = {
        child.get("id")
        for child in (root[904].get("panels") or [])
        if isinstance(child, dict)
    }
    assert 9415 not in audit_ids
    assert 9416 not in audit_ids
    assert 9418 not in audit_ids


def test_retention_panel_9416_retry_preserves_selected_run_and_time() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(
        item
        for item in dashboard.get("panels", [])
        if isinstance(item, dict) and item.get("id") == 9416
    )
    target = panel["targets"][0]
    assert target.get("parser") == "backend"
    assert target.get("root_selector") == "rows"
    target_url = str(target.get("url", ""))
    assert "error_as_row=1" in target_url
    assert "run_id=${run_id}" in target_url
    links = panel.get("fieldConfig", {}).get("defaults", {}).get("links") or []
    retry = next(
        link
        for link in links
        if isinstance(link, dict) and "Retry" in str(link.get("title", ""))
    )
    retry_url = str(retry.get("url", ""))
    assert "var-run_id=$run_id" in retry_url
    assert "${__url_time_range}" in retry_url
    assert "viewPanel=9416" in retry_url


def test_control_plane_first_evidence_panel_stays_close_to_answer_row() -> None:
    """Selected-range blocker evidence stays close to the replay drilldown row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Track Replay Blockers")
    assert panel is not None
    row_panel = panels["Inspect Replay & Checkpoint Evidence"]
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("y") > row_panel.get("gridPos", {}).get("y", 0)
    assert grid_pos.get("w", 0) == 6
    assert grid_pos.get("h", 0) == 3


def test_control_plane_long_first_screen_titles_keep_extra_width() -> None:
    """Long first-screen title cards must keep enough width to avoid avoidable truncation risk."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel_display_title(panel): panel
        for panel in get_dashboard_panels(dashboard)
        if panel_display_title(panel)
    }

    for panel_title in (
        "Monitor Manifest/Ledger",
        "Monitor Telemetry",
        "Review Recovery Action",
    ):
        panel = panels.get(panel_title)
        assert panel is not None
        grid_pos = panel.get("gridPos", {})
        assert grid_pos.get("w", 0) >= 5, (
            f"{panel_title} needs extra width for stable title/text rendering"
        )


def test_control_plane_trust_panels_follow_reference_widths() -> None:
    """Trust panels should align with the 18/6 scope and readiness columns."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = index_panels_by_base_title(get_dashboard_panels(dashboard))

    scope = panels["Inspect Scope & Evidence"]["gridPos"]
    readiness = panels["Monitor Replay Readiness"]["gridPos"]
    run_summary = panels["Review Run Summary"]["gridPos"]
    processed = panels["Review Processed Records"]["gridPos"]
    telemetry = panels["Monitor Telemetry"]["gridPos"]

    assert run_summary["w"] == scope["w"] == 18
    assert processed["w"] == telemetry["w"] == readiness["w"] == 6
    assert run_summary["x"] == 0
    assert processed["x"] == telemetry["x"] == readiness["x"] == 18

    third_width = scope["w"] // 3
    third_panels = [
        panels["Monitor Replay Safety"]["gridPos"],
        panels["Monitor Checkpoint Age"]["gridPos"],
        panels["Monitor Manifest/Ledger"]["gridPos"],
    ]
    assert [grid["w"] for grid in third_panels] == [third_width] * 3
    assert [grid["x"] for grid in third_panels] == [0, third_width, 2 * third_width]


def test_control_plane_terminal_events_table_has_readable_width() -> None:
    """Terminal event evidence table should keep enough width for practical status visibility."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Review Terminal Run Outcomes")
    assert panel is not None
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("w", 0) >= 12


def test_control_plane_manifest_evidence_top_band_uses_full_row_width() -> None:
    """Manifest evidence must use packed, non-overlapping disclosure bands."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("title") == "Inspect Manifest & Ledger Evidence"
    )
    assert row.get("collapsed") is True
    child_panels = get_row_child_panels(dashboard, "Inspect Manifest & Ledger Evidence")
    panels = {panel.get("title"): panel for panel in child_panels if panel.get("title")}
    terminal = panels["Review Terminal Run Outcomes"]
    terminal_grid = terminal.get("gridPos", {})
    assert terminal_grid.get("h") == 6
    assert terminal_grid.get("w") == 24
    assert terminal_grid.get("x") == 0
    assert terminal_grid.get("y", 0) > row.get("gridPos", {}).get("y", 0)
    failure_panels = [
        panels["Track Manifest Write Failures"],
        panels["Track Ledger Append Failures"],
        panels["Monitor Manifest Failures (30m)"],
        panels["Monitor Ledger Failures (30m)"],
    ]
    assert {panel.get("gridPos", {}).get("w") for panel in failure_panels} == {6}
    assert {panel.get("gridPos", {}).get("h") for panel in failure_panels} == {3}
    assert {panel.get("gridPos", {}).get("y") for panel in failure_panels} == {
        terminal_grid["y"] + terminal_grid["h"]
    }
    assert {panel.get("gridPos", {}).get("x") for panel in failure_panels} == {
        0,
        6,
        12,
        18,
    }
    _assert_panels_stay_in_grid_without_overlap(
        child_panels, context="Control Plane manifest/ledger disclosure"
    )


def test_control_plane_replay_safety_detail_top_bands_use_full_row_width() -> None:
    """Replay-safety disclosure must pack evidence into non-overlapping bands."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row_panel = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("type") == "row"
        and panel.get("title") == "Inspect Replay & Checkpoint Evidence"
    )
    assert row_panel.get("collapsed") is True
    child_panels = get_row_child_panels(
        dashboard, "Inspect Replay & Checkpoint Evidence"
    )
    panels = {panel.get("id"): panel for panel in child_panels}

    known_blind_spots = panels[894]
    blind_spots_grid = known_blind_spots.get("gridPos", {})
    assert blind_spots_grid.get("x") == 0
    assert blind_spots_grid.get("w") == 24
    row_y = row_panel.get("gridPos", {}).get("y", 0)
    assert blind_spots_grid.get("y") == row_y + 1

    blocker_grid = panels[130].get("gridPos", {})
    assert blocker_grid.get("x") == 0
    assert blocker_grid.get("w") == 6
    assert blocker_grid.get("h") == 3
    assert blocker_grid.get("y") == blind_spots_grid.get("y") + blind_spots_grid.get(
        "h"
    )
    first_band = [panels[panel_id] for panel_id in (130, 3, 104, 120)]
    assert {panel.get("gridPos", {}).get("y") for panel in first_band} == {
        blocker_grid["y"]
    }
    assert {panel.get("gridPos", {}).get("w") for panel in first_band} == {6}
    assert {panel.get("gridPos", {}).get("h") for panel in first_band} == {3}
    second_band = [panels[panel_id] for panel_id in (101, 102, 103, 121)]
    assert {panel.get("gridPos", {}).get("y") for panel in second_band} == {
        blocker_grid["y"] + blocker_grid["h"]
    }
    _assert_panels_stay_in_grid_without_overlap(
        child_panels, context="Control Plane replay-safety disclosure"
    )


def test_control_plane_lineage_top_band_uses_full_row_width() -> None:
    """Audit/lineage top singleton should fill the row instead of leaving avoidable dead space."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row_panel = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("type") == "row"
        and panel.get("title") == "Inspect Audit & Lineage Evidence"
    )
    panels = {
        panel.get("id"): panel
        for panel in get_row_child_panels(dashboard, "Inspect Audit & Lineage Evidence")
    }
    panel = panels[122]
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("x") == 0
    assert grid_pos.get("y", 0) > row_panel.get("gridPos", {}).get("y", 0)
    assert grid_pos.get("w") == 6
    assert grid_pos.get("h") == 3


def test_overview_current_panels_stay_out_of_selected_range_semantics() -> None:
    """Overview L0/L1 current-answer panels must not use $__range windows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for panel_title in (
        "Monitor Fleet Health",
        "Review First Action",
        "Review Domain Status",
        "Review Runtime Status",
        "Review Data Quality Status",
        "Review Data Validation Status",
        "Review Control Plane Status",
        "Review Global Provider Status",
        "Review Workflow Status",
    ):
        panel = panels.get(panel_title)
        assert panel is not None
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert "$__range" not in expr


def test_runtime_alert_condition_breakdown_panels_exist() -> None:
    """Runtime must expose localization panels in addition to summary cards."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected = {
        "Track Stage Backlog Trend": "bioetl_stage_backlog_records",
        "Review Errors by Stage & Code": "bioetl_errors_total",
        "Compare Records by Stage & Run Type": "bioetl_records_processed_total",
        "Track Phase Duration": "bioetl_phase_duration_seconds_bucket",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    for panel_title, required_metric in expected.items():
        panel = panels.get(panel_title)
        assert panel is not None, f"Runtime dashboard missing {panel_title!r}"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert required_metric in expr


@pytest.mark.parametrize("dashboard_file", ["bioetl-control-plane-v1.json"])
def test_replay_panels_are_split_by_semantics(dashboard_file: str) -> None:
    """Control-plane replay diagnostics must keep reconstructability, drift, and lag separate."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    reconstruct = panels.get("Track Unreconstructable Replays")
    assert reconstruct is not None
    reconstruct_expr = "\n".join(
        target.get("expr", "")
        for target in reconstruct.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_reconstructability_events_total" in reconstruct_expr
    assert "bioetl_replay_drift_events_total" not in reconstruct_expr
    assert "bioetl_replay_lag_seconds" not in reconstruct_expr

    drift = panels.get("Replay Drift Events")
    if dashboard_file == "bioetl-control-plane-v1.json":
        drift = panels.get("Track Replay Drift")
    assert drift is not None
    drift_expr = "\n".join(
        target.get("expr", "")
        for target in drift.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_drift_events_total" in drift_expr

    lag = panels.get("Track Peak Replay Lag")
    assert lag is not None
    lag_expr = "\n".join(
        target.get("expr", "")
        for target in lag.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_lag_seconds" in lag_expr
    assert lag.get("fieldConfig", {}).get("defaults", {}).get("unit") == "s"


def test_control_plane_trust_panels_preserve_missing_telemetry() -> None:
    """Control-plane trust-state panels must not mask missing telemetry as zero."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor Replay Safety",
        "Monitor Manifest/Ledger",
    ):
        panel = panels.get(title)
        assert panel is not None
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert "or vector(0)" not in expr
        assert panel.get("fieldConfig", {}).get("defaults", {}).get("noValue") == (
            "UNKNOWN"
        )
        assert panel.get("options", {}).get("colorMode") == "background"

        value_mapping = next(
            (
                mapping
                for mapping in panel.get("fieldConfig", {})
                .get("defaults", {})
                .get("mappings", [])
                if mapping.get("type") == "value"
            ),
            None,
        )
        assert value_mapping is not None
        assert value_mapping.get("options") == {
            "0": {"text": "OK", "color": "green"},
            "1": {"text": "WARN", "color": "orange"},
            "2": {"text": "CRIT", "color": "red"},
        }


def test_control_plane_run_type_noop_panels_disclose_scope_limit() -> None:
    """Panels backed by metric families without run_type must disclose that the selector is a no-op."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    expected_titles = (
        "Track Checkpoint Incompatibilities",
        "Track Unreconstructable Replays",
        "Track Checkpoint Load Failures",
        "Track Checkpoint Save Failures",
        "Compare Checkpoint Outcomes",
        "Track Checkpoint Save Latency",
        "Track Ledger Append Failures",
        "Compare Ledger Appends by Type & Status",
        "Monitor Ledger Failures (30m)",
        "Track Missing Lineage References",
        "Track Lineage Persistence Failures",
        "Review Missing Lineage by Layer",
        "Compare Lineage Persistence Outcomes",
    )
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in expected_titles:
        panel = panels.get(title)
        assert panel is not None, f"Control Plane missing {title!r}"
        description = str(panel.get("description", ""))
        assert "Run Type does not affect this panel." in description, (
            f"Control Plane panel {title!r} must disclose that run_type is a no-op"
        )


def test_control_plane_exposes_terminal_events_and_telemetry_gap() -> None:
    """Control-plane must expose terminal ledger evidence and missing telemetry risk."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expected = {
        "Monitor Telemetry": ("bioetl_control_plane_telemetry_missing_5m",),
        "Review Terminal Run Outcomes": ("bioetl_control_plane_terminal_events_total",),
    }
    for title, tokens in expected.items():
        panel = panels.get(title)
        assert panel is not None, f"Control Plane dashboard missing {title!r}"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        for token in tokens:
            assert token in expr

    telemetry = panels["Monitor Telemetry"]
    assert telemetry.get("fieldConfig", {}).get("defaults", {}).get("noValue") == (
        "UNKNOWN"
    )


def test_control_plane_bounded_failure_rows_preserve_unknown_evidence() -> None:
    """Bounded failure rows must expose status/reason instead of healthy-looking zeros."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(
        panel for panel in get_dashboard_panels(dashboard) if panel.get("id") == 9417
    )

    assert panel.get("type") == "table"
    assert panel.get("options", {}).get("showHeader") is True
    target = panel.get("targets", [])[0]
    assert target.get("root_selector") == "rows"
    assert target.get("url", "").startswith("/ops/control-plane/failure-reasons?")

    description = str(panel.get("description", "")).lower()
    assert (
        "every category row carries bounded status and reason evidence" in description
    )
    assert "unknown backend verdict must remain visible" in description
    assert "must not look like a healthy zero" in description

    visible_columns = {
        override.get("matcher", {}).get("options")
        for override in panel.get("fieldConfig", {}).get("overrides", [])
    }
    assert {"count", "status", "reason"}.issubset(visible_columns)
    count_override = next(
        override
        for override in panel.get("fieldConfig", {}).get("overrides", [])
        if override.get("matcher", {}).get("options") == "count"
    )
    count_properties = {
        property_.get("id"): property_.get("value")
        for property_ in count_override.get("properties", [])
    }
    assert count_properties.get("noValue") == "UNKNOWN"
    no_value = str(
        panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
    ).lower()
    assert "backend unavailable must not be treated as zero failures" in no_value


def test_control_plane_first_screen_normalizes_workflow_pipeline_aliases() -> None:
    """Trust first-screen cards use thin pipeline selectors (#6574; no mega-expr glue)."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor Replay Safety",
        "Monitor Manifest/Ledger",
        "Monitor Telemetry",
    ):
        panel = panels.get(title)
        assert panel is not None, f"Control Plane dashboard missing {title!r}"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert 'pipeline=~"$pipeline"' in expr, (
            f"{title!r} must scope current-state metrics by pipeline selector"
        )
        assert len(expr) <= 200, f"{title!r} first-screen expr must stay <=200 chars"
        assert "$__range" not in expr


def test_control_plane_failure_ratio_thresholds_match_descriptions() -> None:
    """Manifest/ledger ratio panels should project >10% into CRIT severity."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor Manifest Failures (30m)",
        "Monitor Ledger Failures (30m)",
        "Monitor Global Read Failures (30m)",
    ):
        panel = panels.get(title)
        assert panel is not None
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        if title == "Monitor Global Read Failures (30m)":
            assert "> bool 0.05" in expr
            assert "> bool 0.10" in expr
        elif title == "Monitor Manifest Failures (30m)":
            assert "bioetl_control_plane_manifest_fail_severity_30m" in expr
            assert "> bool 0.1" not in expr
        else:
            assert "bioetl_control_plane_ledger_fail_severity_30m" in expr
            assert "> bool 0.1" not in expr
        steps = (
            panel.get("fieldConfig", {})
            .get("defaults", {})
            .get("thresholds", {})
            .get("steps", [])
        )
        assert steps == [
            {"color": "green", "value": None},
            {"color": "orange", "value": 1},
            {"color": "red", "value": 2},
        ]


def test_dashboard_default_time_and_refresh_policy_by_uid_class() -> None:
    """Shipped dashboards must keep canonical time.from/refresh policy by UID class."""
    contract = _load_navigation_contract()
    policy = contract.get("default_time_refresh_policy", {})
    exceptions = contract.get("default_time_refresh_policy_exceptions", {})

    assert isinstance(policy, dict), "default_time_refresh_policy must be defined"
    assert isinstance(exceptions, dict), (
        "default_time_refresh_policy_exceptions must be a mapping"
    )

    l0_uids = policy.get("L0", {}).get("dashboards", [])
    l1_uids = policy.get("L1", {}).get("dashboards", [])
    l2_uids = policy.get("L2", {}).get("dashboards", [])

    assert (
        isinstance(l0_uids, list)
        and isinstance(l1_uids, list)
        and isinstance(l2_uids, list)
    )

    baseline = {"time_from": "now-12h", "refresh": "60s"}
    explorer_baseline = {"time_from": "now-24h", "refresh": "1m"}

    for uid in [*l0_uids, *l1_uids]:
        expected = exceptions.get(uid, baseline)
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{uid}.json")
        assert dashboard.get("uid") == uid, f"Dashboard UID mismatch for {uid}.json"

        time_cfg = dashboard.get("time", {})
        assert isinstance(time_cfg, dict), f"{uid} time config must be an object"
        assert time_cfg.get("from") == expected["time_from"], (
            f"{uid} must keep time.from={expected['time_from']!r}, got {time_cfg.get('from')!r}"
        )
        assert dashboard.get("refresh") == expected["refresh"], (
            f"{uid} must keep refresh={expected['refresh']!r}, got {dashboard.get('refresh')!r}"
        )

    for uid in l2_uids:
        expected = exceptions.get(uid, explorer_baseline)
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{uid}.json")
        assert dashboard.get("uid") == uid, f"Dashboard UID mismatch for {uid}.json"

        time_cfg = dashboard.get("time", {})
        assert isinstance(time_cfg, dict), f"{uid} time config must be an object"
        assert time_cfg.get("from") == expected["time_from"], (
            f"{uid} must keep time.from={expected['time_from']!r}, got {time_cfg.get('from')!r}"
        )
        assert dashboard.get("refresh") == expected["refresh"], (
            f"{uid} must keep refresh={expected['refresh']!r}, got {dashboard.get('refresh')!r}"
        )


def test_provider_health_selected_provider_detail_row_is_collapsed() -> None:
    """Provider detail telemetry ships under progressive disclosure."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panels = get_dashboard_panels(dashboard)
    detail_row = next(
        (
            panel
            for panel in panels
            if panel.get("type") == "row"
            and panel.get("title") == "Selected Provider Details"
        ),
        None,
    )
    assert detail_row is not None
    assert detail_row.get("collapsed") is True

    child_panels = get_row_child_panels(dashboard, "Selected Provider Details")
    child_titles = {
        panel.get("title")
        for panel in child_panels
        if isinstance(panel.get("title"), str)
    }
    assert "Inspect Health-Check Latency p95" in child_titles
    assert detail_row.get("gridPos", {}).get("y", 0) < min(
        int(panel.get("gridPos", {}).get("y", 0)) for panel in child_panels
    )


def test_short_table_panels_use_compact_cell_height() -> None:
    """Short tables (gridPos.h ≤ 6) must use cellHeight=sm to avoid internal scroll.

    Issue #8530 / UX cycle 2026-08-10: layout contracts pin many gridPos values, so
    density is achieved via table cell height rather than growing panel height.
    """
    short_tables: list[tuple[str, int | str, str, int]] = []
    violations: list[str] = []

    for dashboard_path in sorted(Path("grafana/dashboards").glob("*.json")):
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "table":
                continue
            height = panel.get("gridPos", {}).get("h")
            if not isinstance(height, int) or height > 6:
                continue
            panel_id = panel.get("id", "?")
            title = panel.get("title") or f"id={panel_id}"
            short_tables.append((dashboard_path.name, panel_id, str(title), height))
            cell_height = panel.get("options", {}).get("cellHeight")
            if cell_height != "sm":
                violations.append(
                    f"{dashboard_path.name} panel {panel_id} ({title!r}) "
                    f"h={height} cellHeight={cell_height!r}"
                )

    assert short_tables, "expected at least one short table panel in shipped dashboards"
    assert not violations, (
        "short tables (h≤6) must set options.cellHeight='sm':\n" + "\n".join(violations)
    )


UNIFORM_TABLE_CELL_HEIGHT = "sm"


def test_all_table_panels_use_uniform_cell_height() -> None:
    """Every shipped table panel uses the same Grafana row-height contract.

    Mixed or omitted ``cellHeight`` presets make rows differ across boards.
    FIT-004 already requires ``sm`` on short tables; this lock extends that
    preset to every table. Table-default ``wrapText=True`` still grows some
    rows, so defaults must not wrap; long fields wrap on named columns.
    """
    tables: list[tuple[str, int | str, str]] = []
    violations: list[str] = []
    heights: set[object] = set()

    for dashboard_path in sorted(Path("grafana/dashboards").glob("*.json")):
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "table":
                continue
            panel_id = panel.get("id", "?")
            title = panel_display_title(panel) or panel.get("title") or f"id={panel_id}"
            tables.append((dashboard_path.name, panel_id, str(title)))
            cell_height = panel.get("options", {}).get("cellHeight")
            heights.add(cell_height)
            if cell_height != UNIFORM_TABLE_CELL_HEIGHT:
                violations.append(
                    f"{dashboard_path.name} panel {panel_id} ({title!r}) "
                    f"cellHeight={cell_height!r}"
                )
            custom = ((panel.get("fieldConfig") or {}).get("defaults") or {}).get(
                "custom"
            ) or {}
            wrap_default = (custom.get("cellOptions") or {}).get("wrapText")
            if wrap_default is True:
                violations.append(
                    f"{dashboard_path.name} panel {panel_id} ({title!r}) "
                    "defaults.custom.cellOptions.wrapText=True "
                    "(grows row height; wrap named columns instead)"
                )

    assert tables, "expected at least one table panel in shipped dashboards"
    assert heights == {UNIFORM_TABLE_CELL_HEIGHT}, (
        "all table panels must share options.cellHeight="
        f"{UNIFORM_TABLE_CELL_HEIGHT!r}; observed={sorted(heights, key=str)}"
    )
    assert not violations, (
        "table panels must set options.cellHeight="
        f"{UNIFORM_TABLE_CELL_HEIGHT!r} and must not wrap at table default:\n"
        + "\n".join(violations)
    )


def _table_hidden_fields(panel: dict) -> set[str]:
    hidden: set[str] = set()
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        if not isinstance(override, dict):
            continue
        name = (override.get("matcher") or {}).get("options")
        if not isinstance(name, str):
            continue
        for prop in override.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            if prop.get("id") == "custom.hidden" and prop.get("value") is True:
                hidden.add(name)
            hide = prop.get("value")
            if (
                prop.get("id") == "custom.hideFrom"
                and isinstance(hide, dict)
                and hide.get("viz") is True
            ):
                hidden.add(name)
    return hidden


def _table_width_fields(panel: dict) -> set[str]:
    widths: set[str] = set()
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        if not isinstance(override, dict):
            continue
        name = (override.get("matcher") or {}).get("options")
        if not isinstance(name, str):
            continue
        for prop in override.get("properties") or []:
            if isinstance(prop, dict) and prop.get("id") == "custom.width":
                widths.add(name)
    return widths


def _organize_visible_fields(panel: dict) -> list[str] | None:
    for transform in panel.get("transformations") or []:
        if not isinstance(transform, dict) or transform.get("id") != "organize":
            continue
        options = transform.get("options") or {}
        index = options.get("indexByName") or {}
        if not isinstance(index, dict) or not index:
            return None
        excluded = options.get("excludeByName") or {}
        hidden = _table_hidden_fields(panel)
        return [
            str(name)
            for name in index
            if not excluded.get(name) and str(name) not in hidden
        ]
    return None


def test_table_panels_fill_panel_width() -> None:
    """Grafana TableNG only distributes leftover panel width to columns without custom.width.

    If every visible organize column is pinned, the table leaves an empty band
    inside the panel. Keep at least one flex column so the table occupies the
    full panel width.
    """
    violations: list[str] = []
    checked = 0
    for dashboard_path in sorted(Path("grafana/dashboards").glob("*.json")):
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "table":
                continue
            visible = _organize_visible_fields(panel)
            if not visible:
                continue
            checked += 1
            pinned = _table_width_fields(panel)
            if all(field in pinned for field in visible):
                panel_id = panel.get("id", "?")
                title = (
                    panel_display_title(panel) or panel.get("title") or f"id={panel_id}"
                )
                violations.append(
                    f"{dashboard_path.name} panel {panel_id} ({title!r}) "
                    f"visible={visible} pinned={sorted(pinned & set(visible))}"
                )
    assert checked > 0
    assert not violations, (
        "table panels must leave at least one visible organize column without "
        "custom.width so Grafana fills the panel:\n" + "\n".join(violations)
    )


def test_dq_ultra_short_timeseries_hides_legend() -> None:
    """Ultra-short timeseries (h≤4) free vertical chrome by hiding the legend.

    Issue #8530: DQ panel 153 Track Volume-Weighted DQ Score.
    """
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (item for item in get_dashboard_panels(dashboard) if item.get("id") == 153),
        None,
    )
    assert panel is not None, "DQ panel 153 must exist"
    assert panel.get("type") == "timeseries"
    assert panel.get("gridPos", {}).get("h") == 4
    assert panel.get("options", {}).get("legend", {}).get("showLegend") is False


def test_dashboard_metadata_policy_invariants() -> None:
    """Metadata should follow documented policy without mechanical suite-wide rewrites."""
    allowed_schema_versions = {30, 39}

    for dashboard_path in sorted(Path("grafana/dashboards").glob("*.json")):
        dashboard = load_dashboard(dashboard_path)
        assert dashboard.get("timezone") == "browser", (
            f"{dashboard_path.name} must set timezone='browser'"
        )

        schema_version = dashboard.get("schemaVersion")
        assert schema_version in allowed_schema_versions, (
            f"{dashboard_path.name} must keep approved schemaVersion variance "
            f"{sorted(allowed_schema_versions)}, got {schema_version!r}"
        )

        tags = dashboard.get("tags")
        assert isinstance(tags, list), f"{dashboard_path.name} tags must be a list"
        assert "bioetl" in tags, (
            f"{dashboard_path.name} must include the baseline 'bioetl' tag"
        )

        iteration = dashboard.get("iteration")
        if iteration is not None:
            assert isinstance(iteration, int) and iteration > 0, (
                f"{dashboard_path.name} iteration must be a positive integer when present"
            )


def test_dashboard_design_system_documents_metadata_policy() -> None:
    """Design system must explain why metadata is not rewritten mechanically."""
    text = Path("docs/03-guides/dashboards/design-system.md").read_text(
        encoding="utf-8"
    )
    required_tokens = {
        '`timezone` MUST быть `"browser"`',
        "`schemaVersion` MAY remain `30` or `39`",
        "`iteration` is optional",
        "`tags` MUST include the baseline suite tag `bioetl`",
        "`refresh=60s`",
        "`refresh=1m`",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, f"design-system metadata policy missing tokens: {missing}"
