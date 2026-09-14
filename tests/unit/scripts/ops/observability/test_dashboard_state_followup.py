"""Regression coverage for the state-follow-up migration and data loss risks."""

import copy
import json

from scripts.ops.observability.grafana.apply_state_followup import (
    DASH,
    apply_dashboard,
    walk,
)


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
