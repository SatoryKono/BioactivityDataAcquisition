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
    assert panel["fieldConfig"]["defaults"]["noValue"] == (
        "No rejected records for current filters. Use the reason/field summaries "
        "above to widen filters or select a payload_hash when rows exist; backend "
        "and scope must be confirmed before treating this as zero rows."
    )
    assert "Backend/query failure copy:" in panel["description"]


def test_record_selection_guidance_is_visible_before_empty_record_panels() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )

    panel = next((p for p in dashboard["panels"] if p.get("id") == 15), None)

    assert panel is not None
    assert panel["title"] == "Review: Record Selection Empty State"
    assert panel.get("type") == "text"
    assert panel.get("gridPos", {}).get("y") == 35
    content = str(panel.get("options", {}).get("content", "")).lower()
    assert "payload_hash" in content
    assert "widen filters" in content
    assert "quarantine explorer health" in content


def test_trend_empty_state_guidance_is_visible_before_forensic_tables() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )

    panel = next((p for p in dashboard["panels"] if p.get("id") == 16), None)

    assert panel is not None
    assert panel["title"] == "Review: Trend Empty State"
    assert panel.get("type") == "text"
    assert panel.get("gridPos", {}).get("y") == 27
    content = str(panel.get("options", {}).get("content", "")).lower()
    assert "active filters returned no matching reject samples" in content
    assert "datasource failure" in content


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
    assert "filtered_out_silver is a legacy alias" in content
    assert "silver structural rejects only" in content
    assert "gold contract and semantic rejects are not shown here" in content
    assert (
        "gold contract and semantic rejects are intentionally excluded" in description
    )


def test_filtered_records_table_documents_legacy_silver_alias_scope() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )

    panel = next((p for p in dashboard["panels"] if p.get("id") == 8), None)

    assert panel is not None
    description = str(panel.get("description", "")).lower()
    assert "silver structural filtered_out_silver records" in description
    assert "filtered_out_silver is a legacy alias" in description
    assert "gold contract and semantic rejects are not included" in description


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
