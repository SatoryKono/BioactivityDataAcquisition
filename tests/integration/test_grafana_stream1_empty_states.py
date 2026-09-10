# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Stream 1 VIS empty-state contracts for provider-health, runtime, and DQ."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


_PROVIDER_HEALTH_DASHBOARD = Path("grafana/dashboards/bioetl-provider-health-v2.json")
_PROVIDER_HEALTH_UID = "bioetl-provider-health-v2"
# #10246: fleet-coverage proof required before any provider-health VALID EMPTY.
_PROVIDER_CAUSE_COVERAGE_GUARD = (
    "(count(max by (provider) (bioetl_provider_current_status)) > bool 0)"
    " * (count(max by (provider) (bioetl_provider_current_cause)) > bool 0)"
    " * absent(max by (provider) (bioetl_provider_current_status) != 0)"
    " * absent(max by (provider) (bioetl_provider_current_status)"
    " unless on(provider) max by (provider) (bioetl_provider_health_status))"
    " * absent(max by (provider, cause) (bioetl_provider_current_cause) > 0)"
)
_PROVIDER_CAUSE_VALID_EMPTY_LABEL = (
    "VALID EMPTY - FLEET coverage proven, no active provider causes"
)
_PROVIDER_CAUSE_UNKNOWN_LABEL = (
    "UNKNOWN - FLEET cause coverage unproven, restore provider telemetry"
)
_PROVIDER_CAUSE_PANEL_IDS = (9103, 9113)
_PROVIDER_SINGLE_STATE_NO_VALUE_PANEL_IDS = (9102, 9103, 9107)


def _provider_health_panels_by_id() -> dict[int, dict[str, object]]:
    dashboard = load_dashboard(_PROVIDER_HEALTH_DASHBOARD)
    return {
        panel["id"]: panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }


def test_provider_health_no_value_copy_confirms_exactly_one_empty_state() -> None:
    """#10246 H1: a provider-health noValue must not offer UNKNOWN *or* VALID EMPTY."""
    panels = _provider_health_panels_by_id()
    for panel_id in _PROVIDER_SINGLE_STATE_NO_VALUE_PANEL_IDS:
        panel = panels.get(panel_id)
        assert panel is not None, f"provider-health panel {panel_id} is missing"
        no_value = panel.get("fieldConfig", {}).get("defaults", {}).get("noValue")
        assert isinstance(no_value, str) and no_value, (
            f"panel {panel_id} must declare a fail-closed noValue"
        )
        assert not ("UNKNOWN" in no_value and "VALID EMPTY" in no_value), (
            f"panel {panel_id} noValue concatenates UNKNOWN and VALID EMPTY as "
            f"alternative explanations: {no_value!r}"
        )
        assert no_value.startswith("UNKNOWN"), (
            f"panel {panel_id} noValue must lead with the confirmed UNKNOWN state: "
            f"{no_value!r}"
        )


def test_provider_health_copy_never_hedges_two_empty_states() -> None:
    """Provider-health noValue/description must confirm one state, not alternatives."""
    from scripts.engineering.qa import check_dashboard_visual_semantics as subject

    errors = [
        error
        for panel in get_dashboard_panels(load_dashboard(_PROVIDER_HEALTH_DASHBOARD))
        for error in subject._empty_state_hedge_errors(
            _PROVIDER_HEALTH_DASHBOARD, panel
        )
    ]
    assert not errors, "hedged provider-health empty-state copy:\n" + "\n".join(errors)


def test_empty_state_hedge_invariant_rejects_the_10246_regression() -> None:
    """The anti-hedge invariant must fail on the exact copy #10246 removed."""
    from scripts.engineering.qa import check_dashboard_visual_semantics as subject

    regression = {
        "title": "Inspect Top Provider Causes",
        "fieldConfig": {
            "defaults": {
                "noValue": (
                    "UNKNOWN \u2014 missing/stale provider telemetry, or VALID EMPTY "
                    "if the fleet has no matching rows."
                )
            }
        },
    }
    assert subject._empty_state_hedge_errors(_PROVIDER_HEALTH_DASHBOARD, regression)

    taxonomy_copy = {
        "title": "Inspect Top Provider Causes",
        "description": "TELEMETRY MISSING is not a zero and not VALID EMPTY.",
        "fieldConfig": {
            "defaults": {"noValue": "UNKNOWN \u2014 cause evidence unavailable"}
        },
    }
    assert not subject._empty_state_hedge_errors(
        _PROVIDER_HEALTH_DASHBOARD, taxonomy_copy
    )


def test_provider_cause_tables_emit_one_fleet_verdict_row() -> None:
    """VALID EMPTY needs the coverage proof; otherwise the fleet row stays UNKNOWN."""
    panels = _provider_health_panels_by_id()
    for panel_id in _PROVIDER_CAUSE_PANEL_IDS:
        panel = panels.get(panel_id)
        assert panel is not None, f"provider-health panel {panel_id} is missing"
        expressions = [
            target["expr"]
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert len(expressions) == 1, (
            f"panel {panel_id} must answer from one instant snapshot"
        )
        expr = expressions[0]

        valid_empty_index = expr.find(_PROVIDER_CAUSE_VALID_EMPTY_LABEL)
        unknown_index = expr.find(_PROVIDER_CAUSE_UNKNOWN_LABEL)
        assert valid_empty_index > 0, (
            f"panel {panel_id} must expose a proven VALID EMPTY fleet row"
        )
        assert unknown_index > valid_empty_index, (
            f"panel {panel_id} must fall back to an UNKNOWN fleet row"
        )
        assert expr.count(_PROVIDER_CAUSE_COVERAGE_GUARD) == 2, (
            f"panel {panel_id} must gate VALID EMPTY on the coverage proof and "
            "exclude it from the UNKNOWN branch"
        )
        # The UNKNOWN branch must subtract the VALID EMPTY branch, so the two
        # fleet verdict rows can never render together.
        assert f"unless ({_PROVIDER_CAUSE_COVERAGE_GUARD})" in expr, (
            f"panel {panel_id} UNKNOWN row must exclude the proven-empty case"
        )
        assert "or vector(0)" not in expr
        assert "unless on (provider)" not in expr


def test_provider_cause_contract_declares_unknown_beside_valid_empty() -> None:
    """Contract must admit the UNKNOWN fleet row that #10246 locked in."""
    contract = yaml.safe_load(
        Path(
            "docs/03-guides/dashboards/contracts/panel-content-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    panels = contract["dashboards"][_PROVIDER_HEALTH_UID]["panels"]
    for panel_id in _PROVIDER_CAUSE_PANEL_IDS:
        record = panels[str(panel_id)]
        assert {"VALID_EMPTY", "UNKNOWN"} <= set(record["state_model"]), (
            f"panel {panel_id} must declare both proven-empty and UNKNOWN states"
        )
        assert record["empty_state_class"] == "telemetry_missing"
    for panel_id in (9102, 9107):
        record = panels[str(panel_id)]
        assert "UNKNOWN" in record["state_model"]
        assert "VALID_EMPTY" not in record["state_model"], (
            f"panel {panel_id} cannot prove VALID EMPTY from its own query"
        )


def _runtime_panels_by_id() -> dict[int, dict]:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    return {
        panel["id"]: panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }


def test_runtime_10251_stage_empty_is_not_valid_empty_in_stage_column() -> None:
    """#10251 P1: empty Stage/Code tables fail closed on the full-width noValue."""
    for panel_id in (241, 256):
        panel = _runtime_panels_by_id()[panel_id]
        expr = panel["targets"][0]["expr"]
        assert "vector(0)" not in expr
        no_value = str(panel.get("fieldConfig", {}).get("defaults", {}).get("noValue"))
        assert no_value.startswith("TELEMETRY MISSING")
        assert "VALID EMPTY" not in json.dumps(panel.get("fieldConfig", {}))


def test_runtime_10251_expectedness_unknown_vs_contract_na() -> None:
    """#10251 P2: missing telemetry is UNKNOWN; N/A is only inapplicable-by-construction."""
    panel = _runtime_panels_by_id()[243]
    no_value = panel.get("fieldConfig", {}).get("defaults", {}).get("noValue")
    assert isinstance(no_value, str) and no_value.startswith("UNKNOWN")
    assert "N/A" not in no_value
    expected_no_value = None
    for override in panel.get("fieldConfig", {}).get("overrides", []):
        if override.get("matcher", {}).get("options") != "Expected":
            continue
        for prop in override.get("properties", []):
            if prop.get("id") == "noValue":
                expected_no_value = prop.get("value")
    assert isinstance(expected_no_value, str) and expected_no_value.startswith("N/A —")


def test_runtime_10251_select_run_novalue_drops_hedge_tails() -> None:
    """#10251 §7.3: SELECT RUN names one state."""
    panels = _runtime_panels_by_id()
    expected = {
        9402: "SELECT RUN — no exact Run ID selected. Choose a run first.",
        9403: (
            "SELECT RUN — no exact Run ID selected. "
            "Choose a run in Inspect Recent Runs."
        ),
        9998: "SELECT RUN — no exact Run ID selected. Choose a run first.",
    }
    for panel_id, expected_no_value in expected.items():
        no_value = (
            panels[panel_id].get("fieldConfig", {}).get("defaults", {}).get("noValue")
        )
        assert no_value == expected_no_value
        assert "VALID EMPTY if" not in str(no_value)
        assert "UNKNOWN/QUERY ERROR if" not in str(no_value)


def test_dq_10253_selected_run_summary_is_first_window() -> None:
    """#10253 D1: compact selected-run summary sits on the first screen."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    root = {panel.get("id"): panel for panel in dashboard.get("panels") or []}
    summary = root[9406]
    assert summary.get("gridPos") == {"h": 4, "w": 24, "x": 0, "y": 13}
    assert int((root[9405].get("gridPos") or {}).get("y", 0)) >= 17
    assert all(item.get("id") != 9406 for item in (root[9405].get("panels") or []))
    organize = next(
        item
        for item in summary.get("transformations") or []
        if item.get("id") == "organize"
    )
    exclude = (organize.get("options") or {}).get("excludeByName") or {}
    assert exclude.get("started_at") is True
    assert exclude.get("completed_at") is True
    no_value = str(summary.get("fieldConfig", {}).get("defaults", {}).get("noValue"))
    assert no_value.startswith("SELECT RUN")
    assert "VALID EMPTY if" not in no_value


def test_dq_10253_select_run_novalue_drops_hedge_tails() -> None:
    """#10253 §7.3: DQ HTTP empty copy names one state."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels = {
        panel["id"]: panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    expected = {
        9402: "SELECT RUN — no exact Run ID selected. Choose a run first.",
        9403: (
            "SELECT RUN — no exact Run ID selected. "
            "Choose a run in Inspect Recent Runs."
        ),
        9406: "SELECT RUN — no exact Run ID selected. Choose a run first.",
    }
    for panel_id, expected_no_value in expected.items():
        no_value = (
            panels[panel_id].get("fieldConfig", {}).get("defaults", {}).get("noValue")
        )
        assert no_value == expected_no_value
        assert "VALID EMPTY if" not in str(no_value)
        assert "UNKNOWN/QUERY ERROR if" not in str(no_value)
