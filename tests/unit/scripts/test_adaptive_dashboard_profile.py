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


def test_wide_recent_run_table_exposes_decision_fields_without_changing_data():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = json.loads(
        (root / "grafana/dashboards/bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    native = next(panel for panel in source["panels"] if panel.get("id") == 3010)
    adaptive = next(
        panel for panel in project(source)["panels"] if panel.get("id") == 3010
    )
    renames = next(
        item["options"]["renameByName"]
        for item in native["transformations"]
        if item["id"] == "organize"
    )
    visible = set(renames.values())
    for override in adaptive["fieldConfig"]["overrides"]:
        if any(
            prop["id"] == "custom.hidden" and prop["value"]
            for prop in override["properties"]
        ):
            visible.discard(override["matcher"].get("options"))
    required = {"Workflow", "Duration", "Replay Readiness", "Data Quality"}
    assert required <= visible, f"Wide catalog hides {required - visible}"
    assert {"Pipeline", "Run ID", "Started", "Overview"} <= visible
    assert adaptive["options"]["compactFields"] == [
        "Provider",
        "Pipeline",
        "Run ID",
        "Overview",
    ]
    assert "in the table data inspector" not in adaptive["description"]
    for key in ("targets", "transformations"):
        assert adaptive[key] == native[key]
    assert adaptive["fieldConfig"]["defaults"] == native["fieldConfig"]["defaults"]
    for before, after in zip(
        native["fieldConfig"]["overrides"],
        adaptive["fieldConfig"]["overrides"],
        strict=True,
    ):
        assert before["matcher"] == after["matcher"]
        if after["matcher"].get("options") not in required:
            assert after == before
            continue
        changed = {"custom.hidden"}
        if after["matcher"].get("options") in {"Workflow", "Data Quality"}:
            changed.add("links")
        assert [p for p in after["properties"] if p["id"] not in changed] == [
            p for p in before["properties"] if p["id"] not in changed
        ]

    def links(panel, name):
        override = next(o for o in panel["fieldConfig"]["overrides"] if o["matcher"]["options"] == name)
        return next(p["value"] for p in override["properties"] if p["id"] == "links")

    # Exercise the actual compact-to-wide projection, including the generated
    # hidden identity fields. Neither action may inherit the global selector.
    for name, title in (("Workflow", "Workflow passport"), ("Data Quality", "Data Quality")):
        action = next(link for link in links(native, "Run ID") if link["title"] == title)
        assert links(native, name) == []
        assert links(adaptive, name) == [action]
        assert action in links(adaptive, "Run ID")
        assert action["includeVars"] is False
    assert "${__data.fields.workflow_passport_path:raw}" in links(adaptive, "Workflow")[0]["url"]
    dq = links(adaptive, "Data Quality")[0]
    assert dq["targetBlank"] is False
    assert dq["url"].startswith("/d/bioetl-dq-v2/4-data-quality?")
    for field in ("run_id", "pipeline", "workflow_scope", "run_type"):
        assert "${__data.fields." + field + ":percentencode}" in dq["url"]
    assert "${__url_time_range}" in dq["url"]


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
            assert {
                k: v for k, v in before["gridPos"].items() if k not in {"x", "w"}
            } == {k: v for k, v in after["gridPos"].items() if k not in {"x", "w"}}
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
    # The first incident answer uses the same CURRENT clock as its alert list.
    ranked = after[2010]
    ranked_view = ranked["options"]["currentView"]
    assert ranked_view["queries"] == before[2010]["targets"]
    assert ranked_view["transformations"] == before[2010]["transformations"]
    assert ranked["targets"] == [] and ranked["transformations"] == []
    assert ranked["fieldConfig"] == before[2010]["fieldConfig"]
    # Both paged tables fit beside each other; Details retains the full frame.
    alerts = after[2005]
    assert ranked["options"]["viewMode"] == "current"
    assert "Event freshness" in ranked_view["compactFields"]
    assert alerts["options"]["currentView"]["compactFields"] == [
        "Severity",
        "Alert",
        "Pipeline",
        "State",
    ]
    # Fixed-window diagnostics are CURRENT even beside historical charts. A
    # historical dashboard date must not hide today's telemetry WARN as UNKNOWN.
    for panel_id in (893, 907, 2460, 22011):
        assert "CURRENT" in before[panel_id]["description"][:45]
        current = after[panel_id]["options"]["currentView"]
        assert current["queries"] == before[panel_id]["targets"]
        assert current["transformations"] == before[panel_id].get("transformations", [])
        assert after[panel_id]["targets"] == []
        assert after[panel_id]["fieldConfig"] == before[panel_id]["fieldConfig"]
    # The true rate chart keeps its historical end and selected rate interval.
    assert "currentView" not in after[8807].get("options", {})
    assert after[8807]["targets"] == before[8807]["targets"]
    stage_view = after[2460]["options"]["currentView"]
    assert all(item["id"] != "limit" for item in stage_view["transformations"])
    assert stage_view["options"]["footer"]["enablePagination"] is True
    assert stage_view["options"]["enablePagination"] is True
    assert ranked["gridPos"]["x"] + ranked["gridPos"]["w"] <= alerts["gridPos"]["x"]
    for panel in (ranked, alerts):
        assert panel["gridPos"]["y"] + panel["gridPos"]["h"] <= 15
