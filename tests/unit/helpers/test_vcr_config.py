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


def test_build_base_vcr_config_before_record_request_fails_closed_on_unexpected_request() -> None:
    from tests.helpers.vcr_config import VCRRequestSanitizationError

    config = build_base_vcr_config(
        filter_headers=["authorization"],
        filter_query_parameters=["api_key"],
    )
    before_record_request = cast(Callable[[Any], Any], config["before_record_request"])

    request = "unexpected-request-surface"

    with pytest.raises(VCRRequestSanitizationError):
        before_record_request(request)


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


def test_build_base_vcr_config_before_record_response_drops_unexpected_response() -> (
    None
):
    config = build_base_vcr_config()
    before_record_response = cast(
        Callable[[Any], Any], config["before_record_response"]
    )

    response = "unexpected-response-surface"

    assert before_record_response(response) is None


@pytest.mark.parametrize("cookie_header", ["Set-Cookie", "set-cookie", "SET-COOKIE2"])
def test_response_sanitizer_removes_secrets_without_mutating_response(cookie_header):
    hook = cast(Callable[[Any], Any], build_base_vcr_config()["before_record_response"])
    response = {
        "status": {"code": 200},
        "headers": {
            cookie_header: ["ncbi_sid=session-secret; HttpOnly"],
            "Authorization": ["Bearer secret"],
            "X-API-Key": ["secret"],
            "Cookie": ["session=secret"],
            "Content-Type": ["application/json"],
        },
        "body": {"string": b"{}"},
    }

    sanitized = hook(response)

    assert sanitized["headers"] == {"Content-Type": ["application/json"]}
    assert sanitized["body"] == response["body"]
    assert response["headers"][cookie_header] == ["ncbi_sid=session-secret; HttpOnly"]


@pytest.mark.parametrize("headers", [None, "invalid", ["Set-Cookie"]])
def test_response_sanitizer_drops_unsupported_headers(headers):
    hook = cast(Callable[[Any], Any], build_base_vcr_config()["before_record_response"])

    assert hook({"status": {"code": 200}, "headers": headers}) is None


def test_build_base_vcr_config_installs_canonical_filters_without_caller_filters() -> (
    None
):
    """CF-030: canonical secret filters are installed even for bare calls."""
    config = build_base_vcr_config()
    before_record_request = cast(Callable[[Any], Any], config["before_record_request"])

    request = Request(
        "GET",
        "https://example.org/search?api_key=secret&query=test",
        b"",
        {"authorization": "Bearer secret", "x-api-key": "k", "cookie": "c=1"},
    )

    sanitized = before_record_request(request)

    assert "authorization" not in sanitized.headers
    assert "x-api-key" not in sanitized.headers
    assert "cookie" not in sanitized.headers
    assert "api_key=secret" not in sanitized.uri
    assert "key=secret" not in sanitized.uri


def test_build_base_vcr_config_caller_filters_extend_but_never_remove_canonical() -> (
    None
):
    """CF-030: caller extras extend the canonical set; canonical keys stay enforced."""
    config = build_base_vcr_config(
        filter_headers=["x-custom-token"],
        filter_query_parameters=["token"],
    )
    before_record_request = cast(Callable[[Any], Any], config["before_record_request"])

    request = Request(
        "GET",
        "https://example.org/search?token=abc&query=test",
        b"",
        {"authorization": "Bearer secret", "x-custom-token": "t"},
    )

    sanitized = before_record_request(request)

    assert "authorization" not in sanitized.headers
    assert "x-custom-token" not in sanitized.headers
    assert "token=abc" not in sanitized.uri
    assert "query=test" in sanitized.uri


def test_build_base_vcr_config_sanitizer_is_always_installed() -> None:
    """CF-030: before_record_request is present even without caller filters."""
    config = build_base_vcr_config()

    assert callable(config["before_record_request"])


@pytest.mark.parametrize("missing_attribute", ["headers", "uri"])
def test_sanitizer_fails_closed_with_missing_required_surface(
    missing_attribute: str,
) -> None:
    from types import SimpleNamespace

    from tests.helpers.vcr_config import VCRRequestSanitizationError

    attributes = {
        "headers": {"authorization": "synthetic-secret"},
        "uri": "https://example.org/?api_key=synthetic-secret",
    }
    del attributes[missing_attribute]
    request = SimpleNamespace(**attributes)
    hook = cast(Callable[[Any], Any], build_base_vcr_config()["before_record_request"])
    with pytest.raises(VCRRequestSanitizationError):
        hook(request)


def test_sanitizer_fails_closed_on_httpx_request_instead_of_retaining_query_secret() -> None:
    import httpx

    from tests.helpers.vcr_config import VCRRequestSanitizationError

    request = httpx.Request(
        "GET",
        "https://example.org/?api_key=synthetic-secret",
        headers={"authorization": "synthetic-secret"},
    )
    hook = cast(Callable[[Any], Any], build_base_vcr_config()["before_record_request"])
    with pytest.raises(VCRRequestSanitizationError):
        hook(request)


@pytest.mark.parametrize("request_count", [1, 2])
def test_build_base_vcr_config_sanitizer_logs_failure_only_once(
    monkeypatch, caplog, request_count
) -> None:
    """CF-030: repeated sanitizer failures stay silent after the first warning."""
    import logging
    from unittest.mock import Mock

    import vcr.filters
    from vcr.cassette import Cassette, RecordMode
    from vcr.stubs import VCRHTTPConnection

    from tests.helpers.vcr_config import VCRRequestSanitizationError

    config = build_base_vcr_config()
    before_record_request = cast(Callable[[Any], Any], config["before_record_request"])

    request = Request(
        "GET",
        "https://example.org/search?api_key=secret",
        b"",
        {"authorization": "Bearer secret"},
    )

    def _explode(*args: Any, **kwargs: Any) -> Any:
        raise TypeError("malformed request surface")

    monkeypatch.setattr(vcr.filters, "replace_headers", _explode)
    monkeypatch.setattr("tests.helpers.vcr_config._sanitizer_failure_logged", False)

    with caplog.at_level(logging.WARNING, logger="tests.helpers.vcr_config"):
        for _ in range(request_count):
            with pytest.raises(VCRRequestSanitizationError):
                before_record_request(request)

    dropped = [
        record
        for record in caplog.records
        if record.getMessage() == "vcr_request_sanitizer_failed_closed"
    ]
    assert len(dropped) == 1

    cassette = Cassette(
        path="unused.yaml",
        record_mode=RecordMode.NONE,
        before_record_request=before_record_request,
    )
    connection = object.__new__(VCRHTTPConnection)
    connection.cassette = cassette
    connection._vcr_request = request
    connection.real_connection = Mock()

    with pytest.raises(VCRRequestSanitizationError):
        connection.getresponse()

    connection.real_connection.request.assert_not_called()
