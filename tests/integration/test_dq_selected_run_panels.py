"""DQ selected-run panel copy contracts (#11569-#11572, #11684-#11686)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.integration._grafana_test_support import load_dashboard

pytestmark = pytest.mark.integration

_DASHBOARD = Path("grafana/dashboards/bioetl-dq-v2.json")

_DQ_REASON_CODES = (
    "execution_success",
    "run_dq_threshold_evaluation",
    "run_preflight_provider_observation",
    "run_gold_schema_validation",
    "run_observation_missing",
    "workflow_success",
    "run_completion_trust_assessment",
)


def _panels_by_id() -> dict[int, dict[str, Any]]:
    dashboard = load_dashboard(_DASHBOARD)
    found: dict[int, dict[str, Any]] = {}

    def walk(panels: Any) -> None:
        for panel in panels or []:
            if isinstance(panel, dict):
                if isinstance(panel.get("id"), int):
                    found[int(panel["id"])] = panel
                walk(panel.get("panels"))

    walk(dashboard.get("panels"))
    return found


def _reason_mappings(panel: dict[str, Any], field: str) -> dict[str, Any]:
    options: dict[str, Any] = {}
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        if (override.get("matcher") or {}).get("options") != field:
            continue
        for prop in override.get("properties") or []:
            if prop.get("id") != "mappings":
                continue
            for mapping in prop.get("value") or []:
                if mapping.get("type") == "value":
                    options.update(mapping.get("options") or {})
    return options


def _display_name(panel: dict[str, Any], field: str) -> str | None:
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        if (override.get("matcher") or {}).get("options") != field:
            continue
        for prop in override.get("properties") or []:
            if prop.get("id") == "displayName":
                return prop.get("value")
    return None


def test_9403_names_bronze_denominator() -> None:
    """#11684: the percentage column names its Bronze denominator."""
    panel = _panels_by_id()[9403]
    assert _display_name(panel, "percentage") == "percentage of Bronze"
    assert _display_name(panel, "percentage A") == "percentage of Bronze"
    description = str(panel.get("description") or "")
    assert "Bronze" in description
    assert "TIME RANGE" not in description


def test_9403_empty_state_points_at_run_explorer() -> None:
    """#11569: one SELECT RUN state, Run Explorer as the target."""
    panel = _panels_by_id()[9403]
    no_value = (
        (panel.get("fieldConfig") or {}).get("defaults", {}).get("noValue")
    )
    assert no_value == (
        "SELECT RUN — no exact Run ID selected. Choose this run in Run Explorer."
    )
    assert "Inspect Recent Runs" not in str(no_value)


def test_9406_names_answer_columns() -> None:
    """#11570: Overall verdict reads as the DQ assessment, Trust never replays."""
    panel = _panels_by_id()[9406]
    description = str(panel.get("description") or "")
    assert "Overall verdict is the data-quality assessment of this Run ID" in description
    assert "Processing is the saved ETL outcome" in description
    assert "does not authorize replay" in description
    assert panel.get("gridPos") == {"h": 5, "w": 24, "x": 0, "y": 5}


def test_9400_visible_scope_names_run_proof() -> None:
    """#11572: the visible banner says a time-range value never proves the run."""
    panel = _panels_by_id()[9400]
    content = str((panel.get("options") or {}).get("content") or "")
    assert "never proves this run" in content
    description = str(panel.get("description") or "")
    assert description.count("never proves this run") == 1


def test_9450_row_names_all_three_tables() -> None:
    """#11572: the collapsed row names stages, domains, and full identity."""
    panel = _panels_by_id()[9450]
    description = str(panel.get("description") or "")
    assert "9460" not in description  # names, not numeric ids
    assert "Inspect Selected Run Stages" in description
    assert "Inspect Selected Run Domains" in description
    assert "Inspect Selected Run Identity" in description


def test_9451_and_9452_descriptions_differ() -> None:
    """#11571: domain verdicts and full identity do not clone the status glossary."""
    panels = _panels_by_id()
    domains = str(panels[9451].get("description") or "")
    identity = str(panels[9452].get("description") or "")
    status = str(panels[9406].get("description") or "")
    assert domains != identity
    assert domains != status
    assert identity != status
    for description in (domains, identity):
        assert description.startswith("SELECTED RUN")
        for token in (
            "INCOMPLETE",
            "SELECT RUN",
            "QUERY ERROR",
            "N/A",
            "VALID EMPTY",
        ):
            assert token in description
    assert "not the page status" in domains
    assert "Inspect Run Identity" in identity


def test_9451_reason_codes_are_operator_readable() -> None:
    """#11686: known domain codes map to operator strings, unknown stay visible."""
    mappings = _reason_mappings(_panels_by_id()[9451], "Reason")
    assert "selection_required" in mappings
    for code in _DQ_REASON_CODES:
        assert code in mappings, f"missing operator mapping for {code!r}"
    assert "mystery_code_from_nowhere" not in mappings


def test_9460_stage_columns_are_ordered_and_readable() -> None:
    """#11685: Stage, Status, Records in/out, Duration, Reason, Source."""
    panel = _panels_by_id()[9460]
    organize = next(
        item
        for item in panel.get("transformations") or []
        if item.get("id") == "organize"
    )
    assert organize["options"]["indexByName"] == {
        "stage_id": 0,
        "state": 1,
        "records_in": 2,
        "records_out": 3,
        "duration_seconds": 4,
        "reason": 5,
        "source": 6,
    }
    assert organize["options"]["renameByName"] == {
        "stage_id": "Stage",
        "state": "Status",
        "records_in": "Records in",
        "records_out": "Records out",
        "duration_seconds": "Duration",
        "reason": "Reason",
        "source": "Source",
    }
    by_name = {
        (override.get("matcher") or {}).get("options"): override
        for override in (panel.get("fieldConfig") or {}).get("overrides") or []
    }
    for field in ("Records in", "Records out"):
        props = {
            prop.get("id"): prop.get("value")
            for prop in by_name[field].get("properties") or []
        }
        assert props.get("noValue") == "", f"{field} unknown must stay empty, not 0"
    duration_props = {
        prop.get("id"): prop.get("value")
        for prop in by_name["Duration"].get("properties") or []
    }
    assert duration_props.get("noValue") != "0"
    reason_mappings = _reason_mappings(panel, "Reason")
    for code in _DQ_REASON_CODES:
        assert code in reason_mappings, f"missing stage mapping for {code!r}"
