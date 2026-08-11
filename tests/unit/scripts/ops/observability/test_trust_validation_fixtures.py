"""Contract tests for Trust validation close-up fixtures (#8576/#8578/#8593/#8598)."""

from __future__ import annotations

import ast
import json
import threading
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

import pytest

from scripts.ops.observability.grafana.serve_trust_validation_fixtures import (
    FixtureHandler,
)
from scripts.ops.observability.trust_validation_fixture_materialization import (
    materialize_trust_validation_fixture_matrix,
)

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
            (ROOT / endpoint / "valid_empty_or_unknown.json").read_text(
                encoding="utf-8"
            )
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
    for _endpoint, states in index["endpoints"].items():
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


def test_fixture_handler_log_message_does_not_raise_nameerror(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """#8593: log_message must not reference undefined fmt/args."""
    handler = object.__new__(FixtureHandler)
    handler.command = "GET"
    handler.path = "/ops/control-plane/checkpoint-validation?fixture_state=populated"
    # Must not raise NameError (historical F821 on del fmt, args).
    handler.log_message("%s %s", "ignored", "format")
    err = capsys.readouterr().err
    assert "[fixture] GET /ops/control-plane/checkpoint-validation" in err
    assert "ignored" not in err


def test_fixture_server_serves_populated_and_503_states(
    tmp_path: Path,
) -> None:
    """#8593: request path returns fixture payloads with correct HTTP status."""
    from http.server import ThreadingHTTPServer

    # Point handler at tracked fixtures.
    FixtureHandler.fixture_root = ROOT
    FixtureHandler.default_state = "populated"
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        conn = HTTPConnection(str(host), int(port), timeout=5)
        conn.request(
            "GET",
            "/ops/control-plane/checkpoint-validation?fixture_state=populated",
        )
        populated = conn.getresponse()
        body = json.loads(populated.read().decode("utf-8"))
        assert populated.status == 200
        assert body["status"] == "OK"
        assert body["endpoint"] == "checkpoint-validation"

        conn.request(
            "GET",
            "/ops/control-plane/failure-reasons?fixture_state=service_unavailable",
        )
        unavailable = conn.getresponse()
        err_body = json.loads(unavailable.read().decode("utf-8"))
        assert unavailable.status == 503
        assert err_body["status"] == "ERROR"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_materialize_writes_outside_grafana_tooling_boundary(tmp_path: Path) -> None:
    """#8598: materialization I/O lives outside scripts/.../grafana/."""
    materialization = Path(
        "scripts/ops/observability/trust_validation_fixture_materialization.py"
    )
    generate = Path(
        "scripts/ops/observability/grafana/generate_trust_validation_fixtures.py"
    )
    assert materialization.is_file()
    assert "grafana" not in materialization.parts[-2:]
    generate_src = generate.read_text(encoding="utf-8")
    assert "materialize_trust_validation_fixture_matrix" in generate_src
    tree = ast.parse(generate_src)
    write_text_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "write_text"
    ]
    assert write_text_calls == [], (
        "generate_trust_validation_fixtures.py must not call write_text; "
        "materialization owns fixture I/O (#8598)"
    )

    matrix: dict[str, dict[str, dict[str, Any]]] = {
        "checkpoint-validation": {
            "populated": {
                "contract": "control_plane_validation_evidence_v1",
                "endpoint": "checkpoint-validation",
                "status": "OK",
                "rows": [{"check": "parse", "status": "OK", "reason": "ok"}],
            }
        }
    }
    index = materialize_trust_validation_fixture_matrix(
        out=tmp_path,
        matrix=matrix,
        panel_map={9413: "checkpoint-validation"},
        fixture_run_id="00000000-0000-0000-0000-000000008576",
    )
    assert index["contract"] == "control_plane_validation_evidence_v1"
    written = tmp_path / "checkpoint-validation" / "populated.json"
    assert written.is_file()
    assert (tmp_path / "INDEX.json").is_file()
