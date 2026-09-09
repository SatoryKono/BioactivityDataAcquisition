"""VIS-20260908 stream-3 layout contracts (#10249, #10250, #10254, #10255, #10256)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration._dashboard_layout_budgets import FIRST_WINDOW_Y
from tests.integration._grafana_test_support import get_dashboard_panels, load_dashboard

pytestmark = pytest.mark.integration

_OVERVIEW = Path("grafana/dashboards/bioetl-overview-v2.json")
_INCIDENT = Path("grafana/dashboards/bioetl-incident-v1.json")
_RUNS = Path("grafana/dashboards/bioetl-run-explorer-v1.json")
_RUNBOOK = (
    "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
    "docs/05-operations/runbooks/incident-response.md"
)


def _panel(dashboard: dict, panel_id: int) -> dict:
    panel = next(
        item for item in get_dashboard_panels(dashboard) if item.get("id") == panel_id
    )
    assert isinstance(panel, dict)
    return panel


def _root_ids(dashboard: dict) -> set[object]:
    return {
        panel.get("id")
        for panel in dashboard.get("panels") or []
        if isinstance(panel, dict)
    }


def test_overview_dq_timeline_hides_dotstar_and_in_band_state() -> None:
    """#10249 O1: All not .*; no clipped in-band state text."""
    dashboard = load_dashboard(_OVERVIEW)
    panel = _panel(dashboard, 9019)
    expr = str((panel.get("targets") or [{}])[0].get("expr") or "")
    assert '"pipeline","All"' in expr
    assert '"run_type","All"' in expr
    assert (panel.get("options") or {}).get("showValue") == "never"


def test_set_range_action_names_run_explorer_handoff() -> None:
    """#10250 O2: visible action name matches the Run Explorer transition."""
    dashboard = load_dashboard(_OVERVIEW)
    panel = _panel(dashboard, 9603)
    blob = str(panel)
    assert "Open run in Run Explorer" in blob
    assert '"text": "Set range to run"' not in blob
    assert "from=${__data.fields.from_ms}" in blob
    assert "to=${__data.fields.to_ms}" in blob


def test_overview_and_dq_lower_handoffs_are_explicit_links() -> None:
    """#10250 O3: lower Navigate Diagnostics names are one-click links."""
    overview = load_dashboard(_OVERVIEW)
    content = str((_panel(overview, 9021).get("options") or {}).get("content") or "")
    assert "<a href=" in content
    assert "bioetl-control-plane-v1" in content
    assert "bioetl-runtime" in content
    dq = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    html = " ".join(
        str((panel.get("options") or {}).get("content") or "")
        for panel in get_dashboard_panels(dq)
        if panel.get("type") == "text"
    )
    assert "bioetl-control-plane-v1" in html
    assert "<a href=" in html
    assert "canonical" in html
    assert ">Control Plane</a>" in html
    assert "${__url_time_range}" in content


def test_incident_current_alerts_share_first_window_with_runbook() -> None:
    """#10254 I1: active alerts + runbook on the first Incident screen."""
    dashboard = load_dashboard(_INCIDENT)
    assert 2005 in _root_ids(dashboard)
    alert = _panel(dashboard, 2005)
    suspects = _panel(dashboard, 2010)
    grid = alert.get("gridPos") or {}
    assert int(grid.get("y") or 99) < FIRST_WINDOW_Y
    assert int(grid.get("y") or 0) + int(grid.get("h") or 0) <= FIRST_WINDOW_Y
    assert int(grid.get("w") or 0) == 24
    assert int((suspects.get("gridPos") or {}).get("w") or 0) == 24
    assert int((suspects.get("gridPos") or {}).get("h") or 0) == 5
    assert (suspects.get("options") or {}).get("cellHeight") == "sm"
    links = ((alert.get("fieldConfig") or {}).get("defaults") or {}).get("links") or []
    assert any("runbook" in str(item.get("title", "")).lower() for item in links)
    assert any(_RUNBOOK in str(item.get("url", "")) for item in links)
    assert any(
        isinstance(item, dict)
        and item.get("id") == "limit"
        and (item.get("options") or {}).get("limitField") == 3
        for item in (alert.get("transformations") or [])
    )
    row = next(
        panel
        for panel in dashboard.get("panels") or []
        if isinstance(panel, dict) and panel.get("id") == 2020
    )
    nested = {child.get("id") for child in (row.get("panels") or [])}
    assert 2005 not in nested
    assert 2006 in nested
    assert 2007 in nested


def test_run_identity_reasons_and_artifacts_use_operator_columns() -> None:
    """#10255 R1-R3: local clocks, readable reasons, named artifact actions."""
    dashboard = load_dashboard(_RUNS)
    identity = _panel(dashboard, 3022)
    target = next(
        item
        for item in (identity.get("targets") or [])
        if "identity-table" in str(item.get("url") or "")
    )
    assert target.get("root_selector") == "display_rows"
    assert "timezone=${__timezone}" in str(target.get("url") or "")
    reasons = _panel(dashboard, 3012)
    names = {
        str((item.get("matcher") or {}).get("options") or "")
        for item in (reasons.get("fieldConfig") or {}).get("overrides") or []
    }
    assert "reason_label" in names
    assert "explain" in names
    artifacts = _panel(dashboard, 3013)
    organize = next(
        item
        for item in (artifacts.get("transformations") or [])
        if item.get("id") == "organize"
    )
    exclude = (organize.get("options") or {}).get("excludeByName") or {}
    assert exclude.get("ref") is True
    assert exclude.get("Value") is True
    blob = str(artifacts)
    assert '"value": "Count"' not in blob
    assert "pipeline-run-report-artifact?" in blob


def test_run_id_selector_and_recent_runs_do_not_label_uuid_as_count() -> None:
    """#10256 C1/C2: Run ID options keep text/value; recent runs hide Count."""
    dashboard = load_dashboard(_RUNS)
    run_id = next(
        item
        for item in dashboard.get("templating", {}).get("list", [])
        if item.get("name") == "run_id"
    )
    columns = ((run_id.get("query") or {}).get("infinityQuery") or {}).get("columns")
    selectors = {(item.get("selector"), item.get("text")) for item in columns}
    assert ("text", "__text") in selectors
    assert ("value", "__value") in selectors
    assert "response_shape=options" in str(run_id)
    recent = _panel(dashboard, 3010)
    overrides = (recent.get("fieldConfig") or {}).get("overrides") or []
    assert not any(
        isinstance(item, dict)
        and "Value" in str((item.get("matcher") or {}).get("options") or "")
        and any(
            prop.get("value") == "Count"
            for prop in (item.get("properties") or [])
            if isinstance(prop, dict)
        )
        for item in overrides
    )
    organize = next(
        item
        for item in (recent.get("transformations") or [])
        if item.get("id") == "organize"
    )
    assert ((organize.get("options") or {}).get("excludeByName") or {}).get(
        "Value"
    ) is True
    rename = (organize.get("options") or {}).get("renameByName") or {}
    assert rename.get("run_id") == "Run"
    assert rename.get("started_at") == "Started"
    assert rename.get("status") == "Status"
