"""Regression guards for request duplication and categorical status priority."""

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana._gr_db_corrections import apply_corrections

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def _dashboard(uid):
    return json.loads((ROOT / "grafana/dashboards" / f"{uid}.json").read_text())


def test_retention_does_not_repeat_hash_verification_for_header():
    dashboard = _dashboard("bioetl-control-plane-v1")
    apply_corrections(dashboard)
    panel = next(p for p in dashboard["panels"] if p["id"] == 9416)
    assert [target["refId"] for target in panel["targets"]] == ["A"]
    assert panel["targets"][0]["root_selector"] == "rows"
    assert "error_as_row=1" in panel["targets"][0]["url"]
    assert not any(
        t.get("options", {}).get("configRefId") == "B" for t in panel["transformations"]
    )


def test_provider_status_uses_filtered_vectors_in_severity_order():
    dashboard = _dashboard("bioetl-provider-health-v2")
    apply_corrections(dashboard)
    ids = {panel.get("id") for panel in dashboard["panels"]}
    assert 9401 not in ids
    assert 9101 not in ids
    evidence = next(
        panel
        for panel in dashboard["panels"]
        if panel.get("id") == 9462
        for panel in panel.get("panels", [])
        if panel.get("id") == 9460
    )
    assert "selected-run-status" in evidence["targets"][0]["url"]
    assert evidence["targets"][0]["root_selector"] == "provider_checks"
    assert all(item.get("id") != "limit" for item in evidence["transformations"])
    organize = next(
        item for item in evidence["transformations"] if item.get("id") == "organize"
    )
    assert organize["options"]["renameByName"] == {
        "provider": "Provider",
        "check_result": "Check result",
        "evidence": "Evidence",
        "observed_at": "Observed at",
    }
