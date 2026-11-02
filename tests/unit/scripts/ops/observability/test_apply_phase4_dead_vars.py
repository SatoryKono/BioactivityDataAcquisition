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
    assert "timepicker.refresh_intervals" in cleared


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
    assert "panel:99:repeat=overview_fleet" in cleared
    assert "timepicker.refresh_intervals" in cleared
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


def test_process_helpers_use_literal_repo_basenames() -> None:
    processors = (
        phase4._process_overview,
        phase4._process_dq,
        phase4._process_incident,
        phase4._process_control_plane,
        phase4._process_run_explorer,
    )
    assert len(processors) == len(phase4.FILES)
    assert (phase4.DASH / phase4.FILE_DQ).parent == phase4.DASH


def test_prune_dead_rename_by_name() -> None:
    payload = {
        "templating": {"list": [{"name": "workflow"}]},
        "panels": [
            {
                "id": 1,
                "transformations": [
                    {
                        "id": "organize",
                        "options": {
                            # indexByName is order-only; "unordered" stays valid.
                            "indexByName": {"a": 0},
                            "excludeByName": {"ghost": True},
                            "renameByName": {
                                "a": "A",
                                "unordered": "Still Valid",
                                "ghost": "Gone",
                            },
                        },
                    }
                ],
            }
        ],
    }
    _, cleared = phase4.apply_dashboard_data(payload, path_name=phase4.FILE_OVERVIEW)
    rename = payload["panels"][0]["transformations"][0]["options"]["renameByName"]
    assert rename == {"a": "A", "unordered": "Still Valid"}
    assert any(item.startswith("renameByName:pruned=") for item in cleared)


def test_ensure_shared_timepicker_refresh_intervals() -> None:
    payload: dict = {"templating": {"list": []}, "panels": [], "timepicker": {}}
    _, cleared = phase4.apply_dashboard_data(payload, path_name=phase4.FILE_INCIDENT)
    assert payload["timepicker"]["refresh_intervals"] == list(phase4._REFRESH_INTERVALS)
    assert "timepicker.refresh_intervals" in cleared


def test_drops_unused_selected_vars_on_incident() -> None:
    payload = {
        "templating": {
            "list": [
                {"name": "selected_run_id", "type": "query"},
                {"name": "selected_pipeline", "type": "query"},
                {"name": "workflow", "type": "query"},
            ]
        },
        "panels": [],
    }
    removed, _ = phase4.apply_dashboard_data(payload, path_name=phase4.FILE_INCIDENT)
    names = [var["name"] for var in payload["templating"]["list"]]
    assert names == ["workflow"]
    assert set(removed) == {"selected_run_id", "selected_pipeline"}
