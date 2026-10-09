from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pytest
from vcr.request import Request

from tests.helpers.vcr_config import (
    build_base_vcr_config,
    is_vcr_recording_mode,
    query_ignore_email,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("query=protein&size=1&format=json", "format=json&query=protein&size=1", True),
        ("query=a&email=one&api_key=secret", "key=other&query=a", True),
        ("query=a+b", "query=a%20b", True),
        ("retmax=1", "retmax=5", False),
        ("query=", "", False),
        ("id=1&id=1", "id=1", False),
        ("id=1&id=2", "id=2&id=1", False),
        ("id=1&format=json&id=2", "format=json&id=1&id=2", True),
    ],
)
def test_query_matcher_preserves_values_and_repeated_key_order(
    left: str, right: str, expected: bool
) -> None:
    first = Request("GET", f"https://example.org/search?{left}", b"", {})
    second = Request("GET", f"https://example.org/search?{right}", b"", {})

    assert query_ignore_email(first, second) is expected


def test_is_vcr_recording_mode_uses_env(monkeypatch) -> None:
    monkeypatch.setenv("VCR_RECORD_MODE", "new_episodes")
    monkeypatch.setattr("sys.argv", ["pytest"])

    assert is_vcr_recording_mode() is True


def test_is_vcr_recording_mode_detects_cli_flag(monkeypatch) -> None:
    monkeypatch.delenv("VCR_RECORD_MODE", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["pytest", "tests/e2e/test_pubchem_compound_e2e.py", "--vcr-record=all"],
    )

    assert is_vcr_recording_mode() is True


def test_is_vcr_recording_mode_defaults_to_replay(monkeypatch) -> None:
    monkeypatch.delenv("VCR_RECORD_MODE", raising=False)
    monkeypatch.setattr("sys.argv", ["pytest"])

    assert is_vcr_recording_mode() is False


def test_build_base_vcr_config_defaults_to_replay_only(monkeypatch) -> None:
    monkeypatch.delenv("VCR_RECORD_MODE", raising=False)

    assert build_base_vcr_config()["record_mode"] == "none"


def test_build_base_vcr_config_sanitizes_request_headers_and_query() -> None:
    config = build_base_vcr_config(
        filter_headers=["authorization"],
        filter_query_parameters=["api_key"],
    )
    before_record_request = cast(Callable[[Any], Any], config["before_record_request"])

    request = Request(
        "GET",
        "https://example.org/search?api_key=secret&query=test",
        b"",
        {"authorization": "secret", "x-test": "1"},
    )

    sanitized = before_record_request(request)

    assert sanitized.headers["x-test"] == "1"
    assert "authorization" not in sanitized.headers
    assert "api_key=secret" not in sanitized.uri
    assert "query=test" in sanitized.uri


def test_build_base_vcr_config_before_record_request_noops_on_unexpected_request() -> (
    None
):
    config = build_base_vcr_config(
        filter_headers=["authorization"],
        filter_query_parameters=["api_key"],
    )
    before_record_request = cast(Callable[[Any], Any], config["before_record_request"])

    request = "unexpected-request-surface"

    assert before_record_request(request) == request


def test_build_base_vcr_config_filters_transient_html_server_errors() -> None:
    config = build_base_vcr_config()
    before_record_response = cast(
        Callable[[Any], Any], config["before_record_response"]
    )

    response = {
        "status": {"code": 500, "message": "Internal Server Error"},
        "headers": {"Content-Type": ["text/html"]},
        "body": {"string": b"<html>Error: 500</html>"},
    }

    assert before_record_response(response) is None


def test_build_base_vcr_config_preserves_successful_json_response() -> None:
    config = build_base_vcr_config()
    before_record_response = cast(
        Callable[[Any], Any], config["before_record_response"]
    )

    response = {
        "status": {"code": 200, "message": "OK"},
        "headers": {"Content-Type": ["application/json"]},
        "body": {"string": b'{"status":"UP"}'},
    }

    assert before_record_response(response) == response


def test_build_base_vcr_config_before_record_response_noops_on_unexpected_response() -> (
    None
):
    config = build_base_vcr_config()
    before_record_response = cast(
        Callable[[Any], Any], config["before_record_response"]
    )

    response = "unexpected-response-surface"

    assert before_record_response(response) == response
