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

from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


_PROVIDER_HEALTH_DASHBOARD = Path("grafana/dashboards/bioetl-overview-v2.json")
_PROVIDER_HEALTH_UID = "bioetl-overview-v2"
_PROVIDER_SINGLE_STATE_NO_VALUE_PANEL_IDS = (9480, 9481)


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


def test_provider_health_fleet_cause_tables_are_retired() -> None:
    panels = _provider_health_panels_by_id()
    assert not Path("grafana/dashboards/bioetl-provider-health-v2.json").exists()
    assert {9401, 9101, 9102, 9103, 9107, 114}.isdisjoint(panels)
    for panel_id in _PROVIDER_SINGLE_STATE_NO_VALUE_PANEL_IDS:
        panel = panels[panel_id]
        assert all("expr" not in target for target in panel["targets"])
        assert all("run_id=${run_id}" in target["url"] for target in panel["targets"])


def test_provider_cause_contract_declares_unknown_beside_valid_empty() -> None:
    """Contract must admit UNKNOWN beside VALID_EMPTY on selected-run panels."""
    contract = yaml.safe_load(
        Path(
            "docs/03-guides/dashboards/contracts/panel-content-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    panels = contract["dashboards"][_PROVIDER_HEALTH_UID]["panels"]
    for panel_id in _PROVIDER_SINGLE_STATE_NO_VALUE_PANEL_IDS:
        record = panels[str(panel_id)]
        assert "UNKNOWN" in record["state_model"], (
            f"panel {panel_id} must declare the UNKNOWN state"
        )


def _runtime_panels_by_id() -> dict[int, dict]:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    return {
        panel["id"]: panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }


def test_runtime_10251_select_run_novalue_drops_hedge_tails() -> None:
    panels = _runtime_panels_by_id()
    for pid in (9603, 9604, 9480, 9481):
        no_value = panels[pid]["fieldConfig"]["defaults"]["noValue"]
        assert no_value == "UNKNOWN"
        assert "VALID EMPTY if" not in no_value
        assert "UNKNOWN/QUERY ERROR if" not in no_value
    assert not Path("grafana/dashboards/bioetl-runtime.json").exists()


def test_dq_10253_selected_run_summary_is_first_window() -> None:
    """#10253 D1: compact selected-run summary sits on the first screen."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    root = {panel.get("id"): panel for panel in dashboard.get("panels") or []}
    summary = root[9406]
    assert summary.get("gridPos") == {"h": 5, "w": 24, "x": 0, "y": 5}
    organize = next(
        item
        for item in summary.get("transformations") or []
        if item.get("id") == "organize"
    )
    assert organize["options"]["indexByName"] == {
        "execution_state": 0,
        "verdict": 1,
        "saved_trust": 2,
        "reason_display": 3,
    }
    assert "presentation_summary[0]" in summary["targets"][0]["root_selector"]
    assert "/selected-run-status?" in summary["targets"][0]["url"]
    no_value = str(summary.get("fieldConfig", {}).get("defaults", {}).get("noValue"))
    assert (
        no_value == "UNKNOWN"
    )  # Missing response must not masquerade as no selection.
    assert "VALID EMPTY if" not in no_value


def test_dq_10253_select_run_novalue_drops_hedge_tails() -> None:
    """#10253 §7.3: DQ HTTP empty copy names one state (#11569: Run Explorer)."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels = {
        panel["id"]: panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    expected = {
        9402: "SELECT RUN — no exact Run ID selected. Choose a run first.",
        9403: (
            "SELECT RUN — no exact Run ID selected. Choose this run in Run Explorer."
        ),
        9406: "UNKNOWN",
    }
    for panel_id, expected_no_value in expected.items():
        no_value = (
            panels[panel_id].get("fieldConfig", {}).get("defaults", {}).get("noValue")
        )
        assert no_value == expected_no_value
        assert "VALID EMPTY if" not in str(no_value)
        assert "UNKNOWN/QUERY ERROR if" not in str(no_value)
