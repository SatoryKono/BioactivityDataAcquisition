"""Regression coverage for visual follow-ups #10614 through #10624."""

from copy import deepcopy
import json
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


def test_short_run_link_uses_full_hidden_identity():
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
    assert {"run_id", "run_label"} <= set(fields)
    override = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"] == {"id": "byName", "options": "Run"}
    )
    links = next(
        prop["value"] for prop in override["properties"] if prop["id"] == "links"
    )
    assert all(
        "var-run_id=${__data.fields.run_id:percentencode}" in link["url"]
        for link in links
    )
    assert all("${__value.raw}" not in link["url"] for link in links)
