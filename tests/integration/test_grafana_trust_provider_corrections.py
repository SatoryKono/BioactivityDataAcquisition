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
    panel = next(p for p in dashboard["panels"] if p["id"] == 9401)
    branches = panel["targets"][0]["expr"].split(" or ")
    assert branches == [
        f'max(bioetl_pstatus{{provider=~"$provider"}} == {code})'
        for code in (2, 1, 3, 0)
    ]
    # PromQL comparisons must filter, not emit bool 0/1: the latter would
    # keep the first branch present even when CRIT is absent.
    assert "bool" not in panel["targets"][0]["expr"]
