"""Unit coverage for Phase 4.1 dead-variable cleanup."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import apply_phase4_dead_vars as phase4


pytestmark = pytest.mark.unit


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_drop_provider_and_pipeline_unknown(tmp_path: Path) -> None:
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
    path = _write(tmp_path, phase4.FILE_DQ, payload)
    removed, cleared = phase4.apply_file(path, dashboard_root=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    names = [var["name"] for var in data["templating"]["list"]]
    assert "provider_for_pipeline" not in names
    assert "workflow" in names
    assert data["templating"]["list"][0]["options"] == []
    assert "provider_for_pipeline" in removed
    assert "pipeline.options[unknown]" in removed
    assert cleared == []


def test_clear_dangling_overview_fleet_repeat(tmp_path: Path) -> None:
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
    path = _write(tmp_path, phase4.FILE_OVERVIEW, payload)
    removed, cleared = phase4.apply_file(path, dashboard_root=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    panel = data["panels"][0]
    assert "repeat" not in panel
    assert "repeatDirection" not in panel
    assert "maxPerRow" not in panel
    assert cleared == ["panel:99:repeat=overview_fleet"]
    assert removed == []


def test_keeps_incident_read_latency_quantile(tmp_path: Path) -> None:
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
    path = _write(tmp_path, phase4.FILE_INCIDENT, payload)
    removed, _ = phase4.apply_file(path, dashboard_root=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    names = [var["name"] for var in data["templating"]["list"]]
    assert "read_latency_quantile" in names
    assert "provider_for_pipeline" not in names
    assert removed == ["provider_for_pipeline"]


def test_apply_file_rejects_unexpected_basename(tmp_path: Path) -> None:
    path = _write(tmp_path, "not-a-dashboard.json", {"templating": {"list": []}})
    with pytest.raises(ValueError, match="unexpected dashboard file"):
        phase4.apply_file(path, dashboard_root=tmp_path)
