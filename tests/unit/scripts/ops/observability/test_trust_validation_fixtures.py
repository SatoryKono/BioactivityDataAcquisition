"""Contract tests for Trust validation close-up fixtures (#8576/#8578)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path("tests/fixtures/grafana/control_plane_validation")
PANEL_MAP = {
    9413: "checkpoint-validation",
    9414: "manifest-validation",
    9415: "lineage-validation",
    9416: "retention-compliance",
    9417: "failure-reasons",
}
REQUIRED_STATES = {
    "populated",
    "valid_empty_or_unknown",
    "backend_error",
    "service_unavailable",
    "empty_rows",
}


def test_index_maps_trust_panels_and_required_states() -> None:
    index = json.loads((ROOT / "INDEX.json").read_text(encoding="utf-8"))
    assert index["contract"] == "control_plane_validation_evidence_v1"
    panel_map = {str(k): v for k, v in index["panel_map"].items()}
    for panel_id, endpoint in PANEL_MAP.items():
        assert panel_map[str(panel_id)] == endpoint
    endpoints = index["endpoints"]
    for endpoint in PANEL_MAP.values():
        assert endpoint in endpoints
        for state in REQUIRED_STATES:
            assert state in endpoints[endpoint], f"{endpoint} missing {state}"
            meta = endpoints[endpoint][state]
            path = Path(meta["path"])
            assert path.is_file(), path
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["contract"] == "control_plane_validation_evidence_v1"
            assert payload["endpoint"] == endpoint
            assert "rows" in payload
            assert isinstance(payload["rows"], list)
            assert payload["status"] in {"OK", "WARNING", "ERROR", "UNKNOWN"}
            assert meta["row_count"] == len(payload["rows"])


def test_populated_is_not_error_and_unknown_is_not_ok() -> None:
    for endpoint in PANEL_MAP.values():
        populated = json.loads(
            (ROOT / endpoint / "populated.json").read_text(encoding="utf-8")
        )
        unknown = json.loads(
            (ROOT / endpoint / "valid_empty_or_unknown.json").read_text(encoding="utf-8")
        )
        error = json.loads(
            (ROOT / endpoint / "backend_error.json").read_text(encoding="utf-8")
        )
        assert populated["status"] == "OK"
        assert unknown["status"] == "UNKNOWN"
        assert error["status"] == "ERROR"
        assert any(row.get("status") == "ERROR" for row in error["rows"])


def test_service_unavailable_marks_http_503() -> None:
    index = json.loads((ROOT / "INDEX.json").read_text(encoding="utf-8"))
    for endpoint, states in index["endpoints"].items():
        meta = states["service_unavailable"]
        assert meta["http_status"] == 503
        payload = json.loads(Path(meta["path"]).read_text(encoding="utf-8"))
        assert payload["status"] == "ERROR"


def test_failure_reasons_zero_failures_has_zero_counts() -> None:
    payload = json.loads(
        (ROOT / "failure-reasons" / "zero_failures.json").read_text(encoding="utf-8")
    )
    assert payload["status"] == "OK"
    assert payload["total_failure_count"] == 0
    assert all(row.get("count") == 0 for row in payload["rows"])
    assert {row["category"] for row in payload["rows"]} == {
        "api",
        "dq",
        "schema",
        "storage",
        "network",
        "validation",
        "unknown",
    }


def test_empty_rows_fixture_is_empty_list() -> None:
    for endpoint in PANEL_MAP.values():
        payload = json.loads(
            (ROOT / endpoint / "empty_rows.json").read_text(encoding="utf-8")
        )
        assert payload["rows"] == []
