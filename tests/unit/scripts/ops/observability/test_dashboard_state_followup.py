"""Regression coverage for the state-follow-up migration and data loss risks."""

import copy
import json

import pytest

from scripts.ops.observability.grafana._dashboard_state_followup import (
    DASH,
    apply_dashboard,
    walk,
)

pytestmark = pytest.mark.unit


def test_followup_is_idempotent_and_preserves_unique_panel_ids():
    for path in DASH.glob("*.json"):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        apply_dashboard(dashboard)
        once = copy.deepcopy(dashboard)
        apply_dashboard(dashboard)
        assert dashboard == once, path.name
        ids = [p["id"] for p in walk(dashboard["panels"])]
        assert len(ids) == len(set(ids))
        assert "data:text/plain" not in json.dumps(dashboard)


def test_full_evidence_tables_do_not_truncate_ranked_results():
    for filename, pairs in [
        ("bioetl-overview-v2.json", [(215, 20215)]),
        ("bioetl-incident-v1.json", [(2010, 22010), (2005, 22005)]),
    ]:
        dashboard = json.loads((DASH / filename).read_text(encoding="utf-8"))
        apply_dashboard(dashboard)
        panels = {p["id"]: p for p in walk(dashboard["panels"])}
        for summary, full in pairs:
            assert panels[full]["targets"][0]["panelId"] == summary
            assert panels[full]["targets"][0]["withTransforms"] is False
            assert not any(t["id"] == "limit" for t in panels[full]["transformations"])
            assert panels[full]["options"]["footer"]["enablePagination"]


def test_trust_measures_only_reasons_for_multiline_row_height():
    dashboard = json.loads(
        (DASH / "bioetl-control-plane-v1.json").read_text(encoding="utf-8")
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 9418)
    wrapped = [
        o["matcher"]["options"]
        for o in panel["fieldConfig"]["overrides"]
        if any(
            p["id"] == "custom.cellOptions" and p["value"].get("wrapText")
            for p in o["properties"]
        )
    ]
    assert not wrapped
    assert panel["fieldConfig"]["defaults"]["custom"]["cellOptions"]["wrapText"]
