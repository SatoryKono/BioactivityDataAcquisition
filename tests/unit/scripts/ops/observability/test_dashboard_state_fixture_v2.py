from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from scripts.ops.observability.grafana import dashboard_state_fixture_v2 as v2
from scripts.ops.observability.grafana import rerender_grafana_screenshots as rerender

pytestmark = pytest.mark.unit

INDEX = Path("tests/fixtures/grafana/dashboard_states_v2/INDEX.json")


def test_v2_index_loads_required_cases() -> None:
    payload = v2.load_v2_index(INDEX)
    assert payload["contract"] == v2.CONTRACT
    for case_id in v2.REQUIRED_CASES:
        assert case_id in payload["cases"]
        case = v2.load_v2_case(INDEX, case_id)
        assert case["case_id"] == case_id
        assert case["response_sha256"] == v2.canonical_json_sha256(
            case["datasource_response"]
        )


def test_v2_rejects_stale_response_digest() -> None:
    case = v2.load_v2_case(INDEX, "ok")
    case["response_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="response_sha256"):
        v2.validate_v2_case(case, expected_case_id="ok")


def test_compare_expected_actual_fails_closed() -> None:
    expected = [{"id": "9418", "classification": "OK"}]
    v2.compare_expected_actual(expected, {"9418": "OK"})
    with pytest.raises(ValueError, match="mismatch"):
        v2.compare_expected_actual(expected, {"9418": "ERROR"})
    with pytest.raises(ValueError, match="missing"):
        v2.compare_expected_actual(expected, {})


def test_parse_args_fixture_case_requires_v2_manifest() -> None:
    with pytest.raises(SystemExit):
        rerender._parse_args(["--fixture-case", "ok"])


def test_parse_args_fixture_case_binds_v2_evidence() -> None:
    config = rerender._parse_args(
        [
            "--fixture-manifest",
            str(INDEX),
            "--fixture-case",
            "ok",
        ]
    )
    assert config.fixture_case == "ok"
    assert config.fixture_state is not None
    assert config.fixture_state["contract"] == v2.CONTRACT
    assert config.fixture_state["case_id"] == "ok"
    assert len(str(config.fixture_state["response_sha256"])) == 64


def test_parse_args_fixture_case_rejects_v1_index() -> None:
    with pytest.raises(SystemExit):
        rerender._parse_args(
            [
                "--fixture-manifest",
                "tests/fixtures/grafana/dashboard_states/INDEX.json",
                "--fixture-case",
                "ok",
            ]
        )


def test_stub_server_serves_selected_response() -> None:
    case = v2.load_v2_case(INDEX, "backend_error")
    server = v2.start_stub_server(case, port=0)
    host, port = server.server_address
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        urllib.request.urlopen(f"http://{host}:{port}/prom", timeout=3)
        raise AssertionError("expected HTTP 503")
    except urllib.error.HTTPError as exc:
        assert exc.code == 503
        body = json.loads(exc.read().decode("utf-8"))
    assert body["status"] == "ERROR"
    server.server_close()
