"""Regression contracts for global incident context and evidence navigation."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _panels():
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-incident-v1.json").read_text()
    )

    def walk(items):
        for item in items:
            yield item
            yield from walk(item.get("panels", []))

    return {panel["id"]: panel for panel in walk(dashboard["panels"])}


def _properties(panel, name):
    return {
        prop["id"]: prop["value"]
        for rule in panel["fieldConfig"]["overrides"]
        if rule["matcher"] == {"id": "byName", "options": name}
        for prop in rule["properties"]
    }


def test_global_context_and_row_action_do_not_inherit_selected_history():
    panels = _panels()
    assert (
        "independent of selected Pipeline, Provider and Run ID"
        in panels[9400]["options"]["content"]
    )
    for pid in (2010, 22010):
        panel = panels[pid]
        source = panel if pid == 2010 else panels[panel["targets"][0]["panelId"]]
        assert "$pipeline" not in source["targets"][0]["expr"]
        if pid == 22010:
            assert "expr" not in panel["targets"][0]
        url = _properties(panel, "Action")["links"][0]["url"]
        assert "var-run_id=-" in url
        assert "var-workflow=$__all" in url
        assert "__data.fields.route_pipeline:percentencode" in url
        assert "${pipeline" not in url and "${run_id" not in url


def test_verification_is_presentation_only_and_not_health():
    panels = _panels()
    assert "Rule triggered; cause not confirmed" in panels[2001]["options"]["content"]
    confidence = _properties(panels[2010], "Confidence")
    assert confidence["displayName"] == "Cause verification"
    assert confidence["mappings"][0]["options"]["UNVERIFIED"]["text"] == "Not verified"
    for pid in (2005, 22005):
        source = (
            panels[pid] if pid == 2005 else panels[panels[pid]["targets"][0]["panelId"]]
        )
        assert source["targets"][0]["expr"] == "bioetl_incident_global_alerts"
        rules = Path(
            "grafana/prometheus-rules/bioetl_observability.yml"
        ).read_text(encoding="utf-8")
        assert '"provider","^$"' in rules
        if pid == 22005:
            assert "expr" not in panels[pid]["targets"][0]
        assert _properties(panels[pid], "provider")["noValue"] == "Not provided"
    assert panels[9401]["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"


def test_measurements_keep_stage_and_do_not_claim_event_freshness():
    panel = _panels()[22011]
    for target in panel["targets"]:
        assert "max by (pipeline, run_type, stage)" in target["expr"]
        assert "observed/published timestamps not provided" in target["expr"]
        assert '"observation_time","Not provided"' in target["expr"]
    assert "max_over_time(bioetl_stage_lag_seconds[15m])" in panel["targets"][0]["expr"]
    assert ">= 300" in panel["targets"][0]["expr"]
    assert "> 0" in panel["targets"][0]["expr"]


def test_triage_points_at_the_fleet_row_on_this_page() -> None:
    panels = _panels()
    content = panels[2001]["options"]["content"]
    assert "Rule triggered; cause not confirmed" in content
    assert "Pipeline fleet and range on this page" in content
    assert "Open Pipeline Diagnostics" not in content
    assert "Fleet blockers" in panels[2001]["description"]
    for panel_id in (2020, 32010, 32005, 9700):
        assert panels[panel_id]["description"]


def test_fleet_children_do_not_overlap() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-incident-v1.json").read_text(encoding="utf-8")
    )
    row = next(panel for panel in dashboard["panels"] if panel.get("id") == 8808)
    boxes = []
    for child in row["panels"]:
        grid = child["gridPos"]
        boxes.append(
            (
                child.get("id"),
                grid["x"],
                grid["y"],
                grid["x"] + grid["w"],
                grid["y"] + grid["h"],
            )
        )
    for index, left in enumerate(boxes):
        for right in boxes[index + 1 :]:
            overlaps = not (
                left[3] <= right[1]
                or right[3] <= left[1]
                or left[4] <= right[2]
                or right[4] <= left[2]
            )
            assert not overlaps, f"{left[0]} overlaps {right[0]}"
