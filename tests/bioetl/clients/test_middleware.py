import logging
from dataclasses import dataclass

import pytest

from bioetl.domain.errors import (
    ClientNetworkError,
    ClientRateLimitError,
    ClientResponseError,
)
from bioetl.infrastructure.clients.base.middleware import HttpClientMiddleware


@dataclass
class _FakeResponse:
    status_code: int
    payload: dict

    def json(self) -> dict:
        return self.payload


class _RetryPolicyStub:
    def __init__(self, max_attempts: int = 3) -> None:
        self.max_attempts = max_attempts
        self.calls: list[tuple[Exception, int]] = []

    def should_retry(self, error: Exception, attempt: int) -> bool:
        self.calls.append((error, attempt))
        return attempt < self.max_attempts

    def get_delay(self, attempt: int) -> float:
        return 0.0


def test_success_request(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    response = _FakeResponse(status_code=200, payload={"ok": True})

    class _Client:
        def get(self, url: str) -> _FakeResponse:  # pragma: no cover - simple stub
            return response

    middleware = HttpClientMiddleware(
        provider="chembl",
        http_client=_Client(),
        retry_policy=_RetryPolicyStub(),
        logger=logging.getLogger("test_success"),
    )

    result = middleware.request("http://example.com")

    assert result == {"ok": True}
    assert "HTTP request failed" not in caplog.text


def test_timeout_raises_network_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)

    class _Client:
        def get(self, url: str) -> _FakeResponse:  # pragma: no cover - simple stub
            raise TimeoutError("timeout")

    middleware = HttpClientMiddleware(
        provider="chembl",
        http_client=_Client(),
        retry_policy=_RetryPolicyStub(max_attempts=1),
        logger=logging.getLogger("test_timeout"),
    )

    with pytest.raises(ClientNetworkError):
        middleware.request("http://example.com")

    assert "HTTP request failed" in caplog.text


def test_rate_limit_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    response = _FakeResponse(status_code=429, payload={})

    class _Client:
        def get(self, url: str) -> _FakeResponse:  # pragma: no cover - simple stub
            return response

    middleware = HttpClientMiddleware(
        provider="chembl",
        http_client=_Client(),
        retry_policy=_RetryPolicyStub(max_attempts=1),
        logger=logging.getLogger("test_rate_limit"),
    )

    with pytest.raises(ClientRateLimitError):
        middleware.request("http://example.com")

    assert "HTTP request failed" in caplog.text


def test_server_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    response = _FakeResponse(status_code=503, payload={})

    class _Client:
        def get(self, url: str) -> _FakeResponse:  # pragma: no cover - simple stub
            return response

    middleware = HttpClientMiddleware(
        provider="chembl",
        http_client=_Client(),
        retry_policy=_RetryPolicyStub(max_attempts=1),
        logger=logging.getLogger("test_server_error"),
    )

    with pytest.raises(ClientResponseError):
        middleware.request("http://example.com")

    assert "HTTP request failed" in caplog.text


def test_retry_limit(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    policy = _RetryPolicyStub(max_attempts=2)

    class _Client:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, url: str) -> _FakeResponse:  # pragma: no cover - simple stub
            self.calls += 1
            raise TimeoutError("timeout")

    client = _Client()
    middleware = HttpClientMiddleware(
        provider="chembl",
        http_client=client,
        retry_policy=policy,
        logger=logging.getLogger("test_retry"),
    )

    with pytest.raises(ClientNetworkError):
        middleware.request("http://example.com")

    assert client.calls == policy.max_attempts
    assert len(policy.calls) == policy.max_attempts
    assert "Retrying request" in caplog.text
