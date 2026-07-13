"""Grafana dashboard layout and metadata integration contracts."""

from pathlib import Path
import re

import pytest
import yaml
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_navigation_links,
    get_dashboard_panels,
    get_row_child_panels,
    load_dashboard,
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
    offenders = [title for title in titles if fixed_window_suffix_re.search(title)]
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


def test_runtime_redundant_guidance_panels_stay_out_of_root_layout() -> None:
    """Runtime detail guidance must stay nested behind collapsed disclosure."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    root_titles = {
        panel.get("title")
        for panel in dashboard.get("panels", [])
        if isinstance(panel.get("title"), str)
    }

    assert "Inspect Runtime Scope" not in root_titles
    assert "Review Diagnostic Scope Note" not in root_titles
    assert "Review Incident Summary" not in root_titles
    detect_row = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("title") == "Detect"
        ),
        None,
    )
    assert detect_row is not None, "Runtime dashboard must keep Detect row"
    assert detect_row.get("collapsed") is True
    assert "Inspect Active Runtime Blocker Detail" not in root_titles
    detect_panels = get_row_child_panels(dashboard, "Detect")
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
        for panel in get_row_child_panels(dashboard, "Detect")
        if isinstance(panel.get("title"), str)
    }
    assert "Inspect Active Runtime Blocker Detail" in detect_titles
    _assert_panels_stay_in_grid_without_overlap(
        detect_panels, context="Runtime Detect disclosure"
    )


def test_runtime_first_screen_grid_uses_shared_panel_reference_sizes() -> None:
    """Runtime First Action must share the identity/evidence row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panels = {
        panel.get("title"): panel
        for panel in dashboard.get("panels", [])
        if isinstance(panel.get("title"), str)
    }

    first_action_grid = panels["First Action"]["gridPos"]
    id_grid = panels["ID"]["gridPos"]
    processed_records_grid = panels["Processed Records"]["gridPos"]

    assert (
        first_action_grid["x"]
        == processed_records_grid["x"] + processed_records_grid["w"]
    )
    assert first_action_grid["w"] == 8
    assert first_action_grid["h"] == processed_records_grid["h"]
    assert first_action_grid["y"] == id_grid["y"] == processed_records_grid["y"]
    assert first_action_grid["x"] + first_action_grid["w"] == 24


def test_runtime_telemetry_gap_panel_keeps_readable_first_screen_width() -> None:
    """Runtime datasource trust marker must stay legible on the first-screen evidence row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panels = {
        panel.get("title"): panel
        for panel in dashboard.get("panels", [])
        if isinstance(panel.get("title"), str)
    }

    panel = panels["Runtime Telemetry Gap"]
    grid = panel.get("gridPos", {})
    failed_runs_grid = panels["Failed Runs"]["gridPos"]

    assert grid["y"] == 23
    assert grid["w"] >= 4, (
        "Runtime Telemetry Gap must reserve readable width on the first screen"
    )
    assert failed_runs_grid["y"] == grid["y"]
    assert grid["x"] + grid["w"] == failed_runs_grid["x"]
    assert failed_runs_grid["x"] + failed_runs_grid["w"] == 24


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
    assert row_pairs == [
        (902, "Incident Drilldown: Replay Safety (Checkpoint / Replay)"),
        (901, "Incident Drilldown: Manifest / Ledger Integrity"),
        (903, "Incident Drilldown: Global Control-Plane Store Reliability"),
        (904, "Incident Drilldown: Audit / Lineage Completeness"),
        (905, "Identity evidence and remaining replay-safety signals"),
    ], f"Control Plane row order/title drifted: {row_pairs}"
    assert all(panel.get("collapsed") is True for panel in row_panels)


def test_control_plane_first_evidence_panel_stays_close_to_answer_row() -> None:
    """Selected-range blocker evidence stays close to the replay drilldown row."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Track: Replay / Resume Blockers in Range")
    assert panel is not None
    row_panel = panels["Incident Drilldown: Replay Safety (Checkpoint / Replay)"]
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("y") > row_panel.get("gridPos", {}).get("y", 0)
    assert grid_pos.get("w", 0) == 24


def test_control_plane_long_first_screen_titles_keep_extra_width() -> None:
    """Long first-screen title cards must keep enough width to avoid avoidable truncation risk."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for panel_title in (
        "Monitor: Manifest / Ledger Integrity",
        "Inspect: Telemetry Missing",
        "Next Action: Replay Diagnostics",
    ):
        panel = panels.get(panel_title)
        assert panel is not None
        grid_pos = panel.get("gridPos", {})
        assert grid_pos.get("w", 0) >= 5, (
            f"{panel_title} needs extra width for stable title/text rendering"
        )


def test_control_plane_terminal_events_table_has_readable_width() -> None:
    """Terminal event evidence table should keep enough width for practical status visibility."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Inspect: Terminal Run Events by Status in Range")
    assert panel is not None
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("w", 0) >= 12


def test_control_plane_manifest_evidence_top_band_uses_full_row_width() -> None:
    """Manifest evidence must use packed, non-overlapping disclosure bands."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("title") == "Incident Drilldown: Manifest / Ledger Integrity"
    )
    assert row.get("collapsed") is True
    child_panels = get_row_child_panels(
        dashboard, "Incident Drilldown: Manifest / Ledger Integrity"
    )
    panels = {panel.get("title"): panel for panel in child_panels if panel.get("title")}
    terminal = panels["Inspect: Terminal Run Events by Status in Range"]
    terminal_grid = terminal.get("gridPos", {})
    assert terminal_grid == {
        "h": 6,
        "w": 24,
        "x": 0,
        "y": row.get("gridPos", {}).get("y", 0) + 1,
    }
    failure_panels = [
        panels["Monitor: Manifest Write Failures"],
        panels["Monitor: Ledger Append Failures"],
    ]
    assert {panel.get("gridPos", {}).get("x") for panel in failure_panels} == {
        0,
        12,
    }
    assert {panel.get("gridPos", {}).get("w") for panel in failure_panels} == {12}
    assert {panel.get("gridPos", {}).get("h") for panel in failure_panels} == {6}
    assert {panel.get("gridPos", {}).get("y") for panel in failure_panels} == {
        terminal_grid["y"] + terminal_grid["h"]
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
        and panel.get("title")
        == "Incident Drilldown: Replay Safety (Checkpoint / Replay)"
    )
    assert row_panel.get("collapsed") is True
    child_panels = get_row_child_panels(
        dashboard, "Incident Drilldown: Replay Safety (Checkpoint / Replay)"
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
    assert blocker_grid.get("w") == 24
    assert blocker_grid.get("y") == blind_spots_grid.get("y") + blind_spots_grid.get(
        "h"
    )
    for left_id, right_id in ((3, 104), (120, 101)):
        pair = [panels[left_id], panels[right_id]]
        assert {panel.get("gridPos", {}).get("x") for panel in pair} == {0, 12}
        assert {panel.get("gridPos", {}).get("w") for panel in pair} == {12}
        assert len({panel.get("gridPos", {}).get("y") for panel in pair}) == 1
    assert panels[3].get("gridPos", {}).get("y") == blocker_grid.get(
        "y"
    ) + blocker_grid.get("h")
    assert panels[120].get("gridPos", {}).get("y") == panels[3].get("gridPos", {}).get(
        "y"
    ) + panels[3].get("gridPos", {}).get("h")
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
        and panel.get("title") == "Incident Drilldown: Audit / Lineage Completeness"
    )
    panels = {
        panel.get("id"): panel
        for panel in get_row_child_panels(
            dashboard, "Incident Drilldown: Audit / Lineage Completeness"
        )
    }
    panel = panels[122]
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("x") == 0
    assert grid_pos.get("y") == row_panel.get("gridPos", {}).get("y", 0) + 1
    assert grid_pos.get("w") == 24


def test_overview_current_panels_stay_out_of_selected_range_semantics() -> None:
    """Overview L0/L1 current-answer panels must not use $__range windows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for panel_title in (
        "Status",
        "First Action",
        "Inputs",
        "Runtime",
        "Data Quality",
        "Data Validation",
        "Control Plane",
        "Provider",
        "Workflow",
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
        "Inspect Errors by Stage / Error Code / Range": "bioetl_errors_total",
        "Track Records by Stage / Run Type / Range": "bioetl_records_processed_total",
        "Track Pipeline Phase Duration p50/p95/p99": "bioetl_phase_duration_seconds_bucket",
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

    reconstruct = panels.get("Monitor: Replay Not Reconstructable")
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
        drift = panels.get("Monitor: Replay Drift")
    assert drift is not None
    drift_expr = "\n".join(
        target.get("expr", "")
        for target in drift.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_replay_drift_events_total" in drift_expr

    lag = panels.get("Track: Replay Lag Seconds")
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
        "Monitor: Replay Safety State",
        "Monitor: Manifest / Ledger Integrity",
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
        "Monitor: Checkpoint Incompatibilities",
        "Monitor: Replay Not Reconstructable",
        "Monitor: Checkpoint Load Failures",
        "Monitor: Checkpoint Save Failures",
        "Track: Checkpoint Compatibility Outcomes",
        "Track: Checkpoint Save Latency p50/p95/p99",
        "Monitor: Ledger Append Failures",
        "Track: Ledger Appends by Event Type / Status",
        "Monitor: Ledger Append Failure Ratio",
        "Monitor: Lineage Refs Missing",
        "Monitor: Lineage Fragment Persistence Failures",
        "Inspect: Missing Lineage Refs by Layer / Type",
        "Track: Lineage Fragment Outcomes",
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
        assert "run_type selector does not change this panel" in description, (
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
        "Inspect: Telemetry Missing": ("bioetl_control_plane_telemetry_missing_5m",),
        "Inspect: Terminal Run Events by Status in Range": (
            "bioetl_control_plane_terminal_events_total",
        ),
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

    telemetry = panels["Inspect: Telemetry Missing"]
    assert telemetry.get("fieldConfig", {}).get("defaults", {}).get("noValue") == (
        "UNKNOWN"
    )


def test_control_plane_first_screen_normalizes_workflow_pipeline_aliases() -> None:
    """Current-state trust cards must resolve workflow_<pipeline> selectors back to entity scope."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor: Replay Safety State",
        "Monitor: Manifest / Ledger Integrity",
        "Inspect: Telemetry Missing",
    ):
        panel = panels.get(title)
        assert panel is not None, f"Control Plane dashboard missing {title!r}"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert "and on(pipeline)" in expr, (
            f"{title!r} must filter current-state metrics through a normalized "
            "pipeline selector"
        )
        assert 'label_replace(vector(1), "pipeline_raw", "$pipeline"' in expr
        assert '"^(?:workflow_)?(.*)$"' in expr


def test_control_plane_failure_ratio_thresholds_match_descriptions() -> None:
    """Manifest/ledger ratio panels should project >10% into CRIT severity."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor: Manifest Write Failure Ratio",
        "Monitor: Ledger Append Failure Ratio",
        "Monitor: GLOBAL Control-Plane Read Failure Ratio Severity",
    ):
        panel = panels.get(title)
        assert panel is not None
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        if title == "Monitor: GLOBAL Control-Plane Read Failure Ratio Severity":
            assert "> bool 0.05" in expr
            assert "> bool 0.10" in expr
        else:
            assert "> bool 0.1" in expr
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

    baseline = {"time_from": "now-12h", "refresh": "30s"}
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
    """Provider detail telemetry must stay behind explicit progressive disclosure."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panels = get_dashboard_panels(dashboard)
    detail_row = next(
        (
            panel
            for panel in panels
            if panel.get("type") == "row"
            and panel.get("title") == "Selected Provider Detail"
        ),
        None,
    )
    assert detail_row is not None
    assert detail_row.get("collapsed") is True

    child_panels = get_row_child_panels(dashboard, "Selected Provider Detail")
    child_titles = {
        panel.get("title")
        for panel in child_panels
        if isinstance(panel.get("title"), str)
    }
    assert "Inspect Provider Health Check Latency (p95) - $provider" in child_titles
    root_titles = {
        panel.get("title")
        for panel in dashboard.get("panels", [])
        if isinstance(panel.get("title"), str)
    }
    assert "Inspect Provider Health Check Latency (p95) - $provider" not in root_titles
    detail_panel = next(
        panel
        for panel in child_panels
        if panel.get("title")
        == "Inspect Provider Health Check Latency (p95) - $provider"
    )
    assert detail_panel.get("gridPos", {}).get("y", 0) > detail_row.get(
        "gridPos", {}
    ).get("y", 0)
    _assert_panels_stay_in_grid_without_overlap(
        child_panels, context="Provider selected-detail disclosure"
    )


def test_runtime_dq_control_plane_expose_contextual_loki_explore_link() -> None:
    """Only Runtime/DQ critical panels expose contextual Loki Explore links."""
    dashboard_panels = {
        "bioetl-runtime.json": "Failed Runs",
        "bioetl-dq-v2.json": "Track Range Evidence: Bronze -> Silver -> Gold",
    }

    for dashboard_name, panel_title in dashboard_panels.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        panel = panels.get(panel_title)
        assert panel is not None, (
            f"{dashboard_name} missing critical panel {panel_title!r}"
        )

        links = panel.get("options", {}).get("dataLinks", [])
        assert links, f"{dashboard_name}:{panel_title} must include dataLinks"

        baseline = [
            link
            for link in links
            if isinstance(link, dict)
            and str(link.get("title", "")).startswith("Open Logs (Loki")
            and "query=%7Bjob%3D%22bioetl%22%7D" in str(link.get("url", ""))
        ]
        assert baseline, (
            f'{dashboard_name}:{panel_title} must keep baseline Loki link with {{job="bioetl"}}'
        )

        contextual = [
            link
            for link in links
            if isinstance(link, dict)
            and link.get("title")
            in [
                "Open Logs (Loki, contextual scope marker)",
                "Open Logs (Loki, contextual scope marker, tracing)",
            ]
            and "scope_marker%3D%22dashboard_context%22" in str(link.get("url", ""))
        ]
        assert contextual, (
            f"{dashboard_name}:{panel_title} must include contextual Loki link with scope marker"
        )
        for link in contextual:
            url = str(link.get("url", ""))
            assert "run_id" not in url
            assert "payload_hash" not in url


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
        "`bioetl-silver-reject-explorer`",
        "`refresh=30s`",
        "`refresh=1m`",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, f"design-system metadata policy missing tokens: {missing}"


def test_control_plane_exposes_scope_preserving_explore_links() -> None:
    """Control Plane navigation must offer scoped Logs and Traces handoffs."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    links_by_title = {
        str(link.get("title")): str(link.get("url"))
        for link in get_dashboard_navigation_links(dashboard)
    }

    expected_routes = {
        "Explore Logs": "grafana-lokiexplore-app",
        "Explore Traces": "grafana-exploretraces-app",
    }
    for title, route in expected_routes.items():
        url = links_by_title.get(title, "")
        assert route in url
        assert "from=${__from}" in url
        assert "to=${__to}" in url
        assert "from=now-150m&to=now" not in url
