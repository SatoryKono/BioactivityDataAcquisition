"""Unit tests for ChemblAdapter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.exceptions import ChemblApiError, CriticalError, RateLimitError
from bioetl.domain.types import ErrorType, HealthStatus
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    return ChemblAdapter(http_client=mock_http_client, logger=mock_logger)


@pytest.mark.asyncio
async def test_fetch_activity(adapter, mock_http_client):
    """Test fetching activity records."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "activities": [{"activity_id": 1}],
        "page_meta": {"next": None},
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
        "page_meta": {"next": "page2"},
    }
    # Second page
    resp2 = MagicMock()
    resp2.json.return_value = {
        "activities": [{"activity_id": 2}],
        "page_meta": {"next": None},
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
async def test_health_check_resets_errors_on_degraded_response(
    adapter, mock_http_client
):
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


@pytest.mark.unit
class TestChemblAdapterErrorClassification:
    """Tests for error classification and handling."""

    @pytest.mark.asyncio
    async def test_error_classification_logged(self, adapter, mock_http_client, mock_logger):
        """Test that error type is classified and logged."""
        mock_http_client.get.side_effect = RateLimitError("chembl", 60.0)

        with pytest.raises(ChemblApiError):
            async for _ in adapter.fetch("activity"):
                pass

        # Verify error was logged with classification
        mock_logger.error.assert_called()
        call_kwargs = mock_logger.error.call_args.kwargs
        assert call_kwargs["error_type"] == ErrorType.RATE_LIMIT.value
        assert call_kwargs["is_recoverable"] is True

    @pytest.mark.asyncio
    async def test_error_counts_tracked(self, adapter, mock_http_client):
        """Test that error counts are tracked by type."""
        # Simulate multiple errors
        mock_http_client.get.side_effect = RateLimitError("chembl", 60.0)

        for _ in range(3):
            with pytest.raises(ChemblApiError):
                async for _ in adapter.fetch("activity"):
                    pass

        stats = adapter.get_error_stats()
        assert stats["total_errors"] == 3
        assert stats["consecutive_errors"] == 3
        assert ErrorType.RATE_LIMIT.value in stats["error_counts_by_type"]

    @pytest.mark.asyncio
    async def test_reset_error_counters(self, adapter, mock_http_client):
        """Test error counter reset."""
        mock_http_client.get.side_effect = Exception("Error")

        with pytest.raises(ChemblApiError):
            async for _ in adapter.fetch("activity"):
                pass

        assert adapter._total_errors == 1

        adapter.reset_error_counters()

        assert adapter._total_errors == 0
        assert adapter._consecutive_errors == 0
        assert adapter._cached_health == HealthStatus.HEALTHY


@pytest.mark.unit
class TestChemblAdapterHealthAwareBatchSize:
    """Tests for health-aware batch size adjustment."""

    @pytest.mark.asyncio
    async def test_healthy_uses_full_batch_size(self, mock_http_client, mock_logger):
        """Test that HEALTHY status uses full batch size."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            batch_size=1000,
        )

        effective = adapter._get_effective_batch_size()
        assert effective == 1000

    @pytest.mark.asyncio
    async def test_degraded_halves_batch_size(self, mock_http_client, mock_logger):
        """Test that DEGRADED status halves batch size."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            batch_size=1000,
        )
        adapter._cached_health = HealthStatus.DEGRADED
        adapter._consecutive_errors = 1

        effective = adapter._get_effective_batch_size()
        assert effective == 500

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args.kwargs
        assert call_kwargs["original_batch_size"] == 1000
        assert call_kwargs["effective_batch_size"] == 500

    @pytest.mark.asyncio
    async def test_degraded_respects_minimum_batch_size(
        self, mock_http_client, mock_logger
    ):
        """Test that DEGRADED status respects minimum batch size of 100."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            batch_size=150,  # Half would be 75, below minimum
        )
        adapter._cached_health = HealthStatus.DEGRADED
        adapter._consecutive_errors = 1

        effective = adapter._get_effective_batch_size()
        assert effective == 100  # Minimum enforced

    @pytest.mark.asyncio
    async def test_unhealthy_raises_critical_error(self, mock_http_client, mock_logger):
        """Test that UNHEALTHY status raises CriticalError."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            batch_size=1000,
        )
        adapter._cached_health = HealthStatus.UNHEALTHY
        adapter._consecutive_errors = 3
        adapter._total_errors = 5

        with pytest.raises(CriticalError) as exc_info:
            adapter._get_effective_batch_size()

        assert "UNHEALTHY" in str(exc_info.value)
        assert "3" in str(exc_info.value)  # consecutive errors
        assert "5" in str(exc_info.value)  # total errors

    @pytest.mark.asyncio
    async def test_build_params_uses_effective_batch_size(
        self, mock_http_client, mock_logger
    ):
        """Test that _build_params uses health-aware batch size."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            batch_size=1000,
        )

        # Healthy
        params = adapter._build_params(offset=0)
        assert params["limit"] == 1000

        # Degraded
        adapter._cached_health = HealthStatus.DEGRADED
        adapter._consecutive_errors = 1
        params = adapter._build_params(offset=0)
        assert params["limit"] == 500


@pytest.mark.unit
class TestChemblAdapterHealthTransitions:
    """Tests for health status transitions and logging."""

    @pytest.mark.asyncio
    async def test_health_transition_logged(self, adapter, mock_http_client, mock_logger):
        """Test that health transitions are logged."""
        # First error: HEALTHY -> DEGRADED
        mock_http_client.get.side_effect = Exception("Error")

        with pytest.raises(ChemblApiError):
            async for _ in adapter.fetch("activity"):
                pass

        # Find the health transition log
        info_calls = [
            call for call in mock_logger.info.call_args_list
            if call.args and call.args[0] == "chembl_health_transition"
        ]
        assert len(info_calls) == 1
        kwargs = info_calls[0].kwargs
        assert kwargs["previous_status"] == "HEALTHY"
        assert kwargs["current_status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_consecutive_errors_reset_on_success(
        self, adapter, mock_http_client
    ):
        """Test that consecutive errors reset after successful fetch."""
        # First: simulate error
        mock_http_client.get.side_effect = Exception("Error")
        with pytest.raises(ChemblApiError):
            async for _ in adapter.fetch("activity"):
                pass

        assert adapter._consecutive_errors == 1

        # Second: successful fetch resets counter
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "activities": [{"activity_id": 1}],
            "page_meta": {"next": None},
        }
        mock_http_client.get.side_effect = None
        mock_http_client.get.return_value = mock_response

        async for _ in adapter.fetch("activity"):
            pass

        assert adapter._consecutive_errors == 0
