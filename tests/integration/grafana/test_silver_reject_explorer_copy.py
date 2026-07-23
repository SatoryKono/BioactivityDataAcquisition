"""Integration copy/assert checks for Silver Reject Explorer dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Silver Reject Explorer removed 2026-07-23"),
]


def _load_dashboard() -> dict[str, object]:
    return json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )


def _iter_panels(panels: list[object]):
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        yield panel
        nested = panel.get("panels")
        if isinstance(nested, list):
            yield from _iter_panels(nested)


def _panel(dashboard: dict[str, object], panel_id: int) -> dict[str, object]:
    matches = [
        panel
        for panel in _iter_panels(list(dashboard.get("panels", [])))
        if panel.get("id") == panel_id
    ]
    assert len(matches) == 1, (panel_id, len(matches))
    return matches[0]


def test_filtered_records_table_has_explicit_empty_and_failure_copy() -> None:
    panel = _panel(_load_dashboard(), 8)

    assert panel["title"] == "Inspect Filtered Records Table"
    no_value = str(panel["fieldConfig"]["defaults"]["noValue"])
    assert no_value.startswith("VALID EMPTY")
    assert "QUERY/DATASOURCE ERROR" in no_value
    assert "Backend/query failure copy:" in panel["description"]


def test_record_selection_guidance_is_visible_before_empty_record_panels() -> None:
    dashboard = _load_dashboard()
    row = _panel(dashboard, 15)

    assert row["title"] == "Records and selected detail · expand after narrowing"
    assert row.get("type") == "row"
    assert row.get("collapsed") is True
    assert {panel.get("id") for panel in row.get("panels", [])} == {8, 9}
    first_action = str(_panel(dashboard, 10).get("options", {}).get("content", ""))
    assert "expand Trends only for non-zero rejects" in first_action
    assert "Records only after narrowing" in first_action


def test_trend_empty_state_guidance_is_visible_before_forensic_tables() -> None:
    row = _panel(_load_dashboard(), 16)

    assert row["title"] == "Trends · expand when rejects exist"
    assert row.get("type") == "row"
    assert row.get("collapsed") is True
    assert {panel.get("id") for panel in row.get("panels", [])} == {11, 12}


def test_scope_banner_explains_origin_dashboard_ownership() -> None:
    panel = _panel(_load_dashboard(), 1)
    content = str(panel.get("options", {}).get("content", "")).lower()
    description = str(panel.get("description", "")).lower()
    combined = f"{content} {description}"
    assert "origin dashboards own shared workflow/run_id shell context" in combined
    assert "never owns shared workflow or run_id selectors" in combined
    assert "stays pipeline/run_type forensic" in description
    assert "filtered_out_silver is a legacy alias" in combined
    assert "silver structural rejects only" in combined
    assert (
        "gold contract and semantic rejects are intentionally excluded" in description
    )


def test_filtered_records_table_documents_legacy_silver_alias_scope() -> None:
    panel = _panel(_load_dashboard(), 8)
    description = str(panel.get("description", "")).lower()
    assert "silver structural filtered_out_silver records" in description
    assert "filtered_out_silver is a legacy alias" in description
    assert "gold contract and semantic rejects are not included" in description


def test_first_action_copy_keeps_zero_result_and_unknown_states_distinct() -> None:
    panel = _panel(_load_dashboard(), 10)
    content = str(panel.get("options", {}).get("content", "")).lower()
    description = str(panel.get("description", "")).lower()
    assert "valid empty" in content
    assert "telemetry absent" in content
    assert "query error" in content
    assert "datasource error" in content
    assert "0 vs no data" in description
