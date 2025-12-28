# tests/unit/infrastructure/adapters/crossref/test_crossref_client.py
"""Unit tests for CrossRefAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    # Simulate the internal _client (httpx.AsyncClient)
    client._client = AsyncMock()
    client._client.aclose = AsyncMock()
    # Add circuit_breaker for fallback health status
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.state = "closed"
    return client


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    """Create a CrossRefAdapter with mock http client."""
    return CrossRefAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        mailto="test@example.com",
    )


# =============================================================================
# Provider name tests
# =============================================================================


def test_provider_name(adapter):
    """Test provider_name is 'crossref'."""
    assert adapter.provider_name == "crossref"


# =============================================================================
# Context manager tests
# =============================================================================


@pytest.mark.asyncio
async def test_context_manager_opens_and_closes(adapter, mock_http_client):
    """Test context manager properly opens and closes resources."""
    async with adapter as a:
        assert a is adapter
        mock_http_client.__aenter__.assert_called_once()

    mock_http_client.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_aclose_is_safe(adapter, mock_http_client):
    """Test that aclose() is safe to call."""
    await adapter.aclose()
    # BaseHttpAdapter.aclose is a no-op, but should not raise


# =============================================================================
# DOI normalization tests
# =============================================================================


def test_normalize_doi_lowercase():
    """Test DOI normalization lowercases the DOI."""
    assert CrossRefAdapter._normalize_doi("10.1234/ABC") == "10.1234/abc"


def test_normalize_doi_strip_whitespace():
    """Test DOI normalization strips whitespace."""
    assert CrossRefAdapter._normalize_doi("  10.1234/abc  ") == "10.1234/abc"


def test_normalize_doi_removes_doi_org_prefix():
    """Test DOI normalization removes doi.org URL prefix."""
    assert CrossRefAdapter._normalize_doi("https://doi.org/10.1234/abc") == "10.1234/abc"
    assert CrossRefAdapter._normalize_doi("http://doi.org/10.1234/abc") == "10.1234/abc"


def test_normalize_doi_removes_dx_prefix():
    """Test DOI normalization removes dx.doi.org prefix."""
    assert CrossRefAdapter._normalize_doi("https://dx.doi.org/10.1234/abc") == "10.1234/abc"


def test_normalize_doi_removes_doi_colon_prefix():
    """Test DOI normalization removes 'doi:' prefix."""
    assert CrossRefAdapter._normalize_doi("doi:10.1234/abc") == "10.1234/abc"


# =============================================================================
# Health check tests
# =============================================================================


@pytest.mark.asyncio
async def test_health_check_returns_healthy(adapter, mock_http_client):
    """Test health_check returns HEALTHY when API responds 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": [], "total-results": 100},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.HEALTHY
    mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_on_error(adapter, mock_http_client):
    """Test health_check uses fallback on exception."""
    mock_http_client.get = AsyncMock(side_effect=Exception("Connection error"))

    result = await adapter.health_check()

    # With consecutive errors, health degrades
    assert result in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED)


@pytest.mark.asyncio
async def test_health_check_returns_degraded_on_non_200(
    adapter, mock_http_client, mock_logger
):
    """Test health_check returns DEGRADED on non-200 status code."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.DEGRADED
    mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_health_check_adds_mailto_param(adapter, mock_http_client):
    """Test health_check adds mailto parameter when configured."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get = AsyncMock(return_value=mock_response)

    await adapter.health_check()

    # Verify mailto was passed in params
    call_args = mock_http_client.get.call_args
    params = call_args.kwargs.get("params", {})
    assert params.get("mailto") == "test@example.com"


# =============================================================================
# Fetch tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_rejects_invalid_entity_type(adapter):
    """Test fetch raises ValueError for invalid entity type."""
    with pytest.raises(ValueError, match="CrossRefAdapter only supports"):
        async for _ in adapter.fetch("invalid_type"):
            pass


@pytest.mark.asyncio
async def test_fetch_accepts_publication_entity_type(adapter, mock_http_client):
    """Test fetch accepts 'publication' entity type."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": [], "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    records = [r async for r in adapter.fetch("publication", limit=10)]

    assert records == []
    mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_accepts_work_entity_type(adapter, mock_http_client):
    """Test fetch accepts 'work' entity type."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": [], "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    records = [r async for r in adapter.fetch("work", limit=10)]

    assert records == []


@pytest.mark.asyncio
async def test_fetch_yields_records(adapter, mock_http_client):
    """Test fetch yields records from API response."""
    test_records = [
        {"DOI": "10.1234/test1", "title": ["Test Paper 1"]},
        {"DOI": "10.1234/test2", "title": ["Test Paper 2"]},
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": test_records, "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    records = [r async for r in adapter.fetch("publication")]

    assert len(records) == 2
    assert records[0]["DOI"] == "10.1234/test1"
    assert records[1]["DOI"] == "10.1234/test2"


@pytest.mark.asyncio
async def test_fetch_respects_limit(adapter, mock_http_client):
    """Test fetch respects limit parameter."""
    test_records = [
        {"DOI": f"10.1234/test{i}", "title": [f"Test Paper {i}"]}
        for i in range(10)
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": test_records, "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    records = [r async for r in adapter.fetch("publication", limit=3)]

    assert len(records) == 3


@pytest.mark.asyncio
async def test_fetch_handles_pagination(adapter, mock_http_client):
    """Test fetch handles cursor-based pagination."""
    page1_records = [{"DOI": "10.1234/page1", "title": ["Page 1"]}]
    page2_records = [{"DOI": "10.1234/page2", "title": ["Page 2"]}]

    # Create mock responses for pagination
    page1_response = MagicMock()
    page1_response.status_code = 200
    page1_response.json.return_value = {
        "status": "ok",
        "message": {"items": page1_records, "next-cursor": "cursor123"},
    }

    page2_response = MagicMock()
    page2_response.status_code = 200
    page2_response.json.return_value = {
        "status": "ok",
        "message": {"items": page2_records, "next-cursor": None},
    }

    mock_http_client.get = AsyncMock(side_effect=[page1_response, page2_response])

    records = [r async for r in adapter.fetch("publication")]

    assert len(records) == 2
    assert records[0]["DOI"] == "10.1234/page1"
    assert records[1]["DOI"] == "10.1234/page2"
    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_deduplicates_by_doi(adapter, mock_http_client):
    """Test fetch deduplicates records by DOI."""
    # Same DOI appears twice (different case)
    test_records = [
        {"DOI": "10.1234/TEST", "title": ["First"]},
        {"DOI": "10.1234/test", "title": ["Duplicate"]},
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": test_records, "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    records = [r async for r in adapter.fetch("publication")]

    assert len(records) == 1


@pytest.mark.asyncio
async def test_fetch_adds_mailto_to_params(adapter, mock_http_client):
    """Test fetch adds mailto parameter for polite pool access."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": [], "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    [r async for r in adapter.fetch("publication")]

    call_args = mock_http_client.get.call_args
    params = call_args.kwargs.get("params", {})
    assert params.get("mailto") == "test@example.com"


@pytest.mark.asyncio
async def test_fetch_without_mailto(mock_http_client, mock_logger):
    """Test fetch works without mailto configured."""
    adapter = CrossRefAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        mailto=None,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": [], "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    [r async for r in adapter.fetch("publication")]

    call_args = mock_http_client.get.call_args
    params = call_args.kwargs.get("params", {})
    assert "mailto" not in params


# =============================================================================
# fetch_filtered tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_filtered_by_dois(adapter, mock_http_client):
    """Test fetch_filtered fetches specific DOIs."""
    test_records = [{"DOI": "10.1234/specific", "title": ["Specific Paper"]}]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"items": test_records, "next-cursor": None},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    records = [
        r
        async for r in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["10.1234/specific"],
            filter_field="doi",
        )
    ]

    assert len(records) == 1
    assert records[0]["DOI"] == "10.1234/specific"


# =============================================================================
# Error handling tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_updates_health_on_errors(adapter, mock_http_client):
    """Test fetch updates health status after consecutive errors."""
    mock_http_client.get = AsyncMock(side_effect=Exception("API error"))

    # Initial health should be HEALTHY
    assert adapter._cached_health == HealthStatus.HEALTHY

    # Try to fetch (will fail)
    with pytest.raises(Exception, match="API error"):
        async for _ in adapter.fetch("publication"):
            pass

    # After error, health should be DEGRADED
    assert adapter._cached_health == HealthStatus.DEGRADED


def test_reset_error_counters(adapter, mock_logger):
    """Test reset_error_counters resets all error state."""
    # Simulate some errors
    adapter._consecutive_errors = 5
    adapter._total_errors = 10
    adapter._cached_health = HealthStatus.UNHEALTHY

    adapter.reset_error_counters()

    assert adapter._consecutive_errors == 0
    assert adapter._total_errors == 0
    assert adapter._cached_health == HealthStatus.HEALTHY
    mock_logger.info.assert_called_with(
        "crossref_error_counters_reset",
        provider="crossref",
    )


def test_get_error_stats(adapter):
    """Test get_error_stats returns correct statistics."""
    adapter._consecutive_errors = 2
    adapter._total_errors = 5
    adapter._cached_health = HealthStatus.DEGRADED

    stats = adapter.get_error_stats()

    assert stats["consecutive_errors"] == 2
    assert stats["total_errors"] == 5
    assert stats["health_status"] == "degraded"


# =============================================================================
# get_entity_count tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_entity_count(adapter, mock_http_client):
    """Test get_entity_count returns total works count."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "message": {"total-results": 150000000},
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    count = await adapter.get_entity_count("publication")

    assert count == 150000000
    # Verify rows=0 was passed (minimal query)
    call_args = mock_http_client.get.call_args
    params = call_args.kwargs.get("params", {})
    assert params.get("rows") == 0


# =============================================================================
# Batch size adjustment tests
# =============================================================================


def test_get_effective_batch_size_healthy(adapter):
    """Test effective batch size is normal when HEALTHY."""
    adapter._cached_health = HealthStatus.HEALTHY
    adapter.batch_size = 100

    assert adapter._get_effective_batch_size() == 100


def test_get_effective_batch_size_degraded(adapter, mock_logger):
    """Test effective batch size is halved when DEGRADED."""
    adapter._cached_health = HealthStatus.DEGRADED
    adapter.batch_size = 100

    result = adapter._get_effective_batch_size()

    assert result == 50
    mock_logger.warning.assert_called_once()


def test_get_effective_batch_size_degraded_min_20(adapter):
    """Test effective batch size has minimum of 20 when DEGRADED."""
    adapter._cached_health = HealthStatus.DEGRADED
    adapter.batch_size = 30

    result = adapter._get_effective_batch_size()

    assert result == 20  # min(30/2, 20) = 15, but min is 20


def test_get_effective_batch_size_unhealthy_raises(adapter):
    """Test CriticalError is raised when UNHEALTHY."""
    from bioetl.domain.exceptions import CriticalError

    adapter._cached_health = HealthStatus.UNHEALTHY
    adapter._consecutive_errors = 5

    with pytest.raises(CriticalError, match="CrossRef adapter is UNHEALTHY"):
        adapter._get_effective_batch_size()
