"""Saved-run evidence owners and legacy correction compatibility after cutover."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana._gr_db_corrections import (
    _correct_runtime,
    _panels,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def _dashboard(uid: str) -> dict:
    return json.loads(
        (ROOT / f"grafana/dashboards/{uid}.json").read_text(encoding="utf-8")
    )


def _legacy_fixture() -> dict:
    """Minimal compatibility input; retired dashboards are never provisioned."""
    return {
        "uid": "bioetl-runtime",
        "panels": [
            {
                "id": 9451,
                "targets": [{"refId": "A", "url": "/saved-evidence"}],
                "fieldConfig": {"defaults": {}, "overrides": []},
            },
            {"id": 9403, "fieldConfig": {"defaults": {}, "overrides": []}},
        ],
    }


def test_domain_reason_labels_preserve_unknown_codes_and_queries() -> None:
    payload = _legacy_fixture()
    panels = {p["id"]: p for p in _panels(payload["panels"])}
    targets = deepcopy(panels[9451]["targets"])
    _correct_runtime(payload["uid"], panels)
    mapping = next(
        prop["value"]
        for override in panels[9451]["fieldConfig"]["overrides"]
        if override["matcher"] == {"id": "byName", "options": "Reason"}
        for prop in override["properties"]
        if prop["id"] == "mappings"
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
    payload = _legacy_fixture()
    panels = {p["id"]: p for p in _panels(payload["panels"])}
    _correct_runtime(payload["uid"], panels)
    links = panels[9403]["fieldConfig"]["defaults"]["links"]
    assert len(links) == 1
    assert (
        "pipeline-run-report-artifact?pipeline=${pipeline:percentencode}"
        in links[0]["url"]
    )
    assert "run_id=${run_id:percentencode}" in links[0]["url"]
    untouched = deepcopy(payload)
    _correct_runtime("another-dashboard", panels)
    assert payload == untouched


def test_saved_reason_labels_and_accounting_use_current_owners() -> None:
    overview = {p["id"]: p for p in _panels(_dashboard("bioetl-overview-v2")["panels"])}
    reason = next(
        override
        for override in overview[9002]["fieldConfig"]["overrides"]
        if override["matcher"] == {"id": "byName", "options": "Reason"}
    )
    mappings = next(
        prop["value"] for prop in reason["properties"] if prop["id"] == "mappings"
    )
    labels = {
        key: value["text"]
        for mapping in mappings
        if mapping["type"] == "value"
        for key, value in mapping["options"].items()
    }
    assert labels["execution_success"] == "Processing completed"
    assert labels["standalone_pipeline"] == "Standalone pipeline"
    assert "new_failure_code" not in labels
    assert "selected-run-status" in overview[9002]["targets"][0]["url"]
    dq = {p["id"]: p for p in _panels(_dashboard("bioetl-dq-v2")["panels"])}
    targets = dq[9403]["targets"]
    assert any("processed-records?" in target["url"] for target in targets)
    assert any("pipeline-run-report?" in target["url"] for target in targets)
    for target in targets:
        assert "pipeline=${pipeline" in target["url"]
        assert "run_id=${run_id" in target["url"]
    assert "SELECTED RUN" in dq[9403]["description"]
    assert "CURRENT" not in dq[9403]["description"]


@pytest.mark.parametrize(
    "uid", ["bioetl-overview-v2", "bioetl-dq-v2", "bioetl-incident-v1"]
)
def test_panel_guide_covers_every_shipped_panel(uid: str) -> None:
    guide = (ROOT / f"docs/03-guides/dashboards/panels/{uid}-panels.md").read_text(
        encoding="utf-8"
    )
    for panel in _panels(_dashboard(uid)["panels"]):
        if panel["id"] == 1000:
            continue  # Shared navigation is documented by the nav-bus contract.
        assert str(panel["id"]) in guide
    assert "bioetl_runtime_current_status_trusted" not in guide
