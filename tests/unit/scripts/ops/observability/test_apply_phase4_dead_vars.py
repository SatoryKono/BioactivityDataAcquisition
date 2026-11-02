"""Unit coverage for Phase 4.1 dead-variable cleanup."""

from __future__ import annotations


import pytest

from scripts.ops.observability.grafana import apply_phase4_dead_vars as phase4


pytestmark = pytest.mark.unit


def test_drop_provider_and_pipeline_unknown() -> None:
    payload = {
        "templating": {
            "list": [
                {
                    "name": "pipeline",
                    "options": [
                        {"selected": False, "text": "unknown", "value": "unknown"}
                    ],
                },
                {"name": "provider_for_pipeline", "type": "query"},
                {"name": "workflow", "type": "query"},
            ]
        },
        "panels": [],
    }
    removed, cleared = phase4.apply_dashboard_data(payload, path_name=phase4.FILE_DQ)
    names = [var["name"] for var in payload["templating"]["list"]]
    assert "provider_for_pipeline" not in names
    assert "workflow" in names
    assert payload["templating"]["list"][0]["options"] == []
    assert "provider_for_pipeline" in removed
    assert "pipeline.options[unknown]" in removed
    assert cleared == []


def test_clear_dangling_overview_fleet_repeat() -> None:
    payload = {
        "templating": {"list": [{"name": "pipeline", "options": []}]},
        "panels": [
            {
                "id": 99,
                "type": "text",
                "repeat": "overview_fleet",
                "repeatDirection": "v",
                "maxPerRow": 1,
                "options": {"content": "x"},
            }
        ],
    }
    removed, cleared = phase4.apply_dashboard_data(
        payload, path_name=phase4.FILE_OVERVIEW
    )
    panel = payload["panels"][0]
    assert "repeat" not in panel
    assert "repeatDirection" not in panel
    assert "maxPerRow" not in panel
    assert cleared == ["panel:99:repeat=overview_fleet"]
    assert removed == []


def test_keeps_incident_read_latency_quantile() -> None:
    payload = {
        "templating": {
            "list": [
                {"name": "read_latency_quantile", "type": "custom"},
                {"name": "provider_for_pipeline", "type": "query"},
            ]
        },
        "panels": [
            {
                "id": 1,
                "targets": [{"expr": "histogram_quantile($read_latency_quantile, x)"}],
            }
        ],
    }
    removed, _ = phase4.apply_dashboard_data(payload, path_name=phase4.FILE_INCIDENT)
    names = [var["name"] for var in payload["templating"]["list"]]
    assert "read_latency_quantile" in names
    assert "provider_for_pipeline" not in names
    assert removed == ["provider_for_pipeline"]


def test_apply_dashboard_data_rejects_unexpected_basename() -> None:
    with pytest.raises(ValueError, match="unexpected dashboard file"):
        phase4.apply_dashboard_data({}, path_name="not-a-dashboard.json")


def test_literal_dashboard_path_only_allows_known_files() -> None:
    assert phase4._literal_dashboard_path(phase4.FILE_DQ).name == phase4.FILE_DQ
    with pytest.raises(ValueError, match="unexpected dashboard file"):
        phase4._literal_dashboard_path("not-a-dashboard.json")
