from __future__ import annotations

# tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py
"""Unit tests for PubMedAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    # Simulate the internal _client (httpx.AsyncClient)
    client._client = AsyncMock()
    client._client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    """Create a PubMedAdapter with mock http client."""
    return PubMedAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        email="test@example.com",
        api_key=None,
    )


@pytest.mark.asyncio
async def test_aclose_closes_http_client(adapter, mock_http_client):
    """Test that aclose() properly closes the HTTP client."""
    await adapter.aclose()

    # aclose uses __aexit__ for cleanup
    mock_http_client.__aexit__.assert_called_once_with(None, None, None)


@pytest.mark.asyncio
async def test_aclose_idempotent(adapter, mock_http_client):
    """Test that aclose() can be called multiple times safely."""
    # First call should close
    await adapter.aclose()
    mock_http_client.__aexit__.assert_called_once_with(None, None, None)

    # Second call should also work (still has http_client reference)
    await adapter.aclose()

    # __aexit__ was called twice (once per invocation)
    assert mock_http_client.__aexit__.call_count == 2


@pytest.mark.asyncio
async def test_aclose_handles_missing_client_attribute(adapter, mock_http_client):
    """Test aclose() handles missing _client attribute gracefully."""
    # Remove _client attribute to simulate uninitialized state
    del mock_http_client._client

    # Should not raise
    await adapter.aclose()


@pytest.mark.asyncio
async def test_aclose_handles_none_client(adapter, mock_http_client):
    """Test aclose() handles None _client gracefully."""
    mock_http_client._client = None

    # Should not raise
    await adapter.aclose()


@pytest.mark.asyncio
async def test_aclose_with_none_http_client(mock_logger):
    """Test aclose() handles None http_client gracefully."""
    adapter = PubMedAdapter(
        http_client=None,  # type: ignore[arg-type]
        logger=mock_logger,
        email="test@example.com",
    )

    # Should not raise
    await adapter.aclose()


@pytest.mark.asyncio
async def test_context_manager_closes_resources(adapter, mock_http_client):
    """Test that context manager properly closes resources."""
    async with adapter as a:
        assert a is adapter
        mock_http_client.__aenter__.assert_called_once()

    mock_http_client.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_aclose_no_resource_leak_after_context_exit(adapter):
    """Test no resource leak when aclose is called after context exit."""
    async with adapter:
        pass

    # After context exit, _client should still be closable via aclose
    # In real usage, __aexit__ already closed it, but aclose should be safe
    await adapter.aclose()


# =============================================================================
# health_check tests
# =============================================================================


@pytest.mark.asyncio
async def test_health_check_returns_healthy(adapter, mock_http_client):
    """Test health_check returns HEALTHY when API responds 200 quickly."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.HEALTHY
    mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_on_error(adapter, mock_http_client):
    """Test health_check returns UNHEALTHY on exception."""
    mock_http_client.get = AsyncMock(side_effect=Exception("Connection error"))

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_on_non_200(
    adapter, mock_http_client, mock_logger
):
    """Test health_check returns UNHEALTHY on non-200 status code."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY
    mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_returns_degraded_on_slow_response(
    adapter, mock_http_client, mock_logger
):
    """Test health_check returns DEGRADED when response takes >5 seconds."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get = AsyncMock(return_value=mock_response)

    # Simulate slow response by patching time.monotonic in both modules
    # (adapter module and health_check_mixin where HealthCheckContext uses it)
    call_count = 0

    def mock_monotonic():
        nonlocal call_count
        call_count += 1
        # First call (start_time) returns 0, subsequent calls return 6 (elapsed = 6 sec)
        return 0.0 if call_count == 1 else 6.0

    with patch(
        "bioetl.infrastructure.adapters.pubmed.pubmed_client.time.monotonic",
        side_effect=mock_monotonic,
    ), patch(
        "bioetl.infrastructure.adapters.health_check_mixin.time.monotonic",
        side_effect=mock_monotonic,
    ):
        result = await adapter.health_check()

    assert result == HealthStatus.DEGRADED
    # Verify a slow response warning was logged
    assert mock_logger.warning.called
    # Find the slow response warning among the calls
    slow_warning_found = any(
        call[0][0] == "pubmed_health_check_slow"
        for call in mock_logger.warning.call_args_list
    )
    assert slow_warning_found, "Expected 'pubmed_health_check_slow' warning to be logged"


@pytest.mark.asyncio
async def test_health_check_logs_error_on_exception(
    adapter, mock_http_client, mock_logger
):
    """Test health_check logs error details on exception."""
    mock_http_client.get = AsyncMock(side_effect=Exception("Network timeout"))

    await adapter.health_check()

    # Warning is logged twice: once in _probe_health() and once in _handle_health_check_failure()
    assert mock_logger.warning.called
    # Find the health_check_failed warning with Network timeout
    failed_warning_found = any(
        call[0][0] == "health_check_failed" and "Network timeout" in str(call[1].get("error", "") or call[1].get("error_message", ""))
        for call in mock_logger.warning.call_args_list
    )
    assert failed_warning_found, "Expected 'health_check_failed' warning with 'Network timeout' to be logged"
