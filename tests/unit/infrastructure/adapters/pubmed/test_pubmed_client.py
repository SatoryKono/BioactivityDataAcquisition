"""Unit tests for PubMedAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import RequestError

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter


@pytest.fixture
def mock_http_client():
    """Fixture for mock HTTP client."""
    return AsyncMock()


@pytest.fixture
def mock_logger():
    """Fixture for mock logger."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    """Fixture for PubMedAdapter instance."""
    return PubMedAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        email="test@example.com",
    )


@pytest.mark.asyncio
async def test_fetch_by_pmid_success(adapter, mock_http_client):
    """Test successful fetch_by_pmid."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {"12345": {"title": "Test Title"}}
    }
    mock_http_client.get.return_value = mock_response

    result = await adapter.fetch_by_pmid("12345")

    assert result == {"title": "Test Title"}
    mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_by_pmid_not_found(adapter, mock_http_client, mock_logger):
    """Test fetch_by_pmid when PMID is not found (404)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_http_client.get.return_value = mock_response

    result = await adapter.fetch_by_pmid("99999")

    assert result is None
    mock_logger.debug.assert_called_with(
        "pubmed_pmid_not_found",
        pmid="99999",
        status_code=404,
    )


@pytest.mark.asyncio
async def test_fetch_by_pmid_http_error(adapter, mock_http_client, mock_logger):
    """Test fetch_by_pmid with HTTP error (e.g., 500)."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http_client.get.return_value = mock_response

    result = await adapter.fetch_by_pmid("500error")

    assert result is None
    mock_logger.error.assert_called_with(
        "pubmed_api_error",
        pmid="500error",
        status_code=500,
        response_text=None,
    )


@pytest.mark.asyncio
async def test_fetch_by_pmid_request_error(adapter, mock_http_client, mock_logger):
    """Test fetch_by_pmid with a request error (e.g., network issue)."""
    mock_http_client.get.side_effect = RequestError("Network error")

    result = await adapter.fetch_by_pmid("network-error")

    assert result is None
    mock_logger.error.assert_called_with(
        "pubmed_request_failed",
        pmid="network-error",
        error="Network error",
    )


@pytest.mark.asyncio
async def test_health_check_healthy(adapter, mock_http_client):
    """Test health_check returns HEALTHY on success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get.return_value = mock_response

    result = await adapter.health_check()

    assert result == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_check_unhealthy_on_error(adapter, mock_http_client):
    """Test health_check returns UNHEALTHY on HTTP error."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_http_client.get.return_value = mock_response

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_health_check_unhealthy_on_request_error(adapter, mock_http_client):
    """Test health_check returns UNHEALTHY on request error."""
    mock_http_client.get.side_effect = RequestError("Connection refused")

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY


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

    def mock_monotonic_func():
        nonlocal call_count
        call_count += 1
        # First call (start_time) returns 0, subsequent calls return 6 (elapsed = 6 sec)
        return 0.0 if call_count <= 2 else 6.0

    mock_monotonic = MagicMock(side_effect=mock_monotonic_func)

    with patch(
        "bioetl.infrastructure.adapters.pubmed.pubmed_client.time.monotonic",
        new=mock_monotonic,
    ), patch(
        "bioetl.infrastructure.adapters.health_check_mixin.time.monotonic",
        new=mock_monotonic,
    ):
        result = await adapter.health_check()

    assert result == HealthStatus.DEGRADED
