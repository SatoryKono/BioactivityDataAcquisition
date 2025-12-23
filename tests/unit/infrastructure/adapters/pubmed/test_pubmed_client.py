# tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py
"""Unit tests for PubMedAdapter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

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
    # Save reference to inner client before aclose sets it to None
    inner_client = mock_http_client._client

    await adapter.aclose()

    inner_client.aclose.assert_called_once()
    assert mock_http_client._client is None


@pytest.mark.asyncio
async def test_aclose_idempotent(adapter, mock_http_client):
    """Test that aclose() can be called multiple times safely."""
    # Save reference to inner client before aclose sets it to None
    inner_client = mock_http_client._client

    # First call should close
    await adapter.aclose()
    inner_client.aclose.assert_called_once()

    # Second call should not raise (client is None now)
    await adapter.aclose()

    # aclose was only called once (on first invocation)
    inner_client.aclose.assert_called_once()


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
