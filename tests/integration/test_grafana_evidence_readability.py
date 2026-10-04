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


def test_overview_paired_tables_have_fixed_rows_and_inspectable_reasons():
    dashboard = json.loads(
        (ROOT / "grafana/dashboards/bioetl-overview-v2.json").read_text(
            encoding="utf-8"
        )
    )
    panels = {p["id"]: p for p in _panels(dashboard["panels"])}
    summary, domains = panels[9603], panels[9002]
    assert summary["gridPos"]["y"] == domains["gridPos"]["y"]
    assert domains["gridPos"]["x"] == 0
    assert summary["gridPos"]["x"] == 15
    assert summary["gridPos"]["w"] == 9
    assert summary["gridPos"]["h"] == 5
    assert domains["gridPos"]["y"] + domains["gridPos"]["h"] == (
        panels[9300]["gridPos"]["y"] + panels[9300]["gridPos"]["h"]
    )
    assert 9301 not in panels
    for panel in (summary, domains):
        assert panel["options"]["cellHeight"] == "sm"
        assert panel["options"]["footer"]["enablePagination"] is False
        custom = panel["fieldConfig"]["defaults"]["custom"]
        assert custom["inspect"] is True
        assert custom["wrapText"] is False
        assert custom["cellOptions"]["wrapText"] is False
        for rule in panel["fieldConfig"]["overrides"]:
            for prop in rule["properties"]:
                if prop["id"] == "custom.wrapText":
                    assert prop["value"] is (rule["matcher"]["options"] == "Reason")
                if prop["id"] == "custom.cellOptions":
                    assert prop["value"]["wrapText"] is (
                        rule["matcher"]["options"] == "Reason"
                    )
    trust = next(
        o
        for o in summary["fieldConfig"]["overrides"]
        if o["matcher"]["options"] == "Trust"
    )
    assert {p["id"]: p["value"] for p in trust["properties"]}["displayName"] == "Trust"


def test_overview_paginates_tracks_without_limiting_evidence():
    dashboard = json.loads(
        (ROOT / "grafana/dashboards/bioetl-incident-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panels = {p["id"]: p for p in _panels(dashboard["panels"])}
    # The unbounded workflow evidence table paginates without discarding rows.
    panel = panels[9701]
    assert panel["options"]["footer"]["enablePagination"] is True
    assert not any(t.get("id") == "limit" for t in panel.get("transformations", []))
    assert panel["fieldConfig"]["defaults"]["custom"]["inspect"] is True


@pytest.mark.parametrize("uid", ["bioetl-overview-v2", "bioetl-dq-v2"])
def test_summary_uses_aggregate_verdict_and_explains_missing_archive(uid):
    dashboard = json.loads(
        (ROOT / f"grafana/dashboards/{uid}.json").read_text(encoding="utf-8")
    )
    panels = {p["id"]: p for p in _panels(dashboard["panels"])}
    summary = next(
        p for p in panels.values() if p.get("title") == "Review Selected Run Status"
    )
    target = summary["targets"][0]
    if uid == "bioetl-overview-v2":
        assert target == {
            "panelId": 9002,
            "refId": "A",
            "withTransforms": False,
            "datasource": {"type": "datasource", "uid": "-- Dashboard --"},
        }
        target = panels[9002]["targets"][0]
        assert "'run_verdict': $s.verdict" in target["root_selector"]
    assert "/selected-run-status?" in target["url"]
    assert "presentation_summary[0]" in target["root_selector"]
    assert "presentation_trust[0]" in target["root_selector"]
    assert "reasons_display" in target["root_selector"]
    views = (summary, panels[9002]) if uid == "bioetl-overview-v2" else (summary,)
    for panel in views:
        fields = next(
            t["options"]["include"]["names"]
            for t in panel["transformations"]
            if t["id"] == "filterFieldsByName"
        )
        if panel is summary and uid == "bioetl-overview-v2":
            assert "run_verdict" not in fields
        elif panel is not summary and uid == "bioetl-overview-v2":
            assert "status_display" in fields
        else:
            assert "verdict" in fields
        assert (
            "run_reason"
            if panel is summary and uid == "bioetl-overview-v2"
            else "reason_display"
        ) in fields
        assert "evidence_completeness" not in fields
        reason = next(
            o
            for o in panel["fieldConfig"]["overrides"]
            if o["matcher"]["options"] == "Reason"
        )
        props = {p["id"]: p["value"] for p in reason["properties"]}
        assert props["custom.cellOptions"]["wrapText"] is True
        if uid == "bioetl-overview-v2":
            assert props["custom.inspect"] is True
            assert panel["options"]["cellHeight"] == "sm"
            assert panel["options"]["footer"]["enablePagination"] is False
        assert (
            props["mappings"][0]["options"]["Archive missing"]["text"]
            == "No verified archive"
        )


def test_provider_first_window_preserves_full_fleet_with_pagination():
    dashboard = json.loads(
        (ROOT / "grafana/dashboards/bioetl-overview-v2.json").read_text(
            encoding="utf-8"
        )
    )
    panels = {p["id"]: p for p in _panels(dashboard["panels"])}
    provider = panels[9480]
    assert provider["gridPos"]["y"] >= 18
    assert provider["options"]["footer"]["enablePagination"] is True
    assert not any(t.get("id") == "limit" for t in provider["transformations"])
    assert all("run_id=${run_id}" in t["url"] for t in provider["targets"])
    assert all("expr" not in t for t in provider["targets"])
    assert "not live fleet health" in panels[9481]["description"]


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
    assert "run_id" in fields and "run_label" in fields
    rules = {
        o["matcher"]["options"]: {p["id"]: p["value"] for p in o["properties"]}
        for o in panel["fieldConfig"]["overrides"]
    }
    links = rules["Run ID"]["links"]
    assert len(links) == 2
    assert "var-run_id=${__data.fields.run_id:percentencode}" in links[0]["url"]
    assert links[1]["url"] == "${__data.fields.report_url:raw}"
    assert rules["Run ID"]["custom.inspect"] is True
    for field in ("Overview", "Saved Evidence", "Data Quality", "Replay Readiness"):
        assert all(
            "var-run_id=${__data.fields.run_id:percentencode}" in link["url"]
            for link in rules[field]["links"]
        )
    assert "viewPanel=9418" in rules["Saved Evidence"]["links"][0]["url"]


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
