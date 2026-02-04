"""Additional coverage tests for UniProtAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import CircuitBreakerState, HealthStatus
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    client.circuit_breaker.get_failure_count.return_value = 0
    return client


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    return UniProtAdapter(http_client=mock_http_client, logger=mock_logger)


@pytest.mark.asyncio
async def test_probe_health_healthy(adapter, mock_http_client):
    """Test health probe returns HEALTHY."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"primaryAccession": "P0CG48"}]}
    mock_http_client.get_once.return_value = mock_response

    status = await adapter._probe_health()
    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_probe_health_degraded(adapter, mock_http_client):
    """Test health probe returns HEALTHY on empty search (status 200)."""

    mock_response = MagicMock()

    mock_response.status_code = 200

    mock_response.json.return_value = {"results": []}

    mock_http_client.get_once.return_value = mock_response

    status = await adapter._probe_health()

    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_probe_health_error(adapter, mock_http_client):
    """Test health probe raises exception on failure."""

    mock_http_client.get_once.side_effect = Exception("API Error")

    with pytest.raises(Exception):
        await adapter._probe_health()


@pytest.mark.asyncio
async def test_get_source_metadata(adapter):
    """Test retrieving source metadata."""

    adapter._request_collector.record_request("http://test", "GET", 100, 200)

    metadata = adapter.get_source_metadata(api_version="v1")

    assert metadata.type == "api"

    assert metadata.url == "https://rest.uniprot.org"

    assert metadata.api_version == "v1"

    assert adapter.request_count == 0


@pytest.mark.asyncio
async def test_clear_request_collector(adapter):
    """Test clearing request collector."""

    adapter._request_collector.record_request("http://test", "GET", 100, 200)

    assert adapter.request_count == 1

    adapter.clear_request_collector()

    assert adapter.request_count == 0


@pytest.mark.asyncio
async def test_fetch_with_filter_batching(adapter, mock_http_client):
    """Test fetch_filtered handles batching."""

    # Mock http_client.get to return fake records

    mock_response = MagicMock()

    mock_response.status_code = 200

    mock_response.json.return_value = {"results": [{"primaryAccession": "P1"}]}

    mock_http_client.get.return_value = mock_response

    ids = ["P1"] * 120  # 120 IDs, batch size 100 -> 2 batches

    records = []

    async for record in adapter.fetch_filtered("protein", ids, "accession"):
        records.append(record)

    # Should be called 2 times (once per batch)

    assert mock_http_client.get.call_count == 2
