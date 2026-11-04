"""Regression guards for request duplication and categorical status priority."""

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana._gr_db_corrections import apply_corrections
from tests.integration._grafana_test_support import get_dashboard_panels

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def _dashboard(uid):
    return json.loads(
        (ROOT / "grafana/dashboards" / f"{uid}.json").read_text(encoding="utf-8")
    )


def test_retention_does_not_repeat_hash_verification_for_header():
    dashboard = _dashboard("bioetl-control-plane-v1")
    apply_corrections(dashboard)
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9416)
    assert [target["refId"] for target in panel["targets"]] == ["A"]
    assert panel["targets"][0]["root_selector"] == "rows"
    assert "error_as_row=1" in panel["targets"][0]["url"]
    assert not any(
        t.get("options", {}).get("configRefId") == "B" for t in panel["transformations"]
    )


def test_provider_status_uses_filtered_vectors_in_severity_order():
    """Saved provider check stays categorical and never fabricates a healthy fleet."""
    dashboard = _dashboard("bioetl-overview-v2")
    panel = next(
        item for item in get_dashboard_panels(dashboard) if item.get("id") == 9481
    )
    assert all("expr" not in target for target in panel["targets"])
    assert panel["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"
    description = panel["description"]
    assert "not live fleet health" in description
    assert "QUERY ERROR" in description
    assert "VALID EMPTY" in description
    assert "SELECT RUN" in description
    blob = json.dumps(panel)
    assert "vector(0)" not in blob
    assert not (ROOT / "grafana/dashboards/bioetl-provider-health-v2.json").exists()
