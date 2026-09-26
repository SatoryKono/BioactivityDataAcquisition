"""Regression guards for request duplication and categorical status priority."""

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana._gr_db_corrections import apply_corrections

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def _dashboard(uid):
    return json.loads(
        (ROOT / "grafana/dashboards" / f"{uid}.json").read_text(encoding="utf-8")
    )


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
    panel = next(item for item in dashboard["panels"] if item.get("id") == 9401)
    assert panel["targets"][0]["legendFormat"] == "OK"
    assert "count(bioetl_pstatus" in panel["targets"][0]["expr"]
    assert "bool" not in panel["targets"][0]["expr"]
    assert "vector(0)" not in panel["targets"][0]["expr"]
    assert panel["fieldConfig"]["defaults"]["noValue"] == "TELEMETRY MISSING"
    assert "UNKNOWN" in panel["description"]
    fleet = next(item for item in dashboard["panels"] if item.get("id") == 9101)
    assert fleet["title"].startswith("Все провайдеры")
    assert all(
        "Severity Matrix" not in link.get("title", "")
        and "Top Causes" not in link.get("title", "")
        for link in panel["options"].get("dataLinks", [])
    )
