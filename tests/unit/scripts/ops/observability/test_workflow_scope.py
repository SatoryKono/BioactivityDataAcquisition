"""Regression boundaries for selected workflow and saved-run dashboard evidence."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from scripts.ops.observability.grafana._workflow_scope import apply_workflow_scope

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DASHBOARDS = _REPO_ROOT / "grafana" / "dashboards"


@pytest.mark.parametrize(
    ("uid", "saved_run_panel_id"),
    [("bioetl-overview-v2", 9603), ("bioetl-incident-v1", 9450)],
)
def test_scope_is_idempotent_and_does_not_rewrite_saved_run(uid, saved_run_panel_id):
    payload = json.loads((_DASHBOARDS / f"{uid}.json").read_text(encoding="utf-8"))
    saved = deepcopy(
        next(p for p in payload["panels"] if p["id"] == saved_run_panel_id)
    )
    apply_workflow_scope(payload)
    first = deepcopy(payload)
    apply_workflow_scope(payload)
    assert payload == first
    assert next(p for p in payload["panels"] if p["id"] == saved_run_panel_id) == saved
    if uid == "bioetl-overview-v2":
        titles = {panel.get("title") for panel in payload["panels"]}
        assert "Monitor Scope Health" not in titles
        assert "Review First Action" not in titles
        return
    card = next(
        p
        for p in payload["panels"]
        if p.get("title") in {"Monitor Scope Health", "Monitor Scope Status"}
    )
    expr = card["targets"][0]["expr"]
    assert 'workflow=~"$workflow"' in expr
    assert "$run_id" not in expr
    assert "topk(1, bioetl_workflow_scope_priority_by_input" in expr
    assert card["targets"][0]["legendFormat"] == "{{workflow}} · {{input}}"
    assert card["options"]["textMode"] == "value_and_name"
    assert "displayName" not in card["fieldConfig"]["defaults"]
    assert "viewPanel=9701" in card["fieldConfig"]["defaults"]["links"][0]["url"]
    assert (
        card["fieldConfig"]["defaults"]["mappings"][0]["options"]["3"]["text"] == "CRIT"
    )


def test_overview_does_not_keep_current_first_action():
    payload = json.loads(
        (_DASHBOARDS / "bioetl-overview-v2.json").read_text(encoding="utf-8")
    )
    assert all(panel.get("id") != 215 for panel in payload["panels"])


def test_workflow_freshness_is_scoped_publication_age_not_saved_run_health():
    payload = json.loads(
        (_DASHBOARDS / "bioetl-incident-v1.json").read_text(encoding="utf-8")
    )
    row = next(p for p in payload["panels"] if p["id"] == 9700)
    panel = row["panels"][0]
    assert "${workflow_evidence_freshness}" in row["title"]
    assert "threshold 24h" in panel["title"]
    queries = {target["refId"]: target["expr"] for target in panel["targets"]}
    assert "time() - " in queries["C"]
    assert "bioetl_workflow_scope_published_seconds" in queries["C"]
    assert queries["E"].endswith("> bool 86400")
    assert "* 86400" in queries["D"]
    for expr in queries.values():
        assert "$run_id" not in expr
        assert 'workflow=~"$workflow"' in expr
        assert 'pipeline=~"$pipeline"' in expr
        assert 'run_type=~"$run_type"' in expr
    variable = next(
        v
        for v in payload["templating"]["list"]
        if v["name"] == "workflow_evidence_freshness"
    )
    assert variable["skipUrlSync"] is True
    assert variable["current"]["value"] == "Not verified"
    state_query = variable["query"]["query"]
    assert "unless on(workflow)" in state_query
    assert '"STALE"' in state_query and '"Not verified"' in state_query
    assert "absent(" in state_query
    overrides = panel["fieldConfig"]["overrides"]
    freshness = next(o for o in overrides if o["matcher"]["options"] == "Freshness")
    props = {p["id"]: p["value"] for p in freshness["properties"]}
    assert props["noValue"] == "Not verified"
    assert props["mappings"][0]["options"]["1"]["text"] == "STALE"
