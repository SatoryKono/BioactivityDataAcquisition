"""Unit tests for the scalar information-density survey (DASH-DENSITY-002)."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.engineering.qa import report_dashboard_scalar_density as density

pytestmark = pytest.mark.unit


def _stat(
    panel_id: int,
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    values: bool = False,
    targets: int = 1,
    ptype: str = "stat",
) -> dict[str, Any]:
    panel: dict[str, Any] = {
        "id": panel_id,
        "type": ptype,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [{"expr": f"m{i}"} for i in range(targets)],
    }
    if values:
        panel["options"] = {"reduceOptions": {"values": True}}
    return panel


def test_scalar_density_single_value_stats() -> None:
    panels = [_stat(1, x=0, y=0, w=6, h=4), _stat(2, x=6, y=0, w=6, h=4)]
    assert density.scalar_density(panels) == pytest.approx(2 / 48)


def test_scalar_density_excludes_timeseries_table_and_text() -> None:
    panels = [
        _stat(1, x=0, y=0, w=6, h=4),
        {"type": "table", "gridPos": {"w": 24, "h": 6}},
        {"type": "timeseries", "gridPos": {"w": 24, "h": 6}},
        {"type": "text", "gridPos": {"w": 24, "h": 2}},
    ]
    assert density.scalar_density(panels) == pytest.approx(1 / 24)


def test_scalar_density_is_none_without_scalars() -> None:
    assert density.scalar_density([{"type": "table", "gridPos": {"w": 24, "h": 6}}]) is None
    assert density.scalar_density([]) is None


def test_multi_value_scalar_counts_live_targets() -> None:
    panel = _stat(1, x=0, y=0, w=12, h=6, values=True, targets=3)
    assert density.scalar_density([panel]) == pytest.approx(3 / 72)


def test_first_screen_scalar_panels_filters_by_fold_and_type() -> None:
    dashboard = {
        "panels": [
            _stat(1, x=0, y=3, w=6, h=4),
            {"type": "text", "gridPos": {"w": 24, "h": 3, "x": 0, "y": 0}},
            {
                "type": "row",
                "gridPos": {"w": 24, "h": 1, "x": 0, "y": 13},
                "panels": [_stat(9, x=0, y=20, w=6, h=4)],
            },
            _stat(2, x=0, y=20, w=6, h=4),
        ]
    }
    assert [p["id"] for p in density.first_screen_scalar_panels(dashboard)] == [1]


def test_survey_flags_group_sparser_than_first_screen() -> None:
    dashboard = {
        "uid": "d",
        "panels": [
            _stat(1, x=0, y=3, w=6, h=4),
            _stat(2, x=6, y=3, w=6, h=4),
            {
                "type": "row",
                "id": 900,
                "title": "G",
                "gridPos": {"w": 24, "h": 1, "x": 0, "y": 13},
                "panels": [_stat(10, x=0, y=14, w=24, h=6)],
            },
        ],
    }
    result = density.survey_dashboard(dashboard)
    assert result["first_screen_density"] == pytest.approx(2 / 48)
    group = result["groups"][0]
    assert group["density"] == pytest.approx(1 / 144)
    assert group["passes"] is False


def test_survey_passes_group_denser_than_first_screen() -> None:
    dashboard = {
        "uid": "d",
        "panels": [
            _stat(1, x=0, y=3, w=12, h=6),
            {
                "type": "row",
                "id": 900,
                "title": "G",
                "gridPos": {"w": 24, "h": 1, "x": 0, "y": 13},
                "panels": [
                    _stat(10, x=0, y=14, w=6, h=4),
                    _stat(11, x=6, y=14, w=6, h=4),
                    _stat(12, x=12, y=14, w=6, h=4),
                    _stat(13, x=18, y=14, w=6, h=4),
                ],
            },
        ],
    }
    group = density.survey_dashboard(dashboard)["groups"][0]
    assert group["passes"] is True


def test_survey_group_without_scalars_is_exempt() -> None:
    dashboard = {
        "uid": "d",
        "panels": [
            _stat(1, x=0, y=3, w=6, h=4),
            {
                "type": "row",
                "id": 900,
                "title": "G",
                "gridPos": {"w": 24, "h": 1, "x": 0, "y": 13},
                "panels": [{"type": "table", "gridPos": {"w": 24, "h": 6, "x": 0, "y": 14}}],
            },
        ],
    }
    assert density.survey_dashboard(dashboard)["groups"][0]["passes"] is None
