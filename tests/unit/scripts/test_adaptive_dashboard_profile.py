"""An optional renderer must preserve the native portfolio and exact-run context."""

from __future__ import annotations

from copy import deepcopy

from scripts.ops.observability.grafana.generate_adaptive_dashboards import project


def test_projection_only_changes_renderer_and_keeps_native_fallback():
    source = {
        "uid": "bioetl-run-explorer-v1",
        "panels": [
            {
                "id": 3010,
                "type": "table",
                "targets": [{"url": "/ops/recent?pipeline=${pipeline}"}],
                "transformations": [
                    {"id": "organize", "options": {"run_id": "hidden identity"}}
                ],
                "options": {"sortBy": [{"displayName": "Started", "desc": True}]},
                "fieldConfig": {
                    "defaults": {"links": [{"url": "?run_id=${__data.fields.run_id}"}]}
                },
            }
        ],
    }
    original = deepcopy(source)
    result = project(source)
    assert source == original
    assert result["uid"] == source["uid"]
    native, adaptive = source["panels"][0], result["panels"][0]
    assert adaptive["type"] == "bioetl-selectorshell-panel"
    assert adaptive["options"]["viewMode"] == "runs"
    for key in ["targets", "transformations", "fieldConfig"]:
        assert adaptive[key] == native[key]
    assert native["type"] == "table"


def test_other_dashboard_is_an_unchanged_independent_copy():
    source = {"uid": "bioetl-dq-v2", "panels": [{"id": 9400, "type": "table"}]}
    result = project(source)
    assert result == source and result is not source


def test_overview_verdict_is_first_when_columns_stack_without_changing_semantics():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = json.loads(
        (root / "grafana/dashboards/bioetl-overview-v2.json").read_text(
            encoding="utf-8"
        )
    )
    original = deepcopy(source)
    projected = project(source)
    assert source == original
    first = min(
        (p for p in projected["panels"] if p.get("id") in {99, 9604}),
        key=lambda p: p["gridPos"]["x"],
    )
    assert first["id"] == 9604
    for before, after in zip(source["panels"], projected["panels"], strict=True):
        assert {k: v for k, v in before.items() if k != "gridPos"} == {
            k: v for k, v in after.items() if k != "gridPos"
        }
        assert {k: v for k, v in before["gridPos"].items() if k not in {"x", "w"}} == {
            k: v for k, v in after["gridPos"].items() if k not in {"x", "w"}
        }
    panels = [
        p["gridPos"]
        for p in projected["panels"]
        if p.get("id") in {99, 9002, 9604, 9603, 9300}
    ]
    for i, a in enumerate(panels):
        assert 0 <= a["x"] and a["x"] + a["w"] <= 24
        for b in panels[i + 1 :]:
            assert (
                a["x"] + a["w"] <= b["x"]
                or b["x"] + b["w"] <= a["x"]
                or a["y"] + a["h"] <= b["y"]
                or b["y"] + b["h"] <= a["y"]
            )
