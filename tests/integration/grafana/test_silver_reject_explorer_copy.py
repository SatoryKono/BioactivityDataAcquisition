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


def test_scope_banner_explains_origin_dashboard_ownership() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )

    panel = next((p for p in dashboard["panels"] if p.get("id") == 1), None)

    assert panel is not None
    content = str(panel.get("options", {}).get("content", "")).lower()
    description = str(panel.get("description", "")).lower()
    assert "origin dashboards own shared workflow/run_id shell context" in content
    assert "never owns shared workflow or run_id selectors" in content
    assert "stays pipeline/run_type forensic" in description


def test_first_action_copy_keeps_zero_result_and_unknown_states_distinct() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )

    panel = next((p for p in dashboard["panels"] if p.get("id") == 10), None)

    assert panel is not None
    content = str(panel.get("options", {}).get("content", "")).lower()
    description = str(panel.get("description", "")).lower()
    assert "zero-reject workflow run is an intentional empty explorer state" in content
    assert "zero matching rows for the active filters is an empty result" in content
    assert "bronze_records=0 are unknown or error states" in content
    assert "0 vs no data" in description
