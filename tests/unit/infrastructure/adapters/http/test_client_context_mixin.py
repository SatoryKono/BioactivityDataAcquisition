"""Unit tests for HTTPClientContextMixin."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.http.client_context_mixin import (
    HTTPClientContextMixin,
)

pytestmark = pytest.mark.unit


class _ContextHarness(HTTPClientContextMixin):
    def __init__(
        self,
        *,
        user_agent: str = "BioETL/1.0",
        contact_email: str | None = "team@example.org",
        run_id: object | None = "run-123",
        timeout: float = 10.0,
        max_connections: int = 20,
        max_keepalive_connections: int = 10,
    ) -> None:
        self._client = None
        self.user_agent = user_agent
        self.contact_email = contact_email
        self.run_id = run_id
        self.timeout = timeout
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections


@pytest.mark.asyncio
async def test_aenter_initializes_httpx_client_with_expected_headers() -> None:
    harness = _ContextHarness()

    entered = await harness.__aenter__()
    client = harness._get_client()

    assert entered is harness
    assert client.headers["User-Agent"] == "BioETL/1.0 (team@example.org)"
    assert client.headers["Accept"] == "application/json"
    assert client.headers["X-Correlation-ID"] == "run-123"

    await harness.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_aenter_omits_optional_headers_when_values_absent() -> None:
    harness = _ContextHarness(contact_email=None, run_id=None)

    await harness.__aenter__()
    client = harness._get_client()

    assert client.headers["User-Agent"] == "BioETL/1.0"
    assert "X-Correlation-ID" not in client.headers

    await harness.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_aexit_closes_client_and_resets_reference() -> None:
    harness = _ContextHarness()
    await harness.__aenter__()
    assert harness._client is not None

    await harness.__aexit__(None, None, None)

    assert harness._client is None


def test_get_client_raises_when_context_not_entered() -> None:
    harness = _ContextHarness()

    with pytest.raises(RuntimeError, match="must be used within async context manager"):
        _ = harness._get_client()
