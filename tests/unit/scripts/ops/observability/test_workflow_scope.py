"""Regression boundaries for selected workflow and saved-run dashboard evidence."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.ops.observability.grafana._workflow_scope import apply_workflow_scope

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("uid", ["bioetl-overview-v2", "bioetl-incident-v1"])
def test_scope_is_idempotent_and_does_not_rewrite_saved_run(uid):
    payload = json.loads(Path(f"grafana/dashboards/{uid}.json").read_text())
    saved = deepcopy(next(p for p in payload["panels"] if p["id"] == 9450))
    apply_workflow_scope(payload)
    first = deepcopy(payload)
    apply_workflow_scope(payload)
    assert payload == first
    assert next(p for p in payload["panels"] if p["id"] == 9450) == saved
    card = next(
        p
        for p in payload["panels"]
        if p.get("title") in {"Monitor Scope Health", "Monitor Scope Status"}
    )
    expr = card["targets"][0]["expr"]
    assert 'workflow=~"$workflow"' in expr
    assert "$run_id" not in expr
    assert (
        card["fieldConfig"]["defaults"]["mappings"][0]["options"]["3"]["text"] == "CRIT"
    )


def test_action_navigation_uses_responsible_workflow_even_when_selector_is_all():
    payload = json.loads(Path("grafana/dashboards/bioetl-overview-v2.json").read_text())
    panel = next(p for p in payload["panels"] if p["id"] == 215)
    links = [
        link
        for override in panel["fieldConfig"]["overrides"]
        for prop in override["properties"]
        if prop["id"] == "links"
        for link in prop["value"]
        if "${__data.fields.action_scope" in link.get("url", "")
    ]
    assert links
    assert all(
        "var-workflow=${__data.fields.Workflow:percentencode}" in link["url"]
        for link in links
    )
    assert all("${run_id:queryparam}" in link["url"] for link in links)
