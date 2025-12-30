"""Unit tests for CrossRefAdapter.

Tests the CrossRef adapter's health check, lifecycle, and data fetching methods.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client._client = AsyncMock()
    client._client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    """Create a CrossRefAdapter with mock http client."""
    return CrossRefAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        mailto="test@example.com",
    )


# =============================================================================
# Lifecycle Tests
# =============================================================================


@pytest.mark.asyncio
async def test_aclose_closes_http_client(adapter, mock_http_client):
    """Test that aclose() properly closes the HTTP client."""
    await adapter.aclose()

    # aclose uses __aexit__ for cleanup
    mock_http_client.__aexit__.assert_called_once_with(None, None, None)


@pytest.mark.asyncio
async def test_aclose_idempotent(adapter, mock_http_client):
    """Test that aclose() can be called multiple times safely."""
    await adapter.aclose()
    mock_http_client.__aexit__.assert_called_once_with(None, None, None)

    # Second call should also work
    await adapter.aclose()
    assert mock_http_client.__aexit__.call_count == 2


# =============================================================================
# Health Check Tests
# =============================================================================


@pytest.mark.asyncio
async def test_health_check_returns_healthy_on_success(adapter, mock_http_client):
    """Test health_check returns HEALTHY on 200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_on_non_200(
    adapter, mock_http_client, mock_logger
):
    """Test health_check returns UNHEALTHY on non-200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY
    mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_health_check_returns_degraded_on_slow_response(
    adapter, mock_http_client, mock_logger
):
    """Test _probe_health returns DEGRADED when response takes >5 seconds.

    Tests the internal _probe_health method directly since it contains
    the slow response detection logic.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get = AsyncMock(return_value=mock_response)

    # Mock time.monotonic to simulate slow response
    import bioetl.infrastructure.adapters.crossref.client as crossref_module

    original_monotonic = crossref_module.time.monotonic
    call_count = [0]  # Use list to allow modification in closure

    def mock_monotonic():
        call_count[0] += 1
        # First call returns 0, second call returns 6
        return 0.0 if call_count[0] == 1 else 6.0

    crossref_module.time.monotonic = mock_monotonic
    try:
        result = await adapter._probe_health()
    finally:
        crossref_module.time.monotonic = original_monotonic

    assert result == HealthStatus.DEGRADED
    # Verify a slow response warning was logged
    mock_logger.warning.assert_called_once()
    call_args = mock_logger.warning.call_args
    assert call_args[0][0] == "crossref_health_check_slow"


@pytest.mark.asyncio
async def test_health_check_logs_error_on_exception(
    adapter, mock_http_client, mock_logger
):
    """Test health_check logs error details on exception."""
    mock_http_client.get = AsyncMock(side_effect=Exception("Network timeout"))

    await adapter.health_check()

    # Warning is logged
    assert mock_logger.warning.called
    # Find the health_check_failed warning
    failed_warning_found = any(
        "crossref_health_check_failed" in str(call)
        for call in mock_logger.warning.call_args_list
    )
    assert failed_warning_found, "Expected health check warning to be logged"


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_on_exception(adapter, mock_http_client):
    """Test health_check returns UNHEALTHY when exception occurs."""
    mock_http_client.get = AsyncMock(side_effect=Exception("Connection refused"))

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY


# =============================================================================
# Provider Name Tests
# =============================================================================


def test_provider_name(adapter):
    """Test that provider_name is set correctly."""
    assert adapter.provider_name == "crossref"


def test_health_endpoint(adapter):
    """Test that health endpoint is correct."""
    assert adapter._get_health_endpoint() == "/works"


# =============================================================================
# Fetch Single Work Tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_single_work_success(adapter, mock_http_client):
    """Test successful single work fetch."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"title": ["Test Title"]}}
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter._fetch_single_work("10.1234/test")

    assert result == {"title": ["Test Title"]}


@pytest.mark.asyncio
async def test_fetch_single_work_not_found(adapter, mock_http_client, mock_logger):
    """Test _fetch_single_work when DOI is not found (404)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter._fetch_single_work("10.1234/notfound")

    assert result is None
    mock_logger.debug.assert_called_with(
        "crossref_doi_not_found",
        doi="10.1234/notfound",
    )


@pytest.mark.asyncio
async def test_fetch_single_work_http_error(adapter, mock_http_client):
    """Test _fetch_single_work with HTTP error (e.g., 500)."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http_client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(CrossRefApiError):
        await adapter._fetch_single_work("10.1234/error")


@pytest.mark.asyncio
async def test_fetch_single_work_network_error(adapter, mock_http_client, mock_logger):
    """Test _fetch_single_work with a network error."""
    mock_http_client.get = AsyncMock(side_effect=Exception("Network error"))

    with pytest.raises(CrossRefApiError) as exc_info:
        await adapter._fetch_single_work("10.1234/network-error")

    assert "Network error" in str(exc_info.value)
    mock_logger.error.assert_called()


# =============================================================================
# Fetch Interface Tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_with_filter_ids(adapter, mock_http_client):
    """Test fetch() with filter_ids delegates to fetch_filtered."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"items": [{"DOI": "10.1234/test", "title": ["Test"]}]}
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    results = []
    async for work in adapter.fetch(
        entity_type="work",
        filter_ids=["10.1234/test"],
        filter_field="doi",
    ):
        results.append(work)

    assert len(results) == 1


@pytest.mark.asyncio
async def test_fetch_requires_query_or_filter_ids(adapter):
    """Test fetch() raises ValueError if no query or filter_ids."""
    with pytest.raises(ValueError) as exc_info:
        async for _ in adapter.fetch(entity_type="work"):
            pass

    assert "requires either filter_ids" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_invalid_entity_type(adapter):
    """Test fetch() raises ValueError for invalid entity type."""
    with pytest.raises(ValueError) as exc_info:
        async for _ in adapter.fetch(entity_type="invalid", query="test"):
            pass

    assert "supports 'work' or 'publication'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_filtered_invalid_entity_type(adapter):
    """Test fetch_filtered() raises ValueError for invalid entity type."""
    with pytest.raises(ValueError) as exc_info:
        async for _ in adapter.fetch_filtered(
            entity_type="invalid",
            filter_ids=["10.1234/test"],
            filter_field="doi",
        ):
            pass

    assert "supports 'work' or 'publication'" in str(exc_info.value)
