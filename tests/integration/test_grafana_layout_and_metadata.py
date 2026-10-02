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
from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    panel_declared_row_cap,
)
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
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
    """Fleet diagnostics remain below the current suspect answer."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    row = next(p for p in dashboard["panels"] if p["id"] == 8808)
    assert row["collapsed"] is True
    assert row["gridPos"]["y"] >= FIRST_WINDOW_Y
    ids = {p["id"] for p in get_dashboard_panels({"panels": row["panels"]})}
    assert {9101, 9102, 242, 205, 9996, 9997} <= ids
    assert (
        next(p for p in dashboard["panels"] if p["id"] == 2010)["gridPos"]["y"]
        < FIRST_WINDOW_Y
    )


def test_runtime_redundant_guidance_panels_stay_out_of_root_layout() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    row = next(p for p in dashboard["panels"] if p["id"] == 8808)
    detail = next(p for p in row["panels"] if p["id"] == 242)
    assert row["collapsed"] is True
    assert detail["title"] == "Inspect Active Runtime Blocker Detail"
    assert detail["gridPos"]["y"] > row["gridPos"]["y"]
    assert 242 not in {p["id"] for p in dashboard["panels"]}


def test_runtime_first_screen_grid_uses_shared_panel_reference_sizes() -> None:
    """Exact-run identity has one owner on the Overview first screen."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    identity = next(p for p in dashboard["panels"] if p["id"] == 9300)
    assert identity["gridPos"] == {"x": 15, "y": 10, "w": 9, "h": 8}
    assert "/ops/observability/selected-run-status?" in identity["targets"][0]["url"]
    assert "run_id=${run_id}" in identity["targets"][0]["url"]
    assert (
        "custom.inspect" in str(identity["fieldConfig"])
        or identity["fieldConfig"]["defaults"]["custom"]["inspect"] is True
    )


def test_runtime_telemetry_gap_panel_keeps_readable_first_screen_width() -> None:
    """Coverage and failed-run counters stay discoverable in fleet disclosure."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    row = next(p for p in dashboard["panels"] if p["id"] == 8808)
    panels = {p["id"]: p for p in get_dashboard_panels({"panels": row["panels"]})}
    assert row["collapsed"] is True
    assert panels[9102]["gridPos"]["w"] >= 4
    assert panels[9102]["title"] == "Monitor Coverage"
    assert "bioetl_pipeline_runs_total" in str(panels[205]["targets"])
    assert panels[9102]["gridPos"]["y"] > row["gridPos"]["y"]


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
    _assert_panels_stay_in_grid_without_overlap(
        root_panels,
        context="bioetl-control-plane-v1.json root layout excluding nav/scope",
    )


def test_control_plane_row_sequence_matches_operator_flow() -> None:
    """Replay diagnostics separate persisted provenance from resume validation."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    rows = [p for p in dashboard["panels"] if p["type"] == "row"]
    assert [(p["id"], p["title"]) for p in rows] == [
        (9430, "Inspect Manifest / Lineage / Retention"),
        (9431, "Inspect Resume / Checkpoint"),
    ]
    assert all(p["collapsed"] is True and p["panels"] for p in rows)
    assert [p["id"] for p in rows[0]["panels"]] == [9414, 9415, 9416]
    assert [p["id"] for p in rows[1]["panels"]] == [9413, 9406]


def test_control_plane_named_review_surfaces_are_findable() -> None:
    """Exact readiness is first-window; provenance is explicitly disclosed below."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    assert panels[9422]["title"] == "Review Exact Replay Readiness"
    assert panels[9422]["gridPos"]["y"] < 18
    assert panels[9418]["title"] == "Review Selected-Run Trust"
    assert panels[9416]["title"] == "Review Retention Compliance"
    assert panels[9415]["title"] == "Review Lineage Validation"
    assert {9414, 9415, 9416} <= {p["id"] for p in panels[9430]["panels"]}
    assert panels[9430]["collapsed"] is True


def test_retention_panel_9416_retry_preserves_selected_run_and_time() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(
        item
        for item in get_dashboard_panels(dashboard)
        if isinstance(item, dict) and item.get("id") == 9416
    )
    target = panel["targets"][0]
    assert target.get("parser") == "backend"
    assert target.get("root_selector") == "rows"
    target_url = str(target.get("url", ""))
    assert "error_as_row=1" in target_url
    assert "run_id=${run_id}" in target_url
    links = panel.get("fieldConfig", {}).get("defaults", {}).get("links") or []
    assert all("viewPanel=9416" not in str(link.get("url", "")) for link in links)
    assert "run_id=${run_id}" in target_url


def test_control_plane_first_evidence_panel_stays_close_to_answer_row() -> None:
    """The readiness verdict and all exact checks precede the first-window fold."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {p["id"]: p for p in dashboard["panels"]}
    answer, checks = panels[9422], panels[9423]
    assert checks["type"] == "table"
    assert checks["gridPos"]["y"] == answer["gridPos"]["y"] + answer["gridPos"]["h"]
    assert checks["gridPos"]["y"] + checks["gridPos"]["h"] <= 18
    assert checks["gridPos"]["w"] == 24


def test_control_plane_long_first_screen_titles_keep_extra_width() -> None:
    """Replay verdict and exact-checks titles retain readable first-window width."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {p["id"]: p for p in dashboard["panels"]}
    for pid in (9400, 9422, 9423):
        assert panels[pid]["gridPos"]["w"] >= 5


def test_control_plane_trust_panels_follow_reference_widths() -> None:
    """First-window verdict shares a row with scope; exact checks use full width."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {p["id"]: p for p in dashboard["panels"]}
    scope, verdict, checks = (panels[pid]["gridPos"] for pid in (9400, 9422, 9423))
    assert scope == {"x": 0, "y": 2, "w": 15, "h": 3}
    assert verdict == {"x": 15, "y": 2, "w": 9, "h": 3}
    assert checks == {"x": 0, "y": 5, "w": 24, "h": 13}
    _assert_panels_stay_in_grid_without_overlap(
        [panels[9400], panels[9422], panels[9423]], context="Replay first-window"
    )


def test_control_plane_terminal_events_table_has_readable_width() -> None:
    """Terminal event evidence table should keep enough width for practical status visibility."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("Review Observed Terminal Counters")
    assert panel is not None
    grid_pos = panel.get("gridPos", {})
    assert grid_pos.get("w", 0) >= 12


def test_control_plane_manifest_evidence_top_band_uses_full_row_width() -> None:
    """Persisted manifest, lineage and retention use full-width disclosure tables."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row = next(p for p in dashboard["panels"] if p["id"] == 9430)
    assert row["collapsed"] is True
    assert {p["id"] for p in row["panels"]} == {9414, 9415, 9416}
    for p in row["panels"]:
        assert p["gridPos"]["x"] == 0 and p["gridPos"]["w"] == 24
        assert p["gridPos"]["y"] > row["gridPos"]["y"]
        assert p["gridPos"]["h"] >= 4
    _assert_panels_stay_in_grid_without_overlap(
        row["panels"], context="Replay provenance"
    )


def test_control_plane_replay_safety_detail_top_bands_use_full_row_width() -> None:
    """Resume and checkpoint evidence remain accessible without overlapping rows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row = next(p for p in dashboard["panels"] if p["id"] == 9431)
    assert row["collapsed"] is True
    assert {p["id"] for p in row["panels"]} == {9413, 9406}
    for p in row["panels"]:
        assert p["gridPos"]["x"] == 0 and p["gridPos"]["w"] == 24
        assert p["gridPos"]["y"] > row["gridPos"]["y"]
        assert p["gridPos"]["h"] >= 4
    _assert_panels_stay_in_grid_without_overlap(
        row["panels"], context="Resume/checkpoint"
    )


def test_control_plane_lineage_top_band_uses_full_row_width() -> None:
    """Selected-run lineage belongs to the persisted provenance disclosure."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    row = next(p for p in dashboard["panels"] if p["id"] == 9430)
    panel = next(p for p in row["panels"] if p["id"] == 9415)
    assert panel["gridPos"]["w"] == 24 and panel["gridPos"]["x"] == 0
    assert panel["gridPos"]["y"] > row["gridPos"]["y"]
    assert "run_id=${run_id}" in panel["targets"][0]["url"]


def test_overview_current_panels_stay_out_of_selected_range_semantics() -> None:
    """Overview L0/L1 current-answer panels must not use $__range windows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for panel_title in (
        "Monitor Scope Health",
        "Review First Action",
        "Review All Domain Status",
        "Review Runtime Status",
        "Review Data Quality Status",
        "Review Data Validation Status",
        "Review Control Plane Status",
        "Review Global Provider Status",
        "Review Workflow Status",
    ):
        assert panel_title not in panels
        continue
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
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


@pytest.mark.parametrize("dashboard_file", ["bioetl-incident-v1.json"])
def test_replay_panels_are_split_by_semantics(dashboard_file: str) -> None:
    """Control-plane replay diagnostics must keep reconstructability, drift, and lag separate."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    reconstruct = panels.get("Track Unreconstructable")
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
    if dashboard_file == "bioetl-incident-v1.json":
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor Replay",
        "Monitor Ledger",
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
        assert panel.get("options", {}).get("colorMode") == "value"

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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expected_titles = (
        "Track Incompatibilities",
        "Track Unreconstructable",
        "Track Load Failures",
        "Track Save Failures",
        "Compare Checkpoint Outcomes",
        "Track Checkpoint Save Latency",
        "Track Ledger Failures",
        "Compare Ledger Appends by Type & Status",
        "Monitor Ledger (30m)",
        "Track Missing Lineage",
        "Track Lineage Failures",
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expected = {
        "Monitor Telemetry": ("bioetl_control_plane_telemetry_missing_5m",),
        "Review Observed Terminal Counters": (
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

    telemetry = panels["Monitor Telemetry"]
    assert telemetry.get("fieldConfig", {}).get("defaults", {}).get("noValue") == (
        "UNKNOWN"
    )


def test_control_plane_bounded_failure_rows_preserve_unknown_evidence() -> None:
    """Exact replay checks preserve error rows and do not replace absence with zero."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9423)
    assert panel["type"] == "table"
    assert panel["options"]["showHeader"] is True
    assert panel["options"]["footer"]["enablePagination"] is True
    target = panel["targets"][0]
    assert target["parser"] == "uql"
    assert "replay_checks" in target["uql"]
    assert "run_id=${run_id}" in target["url"]
    assert "/ops/observability/selected-run-status?" in target["url"]
    assert "QUERY ERROR" in panel["description"]
    assert "unknown" in panel["description"].lower()
    assert not any(t.get("id") == "limit" for t in panel.get("transformations", []))


def test_control_plane_first_screen_normalizes_workflow_pipeline_aliases() -> None:
    """Trust first-screen cards use thin pipeline selectors (#6574; no mega-expr glue)."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor Replay",
        "Monitor Ledger",
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    for title in (
        "Monitor Manifest (30m)",
        "Monitor Ledger (30m)",
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
        elif title == "Monitor Manifest (30m)":
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
    """Current provider suspects are disclosed separately from saved run evidence."""
    incident = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    row = next(p for p in incident["panels"] if p["id"] == 2099)
    assert row["collapsed"] is True
    provider = next(p for p in row["panels"] if p["id"] == 2003)
    assert provider["gridPos"]["y"] > row["gridPos"]["y"]
    assert "bioetl_provider_current_cause" in str(provider["targets"])
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    saved = next(p for p in overview["panels"] if p["id"] == 9480)
    assert "run_id=${run_id}" in str(saved["targets"])
    assert "expr" not in saved["targets"][0]


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


def test_all_table_panels_use_uniform_cell_height() -> None:
    """Compact tables use sm; wrapped pagination uses native size-aware pages.

    Grafana 12 calculates page size from the cellHeight preset, so wrapped
    last-10 browse rows require lg to avoid clipping at a 683 px CSS viewport.
    Rendered containment remains mandatory for every pagination page.
    """
    tables = []
    for dashboard_path in sorted(Path("grafana/dashboards").glob("*.json")):
        for panel in get_dashboard_panels(load_dashboard(dashboard_path)):
            if panel.get("type") != "table":
                continue
            tables.append(panel)
            options = panel.get("options", {})
            custom = panel.get("fieldConfig", {}).get("defaults", {}).get("custom", {})
            paginated = options.get("footer", {}).get("enablePagination") is True
            wrapped = custom.get("cellOptions", {}).get("wrapText") is True
            height = options.get("cellHeight")
            assert height in {"sm", "md", "lg"}, (
                dashboard_path.name,
                panel.get("id"),
                height,
            )
            if height == "lg":
                assert paginated and wrapped
                assert panel["gridPos"]["h"] > 6
            if height == "md":
                # #10498/#10504: native 54px pages prevent partially hidden rows.
                assert paginated and custom.get("inspect") is True
                assert panel["gridPos"]["h"] > 6
            if wrapped:
                # 1fee6a viewport-fit: incident 2010 h4 with wrap uses no pagination to avoid 21px footer overflow
                if (
                    dashboard_path.name == "bioetl-incident-v1.json"
                    and panel.get("id") == 2010
                ):
                    assert paginated is False
                else:
                    assert paginated or panel_declared_row_cap(panel) is not None
                assert custom.get("minWidth") == 50
    assert tables


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


# Stream-2 compact Trust/fleet tables pin every visible column (#10247/#10252).
_STREAM2_FULLY_PINNED_TABLES = {
    ("bioetl-control-plane-v1.json", 9405),
    ("bioetl-control-plane-v1.json", 9406),
    ("bioetl-control-plane-v1.json", 9407),
    ("bioetl-control-plane-v1.json", 9408),
    ("bioetl-control-plane-v1.json", 9409),
    ("bioetl-provider-health-v2.json", 9102),
}


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
            if (dashboard_path.name, panel.get("id")) in _STREAM2_FULLY_PINNED_TABLES:
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


def test_dq_score_chart_keeps_readable_height_with_semantic_legend() -> None:
    """Run quality uses saved accounting; no range chart implies run success."""
    dq = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    assert 153 not in {p["id"] for p in get_dashboard_panels(dq)}
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    quality = next(p for p in overview["panels"] if p["id"] == 9482)
    assert quality["type"] == "canvas"
    assert quality["gridPos"]["h"] == 6
    assert "run_id=${run_id:percentencode}" in quality["targets"][0]["url"]
    assert "UNKNOWN" in quality["description"]
    assert "historical run overrides" in quality["description"]
    assert "quarantined" in quality["description"].lower()


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
