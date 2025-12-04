import logging
from dataclasses import dataclass
from typing import Any

import pytest

from bioetl.domain.errors import (
    ClientNetworkError,
    ClientRateLimitError,
    ClientResponseError,
)
from bioetl.infrastructure.clients.middleware import HttpClientMiddleware


@dataclass
class _FakeResponse:
    status_code: int
    payload: dict[str, Any]

    def raise_for_status(self) -> None:  # pragma: no cover - simple stub
        return None

    def json(self) -> dict[str, Any]:  # pragma: no cover - compatibility
        return self.payload


class _BaseClientStub:
    def __init__(self, responses: list[_FakeResponse] | None = None) -> None:
        self.responses = responses or []
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **_: Any) -> _FakeResponse:
        self.calls.append((method, url))
        if not self.responses:
            raise TimeoutError("timeout")
        return self.responses.pop(0)


def test_success_request_returns_response(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    response = _FakeResponse(status_code=200, payload={"ok": True})
    client = _BaseClientStub(responses=[response])

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=client,
        max_attempts=1,
        base_delay=0.0,
        max_delay=0.0,
    )

    result = middleware.request("GET", "http://example.com")

    assert result is response
    assert client.calls == [("GET", "http://example.com")]
    assert "HTTP request succeeded" in caplog.text


def test_timeout_raises_network_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    client = _BaseClientStub(responses=[])

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=client,
        max_attempts=1,
        base_delay=0.0,
        max_delay=0.0,
    )

    with pytest.raises(ClientNetworkError):
        middleware.request("GET", "http://example.com")

    assert client.calls == [("GET", "http://example.com")]
    assert "HTTP request failed" in caplog.text


def test_rate_limit_retries_and_returns_success(  # noqa: D103 - test
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    retry = _FakeResponse(status_code=429, payload={})
    success = _FakeResponse(status_code=200, payload={"ok": True})
    client = _BaseClientStub(responses=[retry, success])

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=client,
        max_attempts=3,
        base_delay=0.0,
        max_delay=0.0,
        backoff_factor=1.0,
    )

    result = middleware.request("GET", "http://example.com")

    assert result is success
    assert client.calls == [
        ("GET", "http://example.com"),
        ("GET", "http://example.com"),
    ]
    assert "HTTP request failed" in caplog.text
    assert "HTTP request succeeded" in caplog.text


def test_server_error_exhausts_retries(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    responses = [_FakeResponse(status_code=503, payload={}) for _ in range(2)]
    client = _BaseClientStub(responses=responses)

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=client,
        max_attempts=2,
        base_delay=0.0,
        max_delay=0.0,
        backoff_factor=1.0,
    )

    with pytest.raises(ClientResponseError):
        middleware.request("GET", "http://example.com")

    assert client.calls == [
        ("GET", "http://example.com"),
        ("GET", "http://example.com"),
    ]
    assert caplog.text.count("HTTP request failed") >= 2
