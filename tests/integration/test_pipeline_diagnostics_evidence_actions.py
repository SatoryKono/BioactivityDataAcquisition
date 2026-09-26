"""Saved-run navigation and explanation regressions for Pipeline Diagnostics."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from scripts.ops.observability.grafana._gr_db_corrections import (
    _correct_runtime,
    _panels,
)

ROOT = Path(__file__).resolve().parents[2]


def _dashboard() -> dict:
    return json.loads((ROOT / "grafana/dashboards/bioetl-runtime.json").read_text())


def test_domain_reason_labels_preserve_unknown_codes_and_queries() -> None:
    payload = _dashboard()
    panels = {p["id"]: p for p in _panels(payload["panels"])}
    targets = deepcopy(panels[9451]["targets"])
    _correct_runtime(payload["uid"], panels)
    mapping = next(
        prop["value"]
        for override in panels[9451]["fieldConfig"]["overrides"]
        if override["matcher"] == {"id": "byName", "options": "Reason"}
        for prop in override["properties"] if prop["id"] == "mappings"
    )
    assert all(item["type"] == "value" for item in mapping)
    labels = {k: v["text"] for item in mapping for k, v in item["options"].items()}
    assert labels["execution_success"] == "Processing completed"
    assert "no workflow applies" in labels["standalone_pipeline"]
    assert "new_failure_code" not in labels
    assert panels[9451]["targets"] == targets
    before = deepcopy(payload)
    _correct_runtime(payload["uid"], panels)
    assert payload == before


def test_accounting_links_reference_exact_saved_run_only() -> None:
    payload = _dashboard()
    panels = {p["id"]: p for p in _panels(payload["panels"])}
    links = panels[9403]["fieldConfig"]["defaults"]["links"]
    assert len(links) == 1
    assert "pipeline-run-report-artifact?pipeline=${pipeline:percentencode}" in links[0]["url"]
    assert "run_id=${run_id:percentencode}" in links[0]["url"]
    untouched = deepcopy(payload)
    _correct_runtime("another-dashboard", panels)
    assert payload == untouched


def test_panel_guide_covers_every_shipped_panel() -> None:
    guide = (ROOT / "docs/03-guides/dashboards/panels/bioetl-runtime-panels.md").read_text()
    for panel in _panels(_dashboard()["panels"]):
        assert str(panel["id"]) in guide
    assert "bioetl_runtime_current_status_trusted" not in guide
    assert "Not recorded" in guide
