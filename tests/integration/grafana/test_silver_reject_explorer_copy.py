"""Integration copy/assert checks for Silver Reject Explorer dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_filtered_records_table_has_explicit_empty_and_failure_copy() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )

    panel = next((p for p in dashboard["panels"] if p.get("id") == 8), None)

    assert panel is not None, (
        "Silver Reject Explorer panel id=8 is missing; available panels: "
        + ", ".join(f"{p.get('id')}:{p.get('title')}" for p in dashboard["panels"])
    )
    assert panel["title"] == "Inspect Filtered Records Table"
    assert (
        panel["fieldConfig"]["defaults"]["noValue"]
        == "No rejected records for current filters."
    )
    assert "Backend/query failure copy:" in panel["description"]
