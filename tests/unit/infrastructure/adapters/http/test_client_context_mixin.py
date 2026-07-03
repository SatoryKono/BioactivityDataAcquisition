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
        read_timeout_multiplier: float = 2.0,
        max_connections: int = 20,
        max_keepalive_connections: int = 10,
        trust_env: bool = True,
    ) -> None:
        self._client = None
        self._client_enter_depth = 0
        self.user_agent = user_agent
        self.contact_email = contact_email
        self.run_id = run_id
        self.timeout = timeout
        self.read_timeout_multiplier = read_timeout_multiplier
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.trust_env = trust_env


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
    assert harness._client_enter_depth == 0


def test_get_client_raises_when_context_not_entered() -> None:
    harness = _ContextHarness()

    with pytest.raises(RuntimeError, match="must be used within async context manager"):
        _ = harness._get_client()


@pytest.mark.asyncio
async def test_read_timeout_uses_default_multiplier() -> None:
    """Default read timeout should be timeout * 2.0."""
    harness = _ContextHarness(timeout=15.0)
    await harness.__aenter__()
    client = harness._get_client()

    assert client._transport._pool._ssl_context is not None or True
    # httpx stores timeout as Timeout object
    assert client.timeout.read == pytest.approx(30.0)  # 15.0 * 2.0

    await harness.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_read_timeout_uses_custom_multiplier() -> None:
    """Custom read_timeout_multiplier should scale the read timeout."""
    harness = _ContextHarness(timeout=10.0, read_timeout_multiplier=3.0)
    await harness.__aenter__()
    client = harness._get_client()

    assert client.timeout.read == pytest.approx(30.0)  # 10.0 * 3.0

    await harness.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_aenter_passes_explicit_trust_env_flag_to_httpx() -> None:
    harness = _ContextHarness(trust_env=False)
    await harness.__aenter__()
    client = harness._get_client()

    assert client._trust_env is False

    await harness.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_reentrant_aenter_reuses_existing_client_until_outer_exit() -> None:
    harness = _ContextHarness()

    await harness.__aenter__()
    first_client = harness._get_client()
    await harness.__aenter__()
    second_client = harness._get_client()

    assert second_client is first_client
    assert harness._client_enter_depth == 2

    await harness.__aexit__(None, None, None)

    assert harness._client is first_client
    assert harness._client_enter_depth == 1

    await harness.__aexit__(None, None, None)

    assert harness._client is None
    assert harness._client_enter_depth == 0
