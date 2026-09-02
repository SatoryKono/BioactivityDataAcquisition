# pyright: reportArgumentType=false
# pyright: reportIndexIssue=false
"""Regression tests for Grafana action routes and navigation layout rendering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import action_target_routes as routes
from scripts.ops.observability.grafana import render_nav_bus as nav_bus


pytestmark = pytest.mark.unit


def _panel(
    panel_id: int,
    panel_type: str,
    *,
    y: int,
    height: int,
    nested: list[object] | None = None,
) -> dict[str, object]:
    panel: dict[str, object] = {
        "id": panel_id,
        "type": panel_type,
        "gridPos": {"x": 0, "y": y, "w": 24, "h": height},
    }
    if nested is not None:
        panel["panels"] = nested
    return panel


def test_row_aware_action_url_preserves_row_and_destination_context() -> None:
    url = routes.row_aware_dashboard_url()

    assert "/d/${__data.fields.action_dashboard_uid}/" in url
    for field in ("workflow", "pipeline", "run_type", "run_id"):
        assert f"var-{field}=${{__data.fields.{field}}}" in url
    assert "var-stage=$__all" in url
    assert "var-provider=unknown" in url
    assert "var-pipeline_context=${__data.fields.pipeline}" in url
    assert nav_bus.build_handoff_url.__module__.endswith("dashboard_context_links")
    assert routes.TIME_TOKEN in url


@pytest.mark.parametrize(
    ("target", "expected_uid"),
    [
        ("runtime", "bioetl-runtime"),
        ("control_plane", "bioetl-control-plane-v1"),
        ("data_quality", "bioetl-dq-v2"),
        ("workflow", "bioetl-runtime"),
        ("provider", "bioetl-provider-health-v2"),
        ("dq", "bioetl-dq-v2"),
        ("verify_dq_reason_rules", None),
        ("future_target", None),
    ],
)
def test_dashboard_uid_for_every_action_target(
    target: str, expected_uid: str | None
) -> None:
    assert routes.dashboard_uid_for_target(target) == expected_uid


def test_nav_tooltips_describe_resets_and_escape_html_attributes() -> None:
    provider = {
        "uid": "bioetl-provider-health-v2",
        "title": '3. Provider "Health" <scope>',
        "path": "bioetl-provider-health-v2",
    }
    tooltip = nav_bus.nav_link_tooltip(
        source_uid="bioetl-overview-v2",
        target=provider,
    )
    rendered = nav_bus._chip_html(
        provider,
        current_uid="bioetl-overview-v2",
        source_uid="bioetl-overview-v2",
    )

    assert "Scope reset: provider=unknown" in tooltip
    assert "pipeline context" in tooltip
    assert "&quot;Health&quot;" in rendered
    assert "&lt;scope&gt;" in rendered
    runtime = next(item for item in nav_bus.BUS if item["uid"] == "bioetl-runtime")
    assert "stage=All" in nav_bus.nav_link_tooltip(
        source_uid="bioetl-overview-v2",
        target=runtime,
    )


def test_overflow_reclamation_uses_root_panels_and_keeps_minimum_height() -> None:
    nav = _panel(1000, "text", y=0, height=4)
    slack = _panel(1001, "text", y=4, height=4)
    first_window = _panel(1002, "table", y=12, height=7)
    nested = _panel(9601, "table", y=15, height=6)
    collapsed_row = _panel(9600, "row", y=18, height=1, nested=[nested])
    panels: list[object] = [nav, slack, first_window, collapsed_row]

    assert nav_bus._first_window_overflow(panels) == 1
    nav_bus._reclaim_first_window_overflow(nav, panels)

    assert slack["gridPos"]["h"] == 3
    assert first_window["gridPos"]["y"] == 11
    assert collapsed_row["gridPos"]["y"] == 17
    assert nested["gridPos"]["y"] == 15
    assert nav_bus._first_window_overflow(panels) == 0


def test_overflow_reclamation_fails_when_no_text_rail_has_slack() -> None:
    nav = _panel(1000, "text", y=0, height=4)
    too_short = _panel(1001, "text", y=4, height=3)
    overflowing = _panel(1002, "table", y=12, height=8)

    with pytest.raises(SystemExit, match="no protected layout band can reclaim"):
        nav_bus._reclaim_first_window_overflow(nav, [nav, too_short, overflowing])


def test_nav_expansion_shifts_only_root_panels() -> None:
    nav = _panel(1000, "text", y=0, height=3)
    nested = _panel(9601, "table", y=4, height=6)
    collapsed_row = _panel(9600, "row", y=3, height=1, nested=[nested])

    nav_bus._expand_nav_height(nav, [nav, collapsed_row], new_height=4)

    assert collapsed_row["gridPos"]["y"] == 4
    assert nested["gridPos"]["y"] == 4


def test_trust_layout_preserves_scalar_area_and_readable_cta() -> None:
    nav = _panel(1000, "text", y=0, height=4)
    scope = _panel(9400, "text", y=4, height=4)
    status = _panel(9401, "stat", y=4, height=4)
    trust = _panel(9418, "table", y=8, height=5)
    retention = _panel(9416, "table", y=8, height=5)
    recovery = _panel(906, "text", y=13, height=2)
    kpis = [
        _panel(891, "stat", y=15, height=3),
        _panel(892, "stat", y=15, height=3),
        _panel(893, "stat", y=15, height=3),
        _panel(907, "stat", y=15, height=3),
    ]
    nested = _panel(894, "text", y=20, height=5)
    collapsed_row = _panel(902, "row", y=18, height=1, nested=[nested])
    panels: list[object] = [
        nav,
        scope,
        status,
        trust,
        retention,
        recovery,
        *kpis,
        collapsed_row,
    ]

    nav_bus._layout_control_plane_first_window(panels)
    nav_bus._normalize_collapsed_row_children(panels)

    assert scope["gridPos"] == {"x": 0, "y": 4, "w": 16, "h": 3}
    assert status["gridPos"] == {"x": 16, "y": 4, "w": 8, "h": 3}
    assert status["gridPos"]["w"] * status["gridPos"]["h"] == 24
    assert trust["gridPos"]["y"] == retention["gridPos"]["y"] == 7
    assert all(kpi["gridPos"]["y"] == 15 for kpi in kpis)
    assert recovery["gridPos"] == {"x": 0, "y": 12, "w": 24, "h": 3}
    assert collapsed_row["gridPos"]["y"] == 18
    assert nested["gridPos"]["y"] == 19
    assert nav_bus._first_window_overflow(panels) == 0


def test_run_explorer_restores_scope_and_compacts_reviewed_table() -> None:
    nav = _panel(1000, "text", y=0, height=4)
    scope = _panel(1, "text", y=4, height=2)
    browse = _panel(3010, "table", y=6, height=12)
    collapsed_row = _panel(3099, "row", y=18, height=1)
    panels: list[object] = [nav, scope, browse, collapsed_row]

    nav_bus._restore_minimum_first_window_heights(
        panels, current_uid="bioetl-run-explorer-v1"
    )
    nav_bus._reclaim_first_window_overflow(
        nav, panels, current_uid="bioetl-run-explorer-v1"
    )

    assert scope["gridPos"] == {"x": 0, "y": 4, "w": 24, "h": 3}
    assert browse["gridPos"] == {"x": 0, "y": 7, "w": 24, "h": 11}
    assert collapsed_row["gridPos"]["y"] == 18


def test_apply_to_dashboard_expands_nav_and_reclaims_first_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dashboard = tmp_path / "dashboard.json"
    payload = {
        "templating": {"list": []},
        "panels": [
            _panel(1000, "text", y=0, height=3),
            _panel(1001, "text", y=3, height=4),
            _panel(1002, "table", y=8, height=10),
        ],
    }
    dashboard.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(nav_bus, "DASH_DIR", tmp_path)

    assert nav_bus.apply_to_dashboard(
        dashboard,
        current_uid="bioetl-overview-v2",
    )

    rendered = json.loads(dashboard.read_text(encoding="utf-8"))
    nav, slack, first_window = rendered["panels"]
    assert nav["gridPos"] == {"x": 0, "y": 0, "w": 24, "h": 4}
    assert slack["gridPos"]["h"] == 3
    assert first_window["gridPos"]["y"] + first_window["gridPos"]["h"] == 18
    assert len(nav["links"]) == 6
