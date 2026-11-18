"""Regression contracts for global incident context and evidence navigation."""

import json
import re
from pathlib import Path

import pytest
import yaml

# Grafana 12 / scenes VARIABLE_REGEX. An unknown name is returned unchanged.
_GRAFANA_VARIABLE = re.compile(
    r"\$(\w+)|\[\[(\w+?)(?::(\w+))?\]\]|\$\{(\w+)(?:\.([^:^\}]+))?(?::([^\}]+))?\}"
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
def test_missing_sample_mapping_and_pagination_survive_both_profiles(profile):
    dashboard = json.loads(
        Path(f"grafana/{profile}/bioetl-incident-v1.json").read_text(encoding="utf-8")
    )

    def walk(items):
        return [
            panel for item in items for panel in [item, *walk(item.get("panels", []))]
        ]

    panels = {p["id"]: p for p in walk(dashboard["panels"])}
    for panel_id in (8804, 136, 104, 101, 102):
        defaults = panels[panel_id]["fieldConfig"]["defaults"]
        assert defaults["noValue"] == "UNKNOWN · no samples"
        special = [
            m
            for m in defaults["mappings"]
            if m["type"] == "special" and m["options"]["match"] == "null"
        ]
        assert special and all(
            m["options"]["result"]["text"] == "UNKNOWN" for m in special
        )
        # The qualified foreground palette resolves neutral gray to theme text.
        assert all(m["options"]["result"]["color"] in {"gray", "text"} for m in special)
    for panel_id in (2005, 2010):
        panel = panels[panel_id]
        options = (
            panel["options"].get("currentView", {}).get("options", panel["options"])
        )
        transforms = (
            panel["options"]
            .get("currentView", {})
            .get("transformations", panel.get("transformations", []))
        )
        assert options["enablePagination"] is True
        assert options["footer"]["enablePagination"] is True
        assert all(transform["id"] != "limit" for transform in transforms)


def _panels():
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-incident-v1.json").read_text(encoding="utf-8")
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
        in panels[2005]["description"]
    )
    for pid in (2010, 22010):
        panel = panels[pid]
        source = panels[2010] if pid == 22010 else panel
        assert "$pipeline" not in source["targets"][0]["expr"]
        if pid == 22010:
            assert panel["targets"][0]["panelId"] == 2010
            assert panel["targets"][0]["withTransforms"] is False
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
        rule_payload = yaml.safe_load(
            Path("grafana/prometheus-rules/bioetl_observability.yml").read_text(
                encoding="utf-8"
            )
        )
        global_rule = next(
            rule
            for group in rule_payload["groups"]
            for rule in group["rules"]
            if rule.get("record") == "bioetl_incident_global_alerts"
        )

        def normalize(expr: str) -> str:
            return "".join(expr.split())

        assert normalize(source["targets"][0]["expr"]) in {
            "bioetl_incident_global_alerts",
            normalize(global_rule["expr"]),
        }
        rules = Path("grafana/prometheus-rules/bioetl_observability.yml").read_text(
            encoding="utf-8"
        )
        assert '"provider","^$"' in rules
        if pid == 22005:
            assert "expr" not in panels[pid]["targets"][0]
        assert _properties(panels[pid], "provider")["noValue"] == "Not provided"
        assert "pipeline-failure-critical" in source["targets"][0]["expr"]
        assert "pipeline-failure-dq" in source["targets"][0]["expr"]
        assert _properties(panels[pid], "owner")["noValue"] == "See runbook"
        assert _properties(panels[pid], "next_step")["displayName"] == "Next step"
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


def _grafana_leave_unknown(target: str) -> str:
    """Grafana 12 leaves a `$name` that is not a dashboard variable unchanged."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2) or match.group(4)
        if name != "1":
            raise AssertionError(name)
        return match.group(0)

    return _GRAFANA_VARIABLE.sub(replace, target)


def _prometheus_expand(template: str, groups: dict[int, str]) -> str:
    """Go regexp Expand: `$$` is a literal dollar, `$1` is capture group 1."""
    out: list[str] = []
    index = 0
    while index < len(template):
        if template[index] == "$" and index + 1 < len(template):
            nxt = template[index + 1]
            if nxt == "$":
                out.append("$")
                index += 2
                continue
            if nxt.isdigit():
                out.append(groups[int(nxt)])
                index += 2
                continue
        out.append(template[index])
        index += 1
    return "".join(out)


def _ranked_suspect_exprs(dashboard: dict) -> list[str]:
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            expr = node.get("expr")
            if isinstance(expr, str) and "bioetl_incident_ranked_evidence" in expr:
                found.append(expr)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(dashboard["panels"])
    return found


def test_ranked_suspect_capture_reaches_prometheus() -> None:
    from scripts.ops.observability.grafana._incident_explanations import (
        _stamp_ranked_suspect_expr,
    )

    stamped: dict = {"targets": [{}]}
    _stamp_ranked_suspect_expr(stamped, summary=True)
    generated = stamped["targets"][0]["expr"]
    assert '"object","$1","object","(.*) / $"' in generated
    assert "$$1" not in generated

    for profile in ("dashboards", "dashboards-adaptive"):
        dashboard = json.loads(
            Path(f"grafana/{profile}/bioetl-incident-v1.json").read_text(
                encoding="utf-8"
            )
        )
        assert all(item["name"] != "1" for item in dashboard["templating"]["list"])
        exprs = _ranked_suspect_exprs(dashboard)
        assert exprs
        assert all(expr == generated for expr in exprs)

    sent = _grafana_leave_unknown(generated)
    assert '"object","$1","object"' in sent
    match = re.fullmatch(r"(.*) / ", "chembl_activity / ")
    assert match is not None
    assert _prometheus_expand("$1", {1: match.group(1)}) == "chembl_activity"
    assert (
        _prometheus_expand(_grafana_leave_unknown("$$1"), {1: "chembl_activity"})
        == "$1"
    )
