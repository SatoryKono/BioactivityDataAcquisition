"""An optional renderer must preserve the native portfolio and exact-run context."""

from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.ops.observability.grafana._audit_presentation import (
    project_adaptive_dashboard as project,
)

pytestmark = pytest.mark.unit


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

    def walk(panels):
        for panel in panels:
            yield panel
            yield from walk(panel.get("panels", []))

    for before, after in zip(
        walk(source["panels"]), walk(projected["panels"]), strict=True
    ):
        if after.get("options", {}).get("viewMode") == "current":
            view = after["options"]["currentView"]
            assert view["queries"] == before["targets"]
            assert view["transformations"] == before.get("transformations", [])
            assert view["options"] == before["options"]
            assert view["pluginId"] == before["type"]
            assert after["fieldConfig"] == before["fieldConfig"]
            assert after["targets"] == []
            assert after["transformations"] == []
        else:
            assert {
                k: v for k, v in before.items() if k not in {"gridPos", "panels"}
            } == {k: v for k, v in after.items() if k not in {"gridPos", "panels"}}
        if before["id"] not in {9604, 9603, 9300}:
            position_changes = {"x", "w"}
            if before["id"] == 9002:
                assert before["gridPos"]["h"] == 8
                assert after["gridPos"]["h"] == 9
                position_changes.add("h")
            assert {
                k: v for k, v in before["gridPos"].items() if k not in position_changes
            } == {
                k: v for k, v in after["gridPos"].items() if k not in position_changes
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


def test_current_consumer_uses_raw_donor_queries_and_preserves_its_own_transforms():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = json.loads(
        (root / "grafana/dashboards/bioetl-incident-v1.json").read_text(
            encoding="utf-8"
        )
    )

    def walk(panels):
        return [p for item in panels for p in [item, *walk(item.get("panels", []))]]

    before = {p["id"]: p for p in walk(source["panels"])}
    after = {p["id"]: p for p in walk(project(source)["panels"])}
    view = after[22005]["options"]["currentView"]
    assert view["queries"] == before[2005]["targets"]
    assert view["transformations"] == before[22005]["transformations"]
    assert after[22005]["fieldConfig"] == before[22005]["fieldConfig"]
    assert after[9701]["title"] == "Review Current Workflow Evidence · threshold 24h"
    assert after[16]["options"]["currentView"]["queries"][0]["instant"] is True
    assert "workflow_evidence_freshness" not in json.dumps(project(source))
    # Ranked suspects explicitly describe TIME RANGE and must keep that clock.
    ranked = after[2010]
    assert "currentView" not in ranked["options"]
    for key in ("targets", "transformations", "fieldConfig", "description"):
        assert ranked[key] == before[2010][key]
    for key, value in before[2010]["options"].items():
        assert ranked["options"][key] == value
    # Both paged tables fit beside each other; Details retains the full frame.
    alerts = after[2005]
    assert ranked["options"]["viewMode"] == "rows"
    assert alerts["options"]["currentView"]["compactFields"] == [
        "Severity",
        "Alert",
        "Pipeline",
        "State",
    ]
    # Explicit TIME RANGE wins over the mixed wording in these descriptions.
    for panel_id in (893, 907):
        assert "CURRENT" in before[panel_id]["description"][:45]
        assert "currentView" not in after[panel_id].get("options", {})
        for key in ("type", "targets", "transformations", "fieldConfig", "description"):
            assert after[panel_id].get(key) == before[panel_id].get(key)
    assert ranked["gridPos"]["x"] + ranked["gridPos"]["w"] <= alerts["gridPos"]["x"]
    for panel in (ranked, alerts):
        assert panel["gridPos"]["y"] + panel["gridPos"]["h"] <= 15
