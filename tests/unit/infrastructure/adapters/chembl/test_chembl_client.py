"""Unit tests for ChemblAdapter."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bioetl.domain.exceptions import ChemblApiError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


@pytest.fixture
def adapter(mock_http_client):
    return ChemblAdapter(http_client=mock_http_client)


@pytest.mark.asyncio
async def test_fetch_activity(adapter, mock_http_client):
    """Test fetching activity records."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "activities": [{"activity_id": 1}],
        "page_meta": {"next": None}
    }
    mock_http_client.get.return_value = mock_response

    records = []
    async for record in adapter.fetch("activity"):
        records.append(record)

    assert len(records) == 1
    assert records[0]["activity_id"] == 1
    mock_http_client.get.assert_called()


@pytest.mark.asyncio
async def test_fetch_pagination(adapter, mock_http_client):
    """Test pagination."""
    # First page
    resp1 = MagicMock()
    resp1.json.return_value = {
        "activities": [{"activity_id": 1}],
        "page_meta": {"next": "page2"}
    }
    # Second page
    resp2 = MagicMock()
    resp2.json.return_value = {
        "activities": [{"activity_id": 2}],
        "page_meta": {"next": None}
    }

    mock_http_client.get.side_effect = [resp1, resp2]

    records = []
    async for record in adapter.fetch("activity"):
        records.append(record)

    assert len(records) == 2
    assert records[0]["activity_id"] == 1
    assert records[1]["activity_id"] == 2
    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_error(adapter, mock_http_client):
    """Test API error handling."""
    mock_http_client.get.side_effect = Exception("API Error")

    with pytest.raises(ChemblApiError):
        async for _ in adapter.fetch("activity"):
            pass

    assert adapter._consecutive_errors == 1


@pytest.mark.asyncio
async def test_health_check_healthy(adapter, mock_http_client):
    """Test healthy check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "UP"}
    mock_http_client.get.return_value = mock_response

    status = await adapter.health_check()
    assert status == HealthStatus.HEALTHY
    assert adapter._consecutive_errors == 0


@pytest.mark.asyncio
async def test_health_check_unhealthy(adapter, mock_http_client):
    """Test unhealthy check."""
    mock_http_client.get.side_effect = Exception("Down")

    # Degraded first
    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED

    # Still degraded
    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED

    # Unhealthy after 3 errors
    status = await adapter.health_check()
    assert status == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_get_entity_count(adapter, mock_http_client):
    """Test getting entity count."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"page_meta": {"total_count": 100}}
    mock_http_client.get.return_value = mock_response

    count = await adapter.get_entity_count("activity")
    assert count == 100


@pytest.mark.asyncio
async def test_context_manager(adapter, mock_http_client):
    """Test async context manager."""
    async with adapter as a:
        assert a is adapter
        mock_http_client.__aenter__.assert_called_once()
    mock_http_client.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_resets_errors_on_degraded_response(adapter, mock_http_client):
    """Test that error counter resets on successful HTTP response even if status is DEGRADED.

    Regression test: Previously _consecutive_errors was only reset when status="UP",
    leaving stale error counts after a successful HTTP 200 response with non-UP status.
    """
    # First: simulate a failed health check to increment error counter
    mock_http_client.get.side_effect = Exception("Network error")
    await adapter.health_check()
    assert adapter._consecutive_errors == 1

    # Second: successful HTTP response with DEGRADED status should reset counter
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "DEGRADED"}
    mock_http_client.get.side_effect = None
    mock_http_client.get.return_value = mock_response

    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED
    assert adapter._consecutive_errors == 0  # Counter should be reset
