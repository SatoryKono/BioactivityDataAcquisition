# pyright: reportArgumentType=false
"""DASH-QA #9088 residual selected-run vs CURRENT operator-safety gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from scripts.engineering.qa import validate_dashboard_content_contract as content
from scripts.ops.observability.grafana.dashboard_context_links import (
    RUN_ID_GRAFANA_REGEX,
    DashboardContext,
    RunIdError,
    normalize_run_id,
    preserves_time_window,
    urls_for_context,
)

from tests.integration._dashboard_layout_budgets import FIRST_WINDOW_Y
from tests.integration._grafana_dashboard_links_support import get_dashboard_files
from tests.integration._grafana_test_support import get_dashboard_panels, load_dashboard

pytestmark = pytest.mark.integration

DASHBOARD_DIR = Path("grafana/dashboards")
CONTRACT_PATH = Path("docs/03-guides/dashboards/contracts/panel-content-contract.yaml")
DISPOSITION_PATH = Path(
    "docs/03-guides/dashboards/contracts/current-card-disposition.yaml"
)
FIXTURE_RUN_ID = "68c11d41-1d2f-5dc9-b041-9265bc485046"
QUERY_TYPES = {
    "stat",
    "table",
    "timeseries",
    "gauge",
    "bargauge",
    "heatmap",
    "state-timeline",
}


def test_canonical_context_trims_run_id_and_shares_uuid_across_seven_uids() -> None:
    with pytest.raises(RunIdError):
        normalize_run_id("%20%20")
    with pytest.raises(RunIdError):
        normalize_run_id("  ")
    context = DashboardContext(
        workflow="chembl_baseline",
        pipeline="chembl_assay",
        run_type="backfill",
        run_id=f"  {FIXTURE_RUN_ID}  ",
    )
    assert context.run_id == FIXTURE_RUN_ID
    urls = urls_for_context(context)
    assert set(urls) == {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-incident-v1",
        "bioetl-run-explorer-v1",
    }
    run_ids = {url.split("var-run_id=", 1)[1].split("&", 1)[0] for url in urls.values()}
    assert run_ids == {FIXTURE_RUN_ID}
    omitted = DashboardContext(
        workflow="chembl_baseline",
        pipeline="chembl_assay",
        run_type="backfill",
        run_id=FIXTURE_RUN_ID,
    )
    for url in urls_for_context(omitted).values():
        assert "var-run_id=" in url
        assert preserves_time_window(url)


def test_shipped_run_id_variables_trim_whitespace() -> None:
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        variables = (dashboard.get("templating") or {}).get("list") or []
        run_id = next(
            (
                variable
                for variable in variables
                if isinstance(variable, dict) and variable.get("name") == "run_id"
            ),
            None,
        )
        assert run_id is not None, path.name
        assert run_id.get("regex") == RUN_ID_GRAFANA_REGEX


def test_data_bearing_selected_run_uses_ops_http() -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    records, errors = content._contract_panel_records(contract)
    assert errors == []
    offenders: list[str] = []
    for (uid, panel_id), record in records.items():
        if record.get("role") in {"navigation", "row_group", "guidance"}:
            continue
        if record.get("scope") != "selected_run":
            continue
        if record.get("evidence_source") != "ops_http":
            offenders.append(f"{uid}:{panel_id}")
    assert not offenders, "selected_run must be ops_http:\n" + "\n".join(offenders)


def test_empty_state_classes_are_declared_and_visible_copy_differs() -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    records, _ = content._contract_panel_records(contract)
    allowed = {"event_empty", "telemetry_missing", "unsupported", "select_run"}
    missing: list[str] = []
    for (uid, panel_id), record in records.items():
        if record.get("role") in {"navigation", "row_group", "guidance"}:
            continue
        if record.get("empty_state_class") not in allowed:
            missing.append(f"{uid}:{panel_id}")
    assert not missing, "empty_state_class:\n" + "\n".join(missing[:20])

    event_copy: set[str] = set()
    missing_copy: set[str] = set()
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        uid = str(dashboard.get("uid"))
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") not in QUERY_TYPES:
                continue
            record = records.get((uid, str(panel.get("id"))))
            if record is None:
                continue
            no_value = str(
                ((panel.get("fieldConfig") or {}).get("defaults") or {}).get("noValue")
                or ""
            )
            blob = f"{panel.get('description') or ''}\n{no_value}"
            klass = record.get("empty_state_class")
            if klass == "event_empty":
                event_copy.add(blob)
            if klass == "telemetry_missing":
                missing_copy.add(blob)
    assert event_copy
    assert missing_copy
    assert event_copy != missing_copy


def test_provider_freshness_is_not_present_ok_on_missing_health_status() -> None:
    dashboard = load_dashboard(DASHBOARD_DIR / "bioetl-provider-health-v2.json")
    panel = next(
        item for item in get_dashboard_panels(dashboard) if item.get("id") == 9104
    )
    expr = str((panel.get("targets") or [{}])[0].get("expr") or "")
    assert "bioetl_provider_health_status" in expr
    assert "test|synthetic" in expr
    blob = f"{panel.get('title') or ''}\n{panel.get('description') or ''}"
    assert "PRESENT" in blob
    assert "PRESENT≠OK" in blob or "not a healthy" in blob.lower()
    fleet = next(
        item for item in get_dashboard_panels(dashboard) if item.get("id") == 9101
    )
    fleet_expr = str((fleet.get("targets") or [{}])[0].get("expr") or "")
    assert "provider=~\"$provider\"" in fleet_expr
    assert "test|synthetic" in fleet_expr


def test_current_card_disposition_covers_first_window_current_panels() -> None:
    payload = yaml.safe_load(DISPOSITION_PATH.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    assert isinstance(entries, list) and entries
    allowed = {"keep", "collapse", "retire"}
    missing_panels: list[str] = []
    for item in entries:
        assert item.get("disposition") in allowed
        assert item.get("owner")
        assert item.get("freshness_slo")
        assert item.get("reason")
        if item.get("disposition") == "collapse":
            assert item.get("collapse_into")
        dashboard = load_dashboard(DASHBOARD_DIR / str(item["dashboard"]))
        panel = next(
            (
                candidate
                for candidate in get_dashboard_panels(dashboard)
                if candidate.get("id") == item["id"]
            ),
            None,
        )
        if panel is None:
            missing_panels.append(f"{item['dashboard']}:{item['id']}")
    assert not missing_panels, "disposition panel missing:\n" + "\n".join(
        missing_panels
    )
    overview = load_dashboard(DASHBOARD_DIR / "bioetl-overview-v2.json")
    keep = {
        (str(item["dashboard"]), int(item["id"]))
        for item in entries
        if item.get("disposition") == "keep"
    }
    assert ("bioetl-overview-v2.json", 214) in keep
    assert ("bioetl-overview-v2.json", 215) in keep
    fleet = next(panel for panel in overview["panels"] if panel.get("id") == 214)
    assert int((fleet.get("gridPos") or {}).get("y") or 99) < FIRST_WINDOW_Y


def test_trust_9416_fixture_rows_are_structured() -> None:
    populated = json.loads(
        Path(
            "tests/fixtures/grafana/control_plane_validation/retention-compliance/populated.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(populated.get("rows"), list)
    assert populated["rows"]
    for row in populated["rows"]:
        assert {"check", "status", "reason", "detail"} <= set(row)
