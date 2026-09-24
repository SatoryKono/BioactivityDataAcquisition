"""Regression contracts for global incident context and evidence navigation."""

import json
from pathlib import Path


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
        assert "$pipeline" not in panel["targets"][0]["expr"]
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
        assert '"provider","^$"' in panels[pid]["targets"][0]["expr"]
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
