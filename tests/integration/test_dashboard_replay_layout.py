"""Replay simplification must retain diagnostics and exact-run evidence scope."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

pytestmark = pytest.mark.integration


def test_replay_layout_preserves_checks_and_identity_scope():
    root = Path(__file__).resolve().parents[2]
    dashboard = json.loads(
        (root / "grafana/dashboards/bioetl-control-plane-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panels = dashboard["panels"]
    pending = list(panels)
    by_id = {}
    while pending:
        panel = pending.pop()
        assert panel["id"] not in by_id
        by_id[panel["id"]] = panel
        pending.extend(panel.get("panels", []))
    assert {9413, 9414, 9415, 9416, 9406, 9422, 9423, 9408} <= by_id.keys()
    assert not (
        {9402, 9403, 9405, 9407, 9409, 9410, 9411, 9417, 9421, 139} & by_id.keys()
    )
    assert by_id[9423] in panels
    assert by_id[9423]["gridPos"]["y"] < by_id[9408]["gridPos"]["y"]
    assert "priority=" not in by_id[9408]["targets"][0]["url"]
    anchors = by_id[9408]["targets"][0]
    assert anchors["parser"] == "backend"
    assert "uql" not in anchors
    assert "present ? 1 : 0" in anchors["root_selector"]
    for panel in by_id.values():
        for target in panel.get("targets", []):
            if panel["id"] in {9422, 9423}:
                assert target["datasource"]["uid"] == "-- Dashboard --"
                assert target["panelId"] == 9418
                assert target["withTransforms"] is False
                target = by_id[9418]["targets"][0]
            assert "run_id=${run_id}" in target["url"]
    assert {p["id"] for p in by_id[9430]["panels"]} == {9414, 9415, 9416}
    assert {p["id"] for p in by_id[9431]["panels"]} == {9413, 9406}


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
def test_identity_evidence_does_not_use_catalog_flags(profile):
    root = Path(__file__).resolve().parents[2]
    dashboard = json.loads(
        (root / "grafana" / profile / "bioetl-control-plane-v1.json").read_text(
            encoding="utf-8"
        )
    )
    pending = list(dashboard["panels"])
    by_id = {}
    while pending:
        panel = pending.pop()
        by_id[panel["id"]] = panel
        pending.extend(panel.get("panels", []))

    for panel_id, view in [(9408, "anchors"), (9406, "checkpoint_compare")]:
        panel = by_id[panel_id]
        query = parse_qs(urlsplit(panel["targets"][0]["url"]).query)
        assert set(query) == {"pipeline", "run_type", "run_id", "view"}
        assert query["run_id"] == ["${run_id}"]
        assert query["view"] == [view]
        assert "Exact Run ID selects evidence" in panel["description"]
        assert (
            "Catalog freshness does not establish evidence freshness"
            in (panel["description"])
        )

    full_report = next(
        link for link in by_id[9408]["links"] if link["title"] == "Full identity report"
    )
    assert parse_qs(urlsplit(full_report["url"]).query) == {
        "pipeline": ["${pipeline:percentencode}"],
        "run_type": ["${run_type:percentencode}"],
        "run_id": ["${run_id:percentencode}"],
        "view": ["copy_values"],
    }


def test_exact_evidence_renderer_removes_only_catalog_parameters():
    from scripts.ops.observability.grafana._replay_layout import (
        _apply_exact_identity_scope,
    )

    catalog = "/ops/control-plane/filter-options?workflow=x&allow_stale=1"
    panel = {
        "description": "Saved anchors.",
        "targets": [
            {
                "url": "/ops/control-plane/identity-evidence?"
                "workflow=x&pipeline=p&run_type=full&run_id=r"
                "&allow_stale=1&view=anchors"
            },
            {"url": catalog},
        ],
    }
    _apply_exact_identity_scope(panel)
    _apply_exact_identity_scope(panel)
    assert panel["targets"][0]["url"] == (
        "/ops/control-plane/identity-evidence?"
        "pipeline=p&run_type=full&run_id=r&view=anchors"
    )
    assert panel["targets"][1]["url"] == catalog
    assert panel["description"].count("Exact Run ID selects evidence") == 1
