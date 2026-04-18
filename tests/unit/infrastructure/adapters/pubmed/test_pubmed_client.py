"""Unit tests for PubMedAdapter.

Tests the PubMed adapter's health check and lifecycle methods.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


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
    """Create a PubMedAdapter with mock http client."""
    return PubMedAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        email="test@example.com",
        api_key=None,
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=mock_logger,
            include_fallback_service=True,
        ),
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
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_check_returns_degraded_on_transient_non_200(
    adapter, mock_http_client, mock_logger
):
    """Test health_check returns DEGRADED on transient non-200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.DEGRADED
    mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_on_auth_non_200(
    adapter, mock_http_client, mock_logger
):
    """Test health_check returns UNHEALTHY on auth-related response codes."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY
    mock_logger.warning.assert_called_once()


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
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    # Mock time.monotonic to simulate slow response
    # _probe_health does: start_time = time.monotonic() then elapsed = time.monotonic() - start_time
    # We need elapsed > 5.0
    import bioetl.infrastructure.adapters.pubmed._health as health_module

    original_monotonic = health_module.time.monotonic
    call_count = [0]  # Use list to allow modification in closure

    def mock_monotonic():
        call_count[0] += 1
        # First call returns 0, second call returns 6
        return 0.0 if call_count[0] == 1 else 6.0

    health_module.time.monotonic = mock_monotonic
    try:
        result = await adapter._probe_health()
    finally:
        health_module.time.monotonic = original_monotonic

    assert result == HealthStatus.DEGRADED
    # Verify a slow response warning was logged
    mock_logger.warning.assert_called_once()
    call_args = mock_logger.warning.call_args
    assert call_args[0][0] == "pubmed_health_check_slow"


@pytest.mark.asyncio
async def test_health_check_logs_error_on_exception(
    adapter, mock_http_client, mock_logger
):
    """Test health_check logs error details on exception."""
    mock_http_client.get_once = AsyncMock(side_effect=RuntimeError("Network timeout"))

    await adapter.health_check()

    # Warning is logged (may be called multiple times due to error handling chain)
    assert mock_logger.warning.called
    # Find the health_check_failed warning with Network timeout
    failed_warning_found = any(
        call[0][0] == "health_check_failed"
        and "Network timeout"
        in str(call[1].get("error", "") or call[1].get("error_message", ""))
        for call in mock_logger.warning.call_args_list
    )
    assert failed_warning_found, (
        "Expected 'health_check_failed' warning with 'Network timeout' to be logged"
    )


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_on_exception(adapter, mock_http_client):
    """Test health_check returns UNHEALTHY when exception occurs."""
    mock_http_client.get_once = AsyncMock(
        side_effect=RuntimeError("Connection refused")
    )

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_fetch_batch_uses_injected_error_handler(
    adapter, mock_http_client
) -> None:
    """Batch fetch should delegate wrapping to the adapter-level error handler."""
    mock_http_client.get = AsyncMock(side_effect=RuntimeError("boom"))
    wrapped_error = RuntimeError("wrapped")
    adapter._error_handler = MagicMock()
    adapter._error_handler.handle_error.return_value = wrapped_error

    with pytest.raises(RuntimeError, match="wrapped"):
        await adapter._fetch_batch(["12345"])

    adapter._error_handler.handle_error.assert_called_once()


@pytest.mark.asyncio
async def test_get_pmids_uses_injected_error_handler(adapter, mock_http_client) -> None:
    """Search path should delegate wrapping to the adapter-level error handler."""
    mock_http_client.get = AsyncMock(side_effect=RuntimeError("boom"))
    wrapped_error = RuntimeError("wrapped-search")
    adapter._error_handler = MagicMock()
    adapter._error_handler.handle_error.return_value = wrapped_error

    with pytest.raises(RuntimeError, match="wrapped-search"):
        await adapter._get_pmids("query", 10)

    adapter._error_handler.handle_error.assert_called_once()


# =============================================================================
# Provider Name Tests
# =============================================================================


def test_provider_name(adapter):
    """Test that provider_name is set correctly."""
    assert adapter.provider_name == "pubmed"


def test_health_endpoint(adapter):
    """Test that health endpoint is correct."""
    assert adapter._get_health_endpoint() == "/entrez/eutils/einfo.fcgi"


@pytest.mark.asyncio
async def test_fetch_applies_resume_offset_before_article_fetch(adapter) -> None:
    """Fetch should skip PMIDs from checkpoint offset before fetching articles."""
    adapter._get_pmids = AsyncMock(return_value=["1", "2", "3", "4"])  # type: ignore[method-assign]
    called_with: list[tuple[list[str], int | None]] = []

    async def _mock_yield_articles(pmids: list[str], limit: int | None):
        called_with.append((pmids, limit))
        for record in ():
            yield record

    adapter._yield_articles_from_pmids = _mock_yield_articles  # type: ignore[method-assign]

    records = [
        record
        async for record in adapter.fetch(
            entity_type="publication", limit=4, offset=2, query="test"
        )
    ]

    assert records == []
    assert called_with == [(["3", "4"], 2)]


@pytest.mark.asyncio
async def test_fetch_returns_early_when_resume_offset_reaches_limit(adapter) -> None:
    """Fetch should stop when checkpoint offset already consumed requested limit."""
    adapter._get_pmids = AsyncMock(return_value=["1", "2"])  # type: ignore[method-assign]
    called = False

    async def _mock_yield_articles(pmids: list[str], limit: int | None):
        nonlocal called
        called = True
        for record in ():
            yield record

    adapter._yield_articles_from_pmids = _mock_yield_articles  # type: ignore[method-assign]

    records = [
        record
        async for record in adapter.fetch(
            entity_type="publication", limit=2, offset=2, query="test"
        )
    ]

    assert records == []
    adapter._get_pmids.assert_not_called()
    assert called is False
