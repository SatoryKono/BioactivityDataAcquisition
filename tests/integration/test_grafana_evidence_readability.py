"""Regression coverage for visual follow-ups #10614 through #10624."""

from copy import deepcopy
import json
import re
from pathlib import Path

import pytest

from scripts.ops.observability.grafana._evidence_readability import (
    apply_evidence_readability,
)

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def _panels(items):
    for panel in items:
        yield panel
        yield from _panels(panel.get("panels", []))


@pytest.mark.parametrize(
    "path", sorted((ROOT / "grafana/dashboards").glob("*.json")), ids=lambda p: p.stem
)
def test_readability_pass_is_idempotent_and_preserves_metric_evidence(path):
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    before = {
        p["id"]: [t["expr"] for t in p.get("targets", []) if "expr" in t]
        for p in _panels(dashboard["panels"])
    }
    apply_evidence_readability(dashboard)
    once = deepcopy(dashboard)
    apply_evidence_readability(dashboard)
    assert dashboard == once
    after = {
        p["id"]: [t["expr"] for t in p.get("targets", []) if "expr" in t]
        for p in _panels(dashboard["panels"])
    }
    assert before == after, "Layout must not remove panels or alter PromQL evidence"


def test_overview_paginates_tracks_without_limiting_evidence():
    dashboard = json.loads(
        (ROOT / "grafana/dashboards/bioetl-overview-v2.json").read_text(
            encoding="utf-8"
        )
    )
    panels = {p["id"]: p for p in _panels(dashboard["panels"])}
    for panel_id in (9018, 9019, 9020):
        panel = panels[panel_id]
        assert panel["options"]["perPage"] == 8
        assert "pageSize" not in panel["options"]
        assert panel["gridPos"]["w"] == 24
        assert not any(t.get("id") == "limit" for t in panel.get("transformations", []))


def test_overview_summary_uses_aggregate_verdict_and_explains_missing_archive():
    dashboard = json.loads(
        (ROOT / "grafana/dashboards/bioetl-overview-v2.json").read_text(
            encoding="utf-8"
        )
    )
    panels = {p["id"]: p for p in _panels(dashboard["panels"])}
    summary = next(
        p for p in panels.values() if p.get("title") == "Review Selected Run Status"
    )
    target = summary["targets"][0]
    assert "panelId" not in target, (
        "First domain OK must not replace aggregate INCOMPLETE"
    )
    assert "/selected-run-status?" in target["url"]
    assert "presentation_summary[0]" in target["root_selector"]
    assert "presentation_trust[0].reasons_display" in target["root_selector"]
    for panel in (summary, panels[9002]):
        fields = next(
            t["options"]["include"]["names"]
            for t in panel["transformations"]
            if t["id"] == "filterFieldsByName"
        )
        assert "verdict" in fields
        assert "reason_display" in fields
        assert "evidence_completeness" not in fields
        reason = next(
            o
            for o in panel["fieldConfig"]["overrides"]
            if o["matcher"]["options"] == "Reason"
        )
        props = {p["id"]: p["value"] for p in reason["properties"]}
        assert props["custom.cellOptions"]["wrapText"] is True
        assert (
            props["mappings"][0]["options"]["Archive missing"]["text"]
            == "No verified archive"
        )


def test_run_cell_inspection_and_links_use_full_identity():
    dashboard = json.loads(
        (ROOT / "grafana/dashboards/bioetl-run-explorer-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next(p for p in _panels(dashboard["panels"]) if p["id"] == 3010)
    fields = next(
        t["options"]["include"]["names"]
        for t in panel["transformations"]
        if t["id"] == "filterFieldsByName"
    )
    assert "run_id" in fields
    assert "run_label" not in fields
    override = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"] == {"id": "byName", "options": "Run"}
    )
    links = next(
        prop["value"] for prop in override["properties"] if prop["id"] == "links"
    )
    assert all(
        "var-run_id=${__data.fields.Run:percentencode}" in link["url"] for link in links
    )
    assert all("${__value.raw}" not in link["url"] for link in links)
    assert {prop["id"]: prop["value"] for prop in override["properties"]}[
        "custom.inspect"
    ] is True
    organize = next(
        t["options"] for t in panel["transformations"] if t["id"] == "organize"
    )
    assert organize["renameByName"]["run_id"] == "Run"
    rules = {
        o["matcher"]["options"]: {p["id"]: p["value"] for p in o["properties"]}
        for o in panel["fieldConfig"]["overrides"]
    }
    assert rules["Workflow"]["custom.hidden"] is False
    for field in ("Pipeline", "Workflow", "Run"):
        assert "custom.width" not in rules[field]
    for field in ("Started", "Duration", "Processing", "Trust", "Report"):
        assert isinstance(rules[field]["custom.width"], int)


@pytest.mark.parametrize("stage", ["bronze", "silver", "gold", "quarantined"])
def test_stage_colors_match_bare_and_pipeline_qualified_names(stage):
    """Grafana stringToJsRegex anchors delimiter-free patterns on both ends."""
    from scripts.ops.observability.grafana._evidence_readability import _stage_colors

    panel = {"fieldConfig": {"overrides": []}}
    _stage_colors(panel)
    colors = []
    for name in (stage, f"chembl_molecule / {stage}"):
        matched = [
            rule
            for rule in panel["fieldConfig"]["overrides"]
            if re.fullmatch(rule["matcher"]["options"], name)
        ]
        assert len(matched) == 1
        colors.append(matched[0]["properties"])
    assert colors[0] == colors[1]
    assert not any(
        re.fullmatch(rule["matcher"]["options"], "bronze_partitioned / passed")
        for rule in panel["fieldConfig"]["overrides"]
    )
