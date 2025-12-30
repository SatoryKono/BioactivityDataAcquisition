"""Unit tests for CrossRefAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import RequestError

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError


@pytest.fixture
def mock_http_client():
    """Fixture for mock HTTP client."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client._client = AsyncMock()
    client._client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_logger():
    """Fixture for mock logger."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    """Fixture for CrossRefAdapter instance."""
    return CrossRefAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        mailto="test@example.com",
    )


@pytest.mark.asyncio
async def test_fetch_single_work_success(adapter, mock_http_client):
    """Test successful fetch_single_work."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"title": ["Test Title"]}}
    mock_http_client.get.return_value = mock_response

    result = await adapter._fetch_single_work("10.1234/test")

    assert result == {"title": ["Test Title"]}
    mock_http_client.get.assert_called_once_with(
        "https://api.crossref.org/works/10.1234/test",
        headers={"User-Agent": "BioETL/1.0 (mailto:test@example.com)", "Accept": "application/json"},
    )


@pytest.mark.asyncio
async def test_fetch_single_work_not_found(adapter, mock_http_client, mock_logger):
    """Test fetch_single_work when DOI is not found (404)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_http_client.get.return_value = mock_response

    result = await adapter._fetch_single_work("10.1234/notfound")

    assert result is None
    mock_logger.debug.assert_called_with(
        "crossref_doi_not_found",
        doi="10.1234/notfound",
    )


@pytest.mark.asyncio
async def test_fetch_single_work_http_error(adapter, mock_http_client):
    """Test fetch_single_work with HTTP error (e.g., 500)."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http_client.get.return_value = mock_response

    with pytest.raises(CrossRefApiError):
        await adapter._fetch_single_work("10.1234/error")


@pytest.mark.asyncio
async def test_fetch_single_work_request_error(adapter, mock_http_client, mock_logger):
    """Test fetch_single_work with a request error (e.g., network issue)."""
    mock_http_client.get.side_effect = RequestError("Network error")

    with pytest.raises(CrossRefApiError):
        await adapter._fetch_single_work("10.1234/network-error")

    mock_logger.error.assert_called()


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
        "bioetl.infrastructure.adapters.crossref.client.time.monotonic",
        new=mock_monotonic,
    ), patch(
        "bioetl.infrastructure.adapters.health_check_mixin.time.monotonic",
        new=mock_monotonic,
    ):
        result = await adapter.health_check()

    assert result == HealthStatus.DEGRADED
