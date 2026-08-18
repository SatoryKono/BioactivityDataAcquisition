from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "grafana" / "dashboard_states"
CONTENT_CONTRACT_PATH = (
    ROOT
    / "docs"
    / "03-guides"
    / "dashboards"
    / "contracts"
    / "panel-content-contract.yaml"
)
VERDICT_ROLES = {"verdict", "confidence"}
REQUIRED_VERDICT_CASES = {"ok", "warn", "crit", "telemetry_absent", "backend_error"}


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _content_panels() -> list[dict[str, object]]:
    payload = yaml.safe_load(CONTENT_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    dashboards = payload["dashboards"]
    assert isinstance(dashboards, dict)
    panels: list[dict[str, object]] = []
    for dashboard in dashboards.values():
        assert isinstance(dashboard, dict)
        dashboard_panels = dashboard["panels"]
        assert isinstance(dashboard_panels, dict)
        for panel in dashboard_panels.values():
            assert isinstance(panel, dict)
            panels.append(panel)
    return panels


def test_state_fixture_index_is_complete_and_payloads_are_well_formed() -> None:
    index = _load_json(FIXTURE_ROOT / "INDEX.json")
    assert index["contract"] == "dashboard_state_fixture_v1"
    cases = index["cases"]
    assert isinstance(cases, dict)
    assert set(cases) == {
        "ok",
        "warn",
        "crit",
        "telemetry_absent",
        "backend_error",
        "populated",
        "valid_empty",
        "not_applicable",
    }
    for case, metadata in cases.items():
        assert isinstance(metadata, dict)
        path = ROOT / str(metadata["path"])
        payload = _load_json(path)
        assert payload["contract"] == "dashboard_state_fixture_v1"
        assert payload["case"] == case
        assert payload["classification"] == metadata["classification"]
        assert payload["http_status"] == metadata["http_status"]
        assert isinstance(payload["rows"], list)
        assert isinstance(payload["message"], str) and payload["message"]
        assert isinstance(payload["next_action"], str) and payload["next_action"]


def test_fixture_cases_cover_every_declared_content_contract_case() -> None:
    index = _load_json(FIXTURE_ROOT / "INDEX.json")
    cases = index["cases"]
    assert isinstance(cases, dict)
    fixture_cases = set(cases)
    for panel in _content_panels():
        declared_cases = panel["fixture_cases"]
        assert isinstance(declared_cases, list)
        assert set(declared_cases).issubset(fixture_cases)
        if panel["role"] in VERDICT_ROLES:
            assert REQUIRED_VERDICT_CASES.issubset(declared_cases)


def test_terminal_fixture_semantics_distinguish_empty_absence_and_error() -> None:
    valid_empty = _load_json(FIXTURE_ROOT / "valid_empty.json")
    telemetry_absent = _load_json(FIXTURE_ROOT / "telemetry_absent.json")
    backend_error = _load_json(FIXTURE_ROOT / "backend_error.json")
    populated = _load_json(FIXTURE_ROOT / "populated.json")
    not_applicable = _load_json(FIXTURE_ROOT / "not_applicable.json")

    assert valid_empty["http_status"] == 200
    assert valid_empty["classification"] == "VALID_EMPTY"
    assert valid_empty["rows"] == []
    assert telemetry_absent["http_status"] == 200
    assert telemetry_absent["classification"] == "TELEMETRY_ABSENT"
    assert telemetry_absent["rows"] == []
    assert backend_error["http_status"] == 503
    assert backend_error["classification"] == "ERROR"
    assert backend_error["rows"] == []
    assert populated["http_status"] == 200
    rows = populated["rows"]
    assert isinstance(rows, list) and rows
    assert {"parameter", "value", "percentage", "row_status"}.issubset(rows[0])
    assert not_applicable["http_status"] == 200
    assert not_applicable["classification"] == "N/A"
    assert not_applicable["rows"] == []
