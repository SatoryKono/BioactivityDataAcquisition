"""Unit tests for ChemblAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.exceptions import CriticalError, ExternalServiceError, RateLimitError
from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import CircuitBreakerState, ErrorType, HealthStatus
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    # Circuit breaker must be MagicMock (not AsyncMock) because its methods are sync
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    client.circuit_breaker.get_failure_count.return_value = 0
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
async def test_fetch_deduplicates_across_pages(adapter, mock_http_client):
    """Test that duplicate records across pages are deduplicated.

    ChEMBL API can return duplicate records across pages due to unstable
    pagination. The adapter should deduplicate by primary key field.
    """
    # First page: activity_id 1 and 2
    resp1 = MagicMock()
    resp1.json.return_value = {
        "activities": [{"activity_id": 1}, {"activity_id": 2}],
        "page_meta": {"next": "page2"},
    }
    # Second page: activity_id 2 (duplicate!) and 3
    resp2 = MagicMock()
    resp2.json.return_value = {
        "activities": [{"activity_id": 2}, {"activity_id": 3}],
        "page_meta": {"next": None},
    }

    mock_http_client.get.side_effect = [resp1, resp2]

    records = []
    async for record in adapter.fetch("activity"):
        records.append(record)

    # Should have 3 unique records, not 4
    assert len(records) == 3
    activity_ids = [r["activity_id"] for r in records]
    assert activity_ids == [1, 2, 3]


@pytest.mark.asyncio
async def test_fetch_deduplicates_assay_by_chembl_id(adapter, mock_http_client):
    """Test deduplication for assay entity type using assay_chembl_id."""
    # First page
    resp1 = MagicMock()
    resp1.json.return_value = {
        "assays": [
            {"assay_chembl_id": "CHEMBL1234567"},
            {"assay_chembl_id": "CHEMBL1234568"},
        ],
        "page_meta": {"next": "page2"},
    }
    # Second page with duplicate
    resp2 = MagicMock()
    resp2.json.return_value = {
        "assays": [
            {"assay_chembl_id": "CHEMBL1234567"},  # Duplicate!
            {"assay_chembl_id": "CHEMBL1234569"},
        ],
        "page_meta": {"next": None},
    }

    mock_http_client.get.side_effect = [resp1, resp2]

    records = []
    async for record in adapter.fetch("assay"):
        records.append(record)

    # Should have 3 unique assays
    assert len(records) == 3
    chembl_ids = [r["assay_chembl_id"] for r in records]
    assert "CHEMBL1234567" in chembl_ids
    assert "CHEMBL1234568" in chembl_ids
    assert "CHEMBL1234569" in chembl_ids


@pytest.mark.asyncio
async def test_fetch_with_filter_deduplicates_across_pages(adapter, mock_http_client):
    """Test deduplication for filtered fetch across multiple pages."""
    # First page with 2 assays
    resp1 = MagicMock()
    resp1.json.return_value = {
        "assays": [
            {"assay_chembl_id": "CHEMBL1000"},
            {"assay_chembl_id": "CHEMBL1001"},
        ],
        "page_meta": {"next": "page2"},
    }
    # Second page with one duplicate and one new
    resp2 = MagicMock()
    resp2.json.return_value = {
        "assays": [
            {"assay_chembl_id": "CHEMBL1000"},  # Duplicate from page 1
            {"assay_chembl_id": "CHEMBL1002"},
        ],
        "page_meta": {"next": None},
    }

    mock_http_client.get.side_effect = [resp1, resp2]

    records = []
    async for record in adapter.fetch_filtered(
        entity_type="assay",
        filter_ids=["CHEMBL1000", "CHEMBL1001", "CHEMBL1002"],
        filter_field="assay_chembl_id",
    ):
        records.append(record)

    # Should have 3 unique assays (duplicate CHEMBL1000 filtered out)
    assert len(records) == 3
    chembl_ids = [r["assay_chembl_id"] for r in records]
    assert chembl_ids.count("CHEMBL1000") == 1
    assert "CHEMBL1001" in chembl_ids
    assert "CHEMBL1002" in chembl_ids


@pytest.mark.asyncio
async def test_fetch_error(adapter, mock_http_client):
    """Test API error handling."""
    mock_http_client.get.side_effect = Exception("API Error")

    with pytest.raises(ExternalServiceError):
        async for _ in adapter.fetch("activity"):
            pass

    # Error tracking is now handled by circuit breaker, no adapter state to check


@pytest.mark.asyncio
async def test_health_check_healthy(adapter, mock_http_client):
    """Test healthy check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "UP"}
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    status = await adapter.health_check()
    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_check_unhealthy(adapter, mock_http_client):
    """Test unhealthy check with circuit breaker in UNHEALTHY state.

    Health status is now derived from circuit breaker state, not consecutive errors.
    """
    mock_http_client.get_once = AsyncMock(side_effect=Exception("Down"))
    # Configure circuit breaker to report UNHEALTHY state (failure_count > 2)
    mock_http_client.circuit_breaker.get_failure_count.return_value = 3

    status = await adapter.health_check()
    # Falls back to circuit breaker state when exception occurs
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
async def test_health_check_degraded_response(adapter, mock_http_client):
    """Test that DEGRADED status is returned when API reports non-UP status.

    Note: Error tracking is now handled by circuit breaker, not adapter.
    This test verifies the _handle_health_response logic.
    """
    # Successful HTTP response with DEGRADED status
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "DEGRADED"}
    mock_http_client.get.return_value = mock_response

    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED


@pytest.mark.unit
class TestChemblAdapterErrorClassification:
    """Tests for error classification and handling."""

    @pytest.mark.asyncio
    async def test_error_classification_logged(
        self, adapter, mock_http_client, mock_logger
    ):
        """Test that error type is classified and logged."""
        mock_http_client.get.side_effect = RateLimitError("chembl", 60.0)

        with pytest.raises(ExternalServiceError):
            async for _ in adapter.fetch("activity"):
                pass

        # Verify error was logged with classification
        mock_logger.error.assert_called()
        call_kwargs = mock_logger.error.call_args.kwargs
        assert call_kwargs["error_type"] == ErrorType.RATE_LIMIT.value
        assert call_kwargs["is_recoverable"] is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_count_accessed(
        self, adapter, mock_http_client
    ):
        """Test that circuit breaker failure count is accessed during errors.

        Error tracking is now delegated to circuit breaker.
        """
        mock_http_client.get.side_effect = RateLimitError("chembl", 60.0)

        with pytest.raises(ExternalServiceError):
            async for _ in adapter.fetch("activity"):
                pass

        # Verify circuit breaker was consulted for health status
        mock_http_client.circuit_breaker.get_failure_count.assert_called()


@pytest.mark.unit
class TestChemblAdapterHealthAwareBatchSize:
    """Tests for health-aware batch size adjustment."""

    @pytest.mark.asyncio
    async def test_healthy_uses_full_batch_size(self, mock_http_client, mock_logger):
        """Test that HEALTHY status uses full batch size."""
        # Configure circuit breaker for HEALTHY state
        mock_http_client.circuit_breaker = MagicMock()
        mock_http_client.circuit_breaker.get_state.return_value = (
            CircuitBreakerState.CLOSED
        )
        mock_http_client.circuit_breaker.get_failure_count.return_value = 0

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=1000),
        )

        effective = adapter._get_effective_batch_size()
        assert effective == 1000

    @pytest.mark.asyncio
    async def test_degraded_halves_batch_size(self, mock_http_client, mock_logger):
        """Test that DEGRADED status halves batch size."""
        # Configure circuit breaker for DEGRADED state (1-2 failures)
        mock_http_client.circuit_breaker = MagicMock()
        mock_http_client.circuit_breaker.get_state.return_value = (
            CircuitBreakerState.CLOSED
        )
        mock_http_client.circuit_breaker.get_failure_count.return_value = 1

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=1000),
        )

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
        # Configure circuit breaker for DEGRADED state
        mock_http_client.circuit_breaker = MagicMock()
        mock_http_client.circuit_breaker.get_state.return_value = (
            CircuitBreakerState.CLOSED
        )
        mock_http_client.circuit_breaker.get_failure_count.return_value = 1

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(
                page_size=150
            ),  # Half would be 75, below minimum
        )

        effective = adapter._get_effective_batch_size()
        assert effective == 100  # Minimum enforced

    @pytest.mark.asyncio
    async def test_unhealthy_raises_critical_error(self, mock_http_client, mock_logger):
        """Test that UNHEALTHY status raises CriticalError."""
        # Configure circuit breaker for UNHEALTHY state (failure_count > 2)
        mock_http_client.circuit_breaker = MagicMock()
        mock_http_client.circuit_breaker.get_state.return_value = (
            CircuitBreakerState.CLOSED
        )
        mock_http_client.circuit_breaker.get_failure_count.return_value = 3

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=1000),
        )

        with pytest.raises(CriticalError) as exc_info:
            adapter._get_effective_batch_size()

        assert "UNHEALTHY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_build_params_uses_effective_batch_size(
        self, mock_http_client, mock_logger
    ):
        """Test that _build_params uses health-aware batch size."""
        # Configure circuit breaker for HEALTHY state
        mock_http_client.circuit_breaker = MagicMock()
        mock_http_client.circuit_breaker.get_state.return_value = (
            CircuitBreakerState.CLOSED
        )
        mock_http_client.circuit_breaker.get_failure_count.return_value = 0

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=1000),
        )

        # Healthy
        params = adapter._build_params(offset=0)
        assert params["limit"] == 1000

        # Degraded - change circuit breaker state
        mock_http_client.circuit_breaker.get_failure_count.return_value = 1
        params = adapter._build_params(offset=0)
        assert params["limit"] == 500


@pytest.mark.unit
class TestChemblAdapterHealthTransitions:
    """Tests for health status via circuit breaker."""

    @pytest.mark.asyncio
    async def test_degraded_mode_logs_warning(self, mock_http_client, mock_logger):
        """Test that degraded mode logs a warning.

        Health transitions are now handled by circuit breaker.
        This test verifies that the adapter logs degraded mode info.
        """
        # Configure circuit breaker for DEGRADED state
        mock_http_client.circuit_breaker = MagicMock()
        mock_http_client.circuit_breaker.get_state.return_value = (
            CircuitBreakerState.CLOSED
        )
        mock_http_client.circuit_breaker.get_failure_count.return_value = 1

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=1000),
        )

        # Trigger effective batch size calculation
        adapter._get_effective_batch_size()

        # Verify warning was logged about degraded mode
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args.args[0] == "chembl_degraded_mode"

    @pytest.mark.asyncio
    async def test_successful_fetch_uses_circuit_breaker_state(
        self, adapter, mock_http_client
    ):
        """Test that fetch uses circuit breaker state for health.

        Error tracking is now delegated to circuit breaker.
        """
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
        # Verify circuit breaker state was consulted
        mock_http_client.circuit_breaker.get_state.assert_called()


@pytest.mark.unit
class TestChemblAdapterRequestCollector:
    """Tests for APIRequestCollector integration."""

    @pytest.mark.asyncio
    async def test_request_count_starts_at_zero(self, mock_http_client, mock_logger):
        """Test that request_count starts at zero."""
        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
        assert adapter.request_count == 0

    @pytest.mark.asyncio
    async def test_get_source_metadata_returns_source_metadata(
        self, mock_http_client, mock_logger
    ):
        """Test that get_source_metadata returns a SourceMetadata object."""
        from bioetl.domain.models.metadata import SourceMetadata

        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
        metadata = adapter.get_source_metadata()

        assert isinstance(metadata, SourceMetadata)
        assert metadata.type == "api"
        assert "ebi.ac.uk" in (metadata.url or "")

    @pytest.mark.asyncio
    async def test_get_source_metadata_clears_collector(
        self, mock_http_client, mock_logger
    ):
        """Test that get_source_metadata clears the collector."""
        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)

        # Manually record a request to simulate activity
        adapter._request_collector.record_request(
            url="https://example.com/test",
            method="GET",
            duration_ms=100,
        )
        assert adapter.request_count == 1

        # Get metadata (should clear)
        adapter.get_source_metadata()
        assert adapter.request_count == 0

    @pytest.mark.asyncio
    async def test_clear_request_collector(self, mock_http_client, mock_logger):
        """Test that clear_request_collector clears without returning metadata."""
        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)

        # Manually record a request
        adapter._request_collector.record_request(
            url="https://example.com/test",
            method="GET",
            duration_ms=100,
        )
        assert adapter.request_count == 1

        # Clear
        adapter.clear_request_collector()
        assert adapter.request_count == 0

    @pytest.mark.asyncio
    async def test_source_metadata_includes_api_version(
        self, mock_http_client, mock_logger
    ):
        """Test that api_version is included in source metadata."""
        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
        metadata = adapter.get_source_metadata(api_version="1.0")

        assert metadata.api_version == "1.0"


@pytest.mark.unit
class TestChemblAdapterFallbackMode:
    """Tests for fallback mode when batch filter fails."""

    @pytest.mark.asyncio
    async def test_fetch_single_record_success(self, mock_http_client, mock_logger):
        """Test fetching a single record by ID."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "document_chembl_id": "CHEMBL1121421",
            "title": "Test Document",
        }
        mock_http_client.get.return_value = mock_response

        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
        record = await adapter._fetch_single_record("document", "CHEMBL1121421")

        assert record is not None
        assert record["document_chembl_id"] == "CHEMBL1121421"
        mock_http_client.get.assert_called_once()
        # Verify URL includes record ID
        call_args = mock_http_client.get.call_args
        assert "CHEMBL1121421" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_fetch_single_record_failure_returns_none(
        self, mock_http_client, mock_logger
    ):
        """Test that fetch_single_record returns None on failure."""
        mock_http_client.get.side_effect = Exception("API Error")

        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
        record = await adapter._fetch_single_record("document", "CHEMBL1121421")

        assert record is None
        mock_logger.warning.assert_called()
        call_kwargs = mock_logger.warning.call_args.kwargs
        assert call_kwargs.get("record_id") == "CHEMBL1121421"

    @pytest.mark.asyncio
    async def test_fetch_with_filter_fallback_yields_records(
        self, mock_http_client, mock_logger
    ):
        """Test that fallback mode yields records one by one."""
        # Setup mock for individual record fetches
        def mock_get(url, params=None):
            response = MagicMock()
            if "CHEMBL1121421" in url:
                response.json.return_value = {
                    "document_chembl_id": "CHEMBL1121421",
                    "title": "Doc 1",
                }
            elif "CHEMBL1121493" in url:
                response.json.return_value = {
                    "document_chembl_id": "CHEMBL1121493",
                    "title": "Doc 2",
                }
            else:
                raise Exception("Not found")
            return response

        mock_http_client.get = AsyncMock(side_effect=mock_get)

        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
        records = []
        async for record in adapter._fetch_with_filter_fallback(
            "document",
            ["CHEMBL1121421", "CHEMBL1121493"],
            "document_chembl_id",
        ):
            records.append(record)

        assert len(records) == 2
        assert records[0]["document_chembl_id"] == "CHEMBL1121421"
        assert records[1]["document_chembl_id"] == "CHEMBL1121493"
        # Verify fallback mode was logged
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_with_filter_falls_back_on_500(
        self, mock_http_client, mock_logger
    ):
        """Test that _fetch_with_filter falls back to individual fetches on 500."""
        import httpx

        # First call (batch filter) raises 500 error
        http_error = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        # Track call count to return different results
        call_count = 0

        async def mock_get(url, params=None):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call is batch filter - raise 500
                raise http_error

            # Subsequent calls are individual fetches
            response = MagicMock()
            if "CHEMBL1121421" in url:
                response.json.return_value = {
                    "document_chembl_id": "CHEMBL1121421",
                    "title": "Doc 1",
                }
            elif "CHEMBL1121493" in url:
                response.json.return_value = {
                    "document_chembl_id": "CHEMBL1121493",
                    "title": "Doc 2",
                }
            return response

        mock_http_client.get = mock_get

        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)

        records = []
        async for record in adapter._fetch_with_filter(
            "document",
            ["CHEMBL1121421", "CHEMBL1121493"],
            "document_chembl_id",
        ):
            records.append(record)

        assert len(records) == 2
        # Verify fallback warning was logged
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args
        assert warning_call.args[0] == "chembl_batch_filter_failed"

    @pytest.mark.asyncio
    async def test_fetch_with_filter_reraises_non_500_errors(
        self, mock_http_client, mock_logger
    ):
        """Test that non-500 errors are re-raised, not triggering fallback."""
        mock_http_client.get.side_effect = Exception("Connection Error")

        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)

        with pytest.raises(ExternalServiceError):
            async for _ in adapter._fetch_with_filter(
                "document",
                ["CHEMBL1121421"],
                "document_chembl_id",
            ):
                pass
