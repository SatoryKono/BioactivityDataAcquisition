"""Unit tests for CrossRefAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter,
    _create_crossref_adapter,
)
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
        batch_size=50,
    )


# =============================================================================
# Initialization tests
# =============================================================================


def test_adapter_provider_name(adapter):
    """Test adapter has correct provider name."""
    assert adapter.provider_name == "crossref"


def test_adapter_mailto_stored(adapter):
    """Test adapter stores mailto correctly."""
    assert adapter.mailto == "test@example.com"


def test_adapter_batch_size_default():
    """Test adapter uses default batch size."""
    adapter = CrossRefAdapter(
        http_client=MagicMock(),
        logger=MagicMock(),
        mailto="test@example.com",
    )
    assert adapter.batch_size == 50


# =============================================================================
# Context manager tests
# =============================================================================


@pytest.mark.asyncio
async def test_context_manager_closes_resources(adapter, mock_http_client):
    """Test that context manager properly closes resources."""
    async with adapter as a:
        assert a is adapter
        mock_http_client.__aenter__.assert_called_once()

    mock_http_client.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_aclose_closes_http_client(adapter, mock_http_client):
    """Test that aclose() properly closes the HTTP client."""
    await adapter.aclose()
    mock_http_client.__aexit__.assert_called_once_with(None, None, None)


@pytest.mark.asyncio
async def test_aclose_idempotent(adapter, mock_http_client):
    """Test that aclose() can be called multiple times safely."""
    await adapter.aclose()
    mock_http_client.__aexit__.assert_called_once_with(None, None, None)

    await adapter.aclose()
    assert mock_http_client.__aexit__.call_count == 2


@pytest.mark.asyncio
async def test_aclose_with_none_http_client(mock_logger):
    """Test aclose() handles None http_client gracefully."""
    adapter = CrossRefAdapter(
        http_client=None,  # type: ignore[arg-type]
        logger=mock_logger,
        mailto="test@example.com",
    )
    await adapter.aclose()


# =============================================================================
# Health check tests
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
        "bioetl.infrastructure.adapters.crossref.client.time.monotonic",
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
        call[0][0] == "crossref_health_check_slow"
        for call in mock_logger.warning.call_args_list
    )
    assert slow_warning_found, "Expected 'crossref_health_check_slow' warning to be logged"


# =============================================================================
# DOI normalization tests
# =============================================================================


def test_normalize_doi_lowercase(adapter):
    """Test DOI normalization converts to lowercase."""
    result = adapter._normalize_doi("10.1234/ABC.DEF")
    assert result == "10.1234/abc.def"


def test_normalize_doi_strips_whitespace(adapter):
    """Test DOI normalization strips whitespace."""
    result = adapter._normalize_doi("  10.1234/test  ")
    assert result == "10.1234/test"


# =============================================================================
# Fetch single work tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_single_work_success(adapter, mock_http_client):
    """Test successful single work fetch."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "DOI": "10.1234/test",
            "title": ["Test Title"],
        }
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter._fetch_single_work("10.1234/test")

    assert result is not None
    assert result["DOI"] == "10.1234/test"


@pytest.mark.asyncio
async def test_fetch_single_work_not_found(adapter, mock_http_client, mock_logger):
    """Test fetch returns None for 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_http_client.get = AsyncMock(return_value=mock_response)

    result = await adapter._fetch_single_work("10.1234/nonexistent")

    assert result is None
    mock_logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_single_work_api_error(adapter, mock_http_client):
    """Test fetch raises CrossRefApiError on non-200/404."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http_client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(CrossRefApiError):
        await adapter._fetch_single_work("10.1234/test")


# =============================================================================
# Fetch filtered tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_filtered_valid_entity_types(adapter, mock_http_client):
    """Test fetch_filtered accepts 'work' and 'publication' entity types."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"items": []}}
    mock_http_client.get = AsyncMock(return_value=mock_response)

    results = []
    async for work in adapter.fetch_filtered("work", ["10.1234/test"], "doi", limit=10):
        results.append(work)

    assert results == []


@pytest.mark.asyncio
async def test_fetch_filtered_invalid_entity_type(adapter):
    """Test fetch_filtered raises ValueError for invalid entity type."""
    with pytest.raises(ValueError, match="supports 'work' or 'publication'"):
        async for _ in adapter.fetch_filtered("invalid", ["10.1234/test"], "doi"):
            pass


@pytest.mark.asyncio
async def test_fetch_filtered_with_results(adapter, mock_http_client):
    """Test fetch_filtered yields work records."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "items": [
                {"DOI": "10.1234/test1", "title": ["Title 1"]},
                {"DOI": "10.1234/test2", "title": ["Title 2"]},
            ]
        }
    }
    mock_http_client.get = AsyncMock(return_value=mock_response)

    results = []
    async for work in adapter.fetch_filtered(
        "publication", ["10.1234/test1", "10.1234/test2"], "doi"
    ):
        results.append(work)

    assert len(results) == 2


# =============================================================================
# Fetch tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_with_filter_ids(adapter, mock_http_client):
    """Test fetch delegates to fetch_filtered when filter_ids provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"items": []}}
    mock_http_client.get = AsyncMock(return_value=mock_response)

    results = []
    async for work in adapter.fetch(
        "work",
        filter_ids=["10.1234/test"],
        filter_field="doi",
    ):
        results.append(work)

    assert results == []


@pytest.mark.asyncio
async def test_fetch_without_query_raises_error(adapter):
    """Test fetch raises ValueError when no filter_ids or query."""
    with pytest.raises(ValueError, match="requires either filter_ids"):
        async for _ in adapter.fetch("work"):
            pass


@pytest.mark.asyncio
async def test_fetch_with_query(adapter, mock_http_client):
    """Test fetch with query performs search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"items": []}}
    mock_http_client.get = AsyncMock(return_value=mock_response)

    results = []
    async for work in adapter.fetch("work", query="cancer research"):
        results.append(work)

    assert results == []


# =============================================================================
# Headers tests
# =============================================================================


def test_build_headers_includes_mailto(adapter):
    """Test headers include mailto in User-Agent."""
    headers = adapter._build_headers()

    assert "User-Agent" in headers
    assert "test@example.com" in headers["User-Agent"]
    assert headers["Accept"] == "application/json"


# =============================================================================
# Factory function tests
# =============================================================================


def test_create_crossref_adapter_success():
    """Test factory creates adapter with all required args."""
    http_client = MagicMock()
    logger = MagicMock()
    settings = MagicMock()
    settings.default_email = "settings@example.com"

    adapter = _create_crossref_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
    )

    assert adapter.mailto == "settings@example.com"
    assert adapter.http_client is http_client
    assert adapter.logger is logger


def test_create_crossref_adapter_mailto_from_kwargs():
    """Test factory uses mailto from kwargs over settings."""
    http_client = MagicMock()
    logger = MagicMock()
    settings = MagicMock()
    settings.default_email = "settings@example.com"

    adapter = _create_crossref_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
        mailto="kwargs@example.com",
    )

    assert adapter.mailto == "kwargs@example.com"


def test_create_crossref_adapter_missing_mailto():
    """Test factory raises ValueError without mailto."""
    with pytest.raises(ValueError, match="requires mailto"):
        _create_crossref_adapter(
            http_client=MagicMock(),
            logger=MagicMock(),
            settings=None,
        )


def test_create_crossref_adapter_missing_http_client():
    """Test factory raises ValueError without http_client."""
    with pytest.raises(ValueError, match="requires http_client"):
        _create_crossref_adapter(
            http_client=None,
            logger=MagicMock(),
            settings=None,
            mailto="test@example.com",
        )


def test_create_crossref_adapter_missing_logger():
    """Test factory raises ValueError without logger."""
    with pytest.raises(ValueError, match="requires logger"):
        _create_crossref_adapter(
            http_client=MagicMock(),
            logger=None,
            settings=None,
            mailto="test@example.com",
        )
