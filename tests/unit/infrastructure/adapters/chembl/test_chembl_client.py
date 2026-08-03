# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for ChemblAdapter."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bioetl.domain.exceptions import (
    CriticalError,
    ExternalServiceError,
    RateLimitError,
    RetryExhaustedError,
)
from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import CircuitBreakerState, ErrorType, HealthStatus
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    FallbackFetchOrchestrator,
)


pytestmark = pytest.mark.unit


async def _drain_async_iter(async_iter) -> None:
    """Consume an async iterator until completion."""
    async for _ in async_iter:
        continue


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


def test_post_init_preserves_injected_base_collaborators(
    mock_http_client, mock_logger
) -> None:
    """Dataclass adapter should delegate shared base initialization."""
    error_handler = MagicMock()
    metrics = MagicMock()
    adapter_metrics = AdapterMetricsRecorder(metrics, "chembl")
    request_collector = APIRequestCollector()

    adapter = ChemblAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        metrics=metrics,
        error_handler=error_handler,
        adapter_metrics=adapter_metrics,
        request_collector=request_collector,
    )

    assert adapter._http_client is mock_http_client
    assert adapter._logger is mock_logger
    assert adapter._metrics is metrics
    assert adapter._error_handler is error_handler
    assert adapter._adapter_metrics is adapter_metrics
    assert adapter._request_collector is request_collector


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
    """Test deduplication for assay entity type using assay_chembl_id (API field name)."""
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
        filter_field="assay_id",
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
    mock_http_client.get.side_effect = RuntimeError("API Error")

    with pytest.raises(ExternalServiceError):
        await _drain_async_iter(adapter.fetch("activity"))

    # Error tracking is now handled by circuit breaker, no adapter state to check


@pytest.mark.asyncio
async def test_chembl_chembl_client__health_check_healthy__c61c1001(
    adapter, mock_http_client
):
    """Test healthy check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "UP"}
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    status = await adapter.health_check()
    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_check_unhealthy(adapter, mock_http_client):
    """Test unhealthy check with circuit breaker in OPEN state.

    Health status is derived from circuit breaker state: OPEN = UNHEALTHY.
    """
    mock_http_client.get_once = AsyncMock(side_effect=RuntimeError("Down"))
    # Configure circuit breaker OPEN state (threshold reached)
    mock_http_client.circuit_breaker.get_state.return_value = CircuitBreakerState.OPEN
    mock_http_client.circuit_breaker.get_failure_count.return_value = 5

    status = await adapter.health_check()
    # Falls back to circuit breaker state when exception occurs
    assert status == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_chembl_chembl_client__get_entity_count__6d319d8b(
    adapter, mock_http_client
):
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
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_health_check_status_endpoint_500_returns_degraded(
    adapter, mock_http_client
):
    """Treat ChEMBL status endpoint 5xx as DEGRADED to avoid hard preflight block."""

    class StatusProbeError(RuntimeError):
        """Synthetic status probe failure used by the test."""

    error = StatusProbeError("status endpoint failed")
    error.response = MagicMock(status_code=500)
    mock_http_client.get_once = AsyncMock(side_effect=error)

    status = await adapter.health_check()
    assert status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_health_check_probe_timeout_returns_degraded(
    adapter,
    mock_http_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stuck ChEMBL status probe should fail fast as DEGRADED."""

    async def _hang(_url: str) -> None:
        await asyncio.sleep(1)

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.chembl.health.CHEMBL_HEALTH_PROBE_TIMEOUT_SECONDS",
        0.01,
    )
    mock_http_client.get_once = AsyncMock(side_effect=_hang)

    status = await adapter.health_check()

    assert status == HealthStatus.DEGRADED
    assert adapter._last_probe_health_status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_check_health_status_endpoint_500_returns_degraded(
    adapter, mock_http_client
):
    """check_health() should return DEGRADED (not UNHEALTHY) on status endpoint 5xx."""

    class StatusProbeError(RuntimeError):
        """Synthetic status probe failure used by the test."""

    error = StatusProbeError("status endpoint failed")
    error.response = MagicMock(status_code=500)
    mock_http_client.get_once = AsyncMock(side_effect=error)

    result = await adapter.check_health()
    assert result.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_degraded_probe_reduces_first_fetch_batch_size(
    mock_http_client, mock_logger
) -> None:
    """A degraded preflight probe should shrink the next page limit immediately."""
    adapter = ChemblAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        adapter_config=AdapterConfig(page_size=1000),
    )
    request = httpx.Request("GET", "https://www.ebi.ac.uk/chembl/api/data/status")
    response = httpx.Response(status_code=500, request=request)
    mock_http_client.get_once = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "status endpoint failed",
            request=request,
            response=response,
        )
    )

    result = await adapter.check_health()

    assert result.status == HealthStatus.DEGRADED
    assert adapter._build_params(0, "activity")["limit"] == 500


def test_effective_batch_size_prefers_probe_degradation_over_clean_circuit(
    adapter, mock_http_client
) -> None:
    """Probe degradation should matter before any request failures hit the circuit breaker."""
    mock_http_client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    mock_http_client.circuit_breaker.get_failure_count.return_value = 0
    adapter._last_probe_health_status = HealthStatus.DEGRADED

    assert adapter._get_effective_batch_size() == 500


@pytest.mark.asyncio
async def test_successful_fetch_clears_stale_probe_degraded_state(
    adapter, mock_http_client
) -> None:
    """A successful data page should clear probe-only degraded state."""
    adapter._last_probe_health_status = HealthStatus.DEGRADED
    mock_http_client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    mock_http_client.circuit_breaker.get_failure_count.return_value = 0

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "assays": [{"assay_chembl_id": "CHEMBL1"}],
        "page_meta": {"next": None},
    }
    mock_http_client.get.return_value = mock_response

    records, has_next = await adapter._fetch_page(
        "https://www.ebi.ac.uk/chembl/api/data/assay",
        {"format": "json", "limit": 500, "offset": 0},
        "assay",
    )

    assert records == [{"assay_chembl_id": "CHEMBL1"}]
    assert has_next is False
    assert adapter._last_probe_health_status is None
    assert adapter._get_effective_batch_size() == 1000


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
            await _drain_async_iter(adapter.fetch("activity"))

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
            await _drain_async_iter(adapter.fetch("activity"))

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
        # Configure circuit breaker for UNHEALTHY state (OPEN = threshold reached)
        mock_http_client.circuit_breaker = MagicMock()
        mock_http_client.circuit_breaker.get_state.return_value = (
            CircuitBreakerState.OPEN
        )
        mock_http_client.circuit_breaker.get_failure_count.return_value = 5

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


@pytest.mark.unit
class TestChemblAdapterBatchReduction:
    """Tests for batch size reduction on RetryExhaustedError."""

    @pytest.mark.asyncio
    async def test_batch_splits_on_retry_exhausted_error(
        self, mock_http_client, mock_logger
    ):
        """Test that batch is split in half when RetryExhaustedError occurs."""
        from bioetl.domain.exceptions import RetryExhaustedError

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(batch_size=4),
        )

        call_count = 0

        async def mock_get(url, params=None):
            await asyncio.sleep(0)
            nonlocal call_count
            call_count += 1
            ids_param = params.get("document_chembl_id__in") or params.get(
                "publication_id__in", ""
            )
            ids = ids_param.split(",") if ids_param else []

            # Fail on 4-ID batch, succeed on smaller batches
            if len(ids) == 4:
                raise RetryExhaustedError(
                    url, attempts=3, last_error=Exception("500 Internal Server Error")
                )

            # Return records for smaller batches
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "documents": [{"document_chembl_id": id_} for id_ in ids],
                "page_meta": {"next": None},
            }
            return mock_response

        mock_http_client.get = mock_get

        records = []
        async for record in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["CHEMBL1", "CHEMBL2", "CHEMBL3", "CHEMBL4"],
            filter_field="publication_id",
        ):
            records.append(record)

        # Should get all 4 records despite initial failure
        assert len(records) == 4
        chembl_ids = {r["document_chembl_id"] for r in records}
        assert chembl_ids == {"CHEMBL1", "CHEMBL2", "CHEMBL3", "CHEMBL4"}

        # Verify warning was logged about batch reduction
        mock_logger.warning.assert_called()
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args[0] == "batch_reduction_retry"
        ]
        assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_single_id_failure_logs_error_and_skips(
        self, mock_http_client, mock_logger
    ):
        """Test that single-ID failure is logged and skipped gracefully."""
        from bioetl.domain.exceptions import RetryExhaustedError

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(batch_size=2),
        )

        async def mock_get(url, params=None):
            await asyncio.sleep(0)
            ids_param = params.get("document_chembl_id__in") or params.get(
                "publication_id__in", ""
            )
            ids = ids_param.split(",") if ids_param else []

            # Always fail for CHEMBL_BAD
            if "CHEMBL_BAD" in ids:
                raise RetryExhaustedError(
                    url, attempts=3, last_error=Exception("500 Internal Server Error")
                )

            # Return records for good IDs
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "documents": [{"document_chembl_id": id_} for id_ in ids],
                "page_meta": {"next": None},
            }
            return mock_response

        mock_http_client.get = mock_get

        records = []
        async for record in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["CHEMBL_GOOD", "CHEMBL_BAD"],
            filter_field="publication_id",
        ):
            records.append(record)

        # Should get only the good record
        assert len(records) == 1
        assert records[0]["document_chembl_id"] == "CHEMBL_GOOD"

        # Verify error was logged for the failed single ID
        mock_logger.error.assert_called()
        error_calls = [
            c
            for c in mock_logger.error.call_args_list
            if c.args[0] == "single_id_fetch_failed"
        ]
        assert len(error_calls) == 1
        assert error_calls[0].kwargs["failed_id"] == "CHEMBL_BAD"

    @pytest.mark.asyncio
    async def test_successful_batch_no_reduction(self, mock_http_client, mock_logger):
        """Test that successful batches don't trigger reduction."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(batch_size=4),
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "documents": [
                {"document_chembl_id": "CHEMBL1"},
                {"document_chembl_id": "CHEMBL2"},
            ],
            "page_meta": {"next": None},
        }
        mock_http_client.get.return_value = mock_response

        records = []
        async for record in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["CHEMBL1", "CHEMBL2"],
            filter_field="publication_id",
        ):
            records.append(record)

        assert len(records) == 2

        # Verify no batch reduction warning was logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "batch_reduction_retry"
        ]
        assert len(warning_calls) == 0

    @pytest.mark.asyncio
    async def test_recursive_batch_reduction(self, mock_http_client, mock_logger):
        """Test recursive batch reduction when multiple levels fail."""
        from bioetl.domain.exceptions import RetryExhaustedError

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(batch_size=4),
        )

        async def mock_get(url, params=None):
            await asyncio.sleep(0)
            ids_param = params.get("document_chembl_id__in") or params.get(
                "publication_id__in", ""
            )
            ids = ids_param.split(",") if ids_param else []

            # Fail on batches of size 2 or more
            if len(ids) >= 2:
                raise RetryExhaustedError(
                    url, attempts=3, last_error=Exception("500 Internal Server Error")
                )

            # Succeed only on single-ID requests
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "documents": [{"document_chembl_id": id_} for id_ in ids],
                "page_meta": {"next": None},
            }
            return mock_response

        mock_http_client.get = mock_get

        records = []
        async for record in adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["CHEMBL1", "CHEMBL2", "CHEMBL3", "CHEMBL4"],
            filter_field="publication_id",
        ):
            records.append(record)

        # Should get all 4 records through recursive single-ID fetches
        assert len(records) == 4

        # Verify multiple batch_reduction_retry warnings were logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "batch_reduction_retry"
        ]
        # Should have warnings for: 4->2+2, then 2->1+1 twice
        assert len(warning_calls) >= 3


@pytest.mark.unit
class TestChemblAdapterDirectEndpointFallback:
    """Tests for direct endpoint fallback when filter endpoint fails."""

    @pytest.mark.asyncio
    async def test_direct_endpoint_fallback_on_filter_500(
        self, mock_http_client, mock_logger
    ):
        """Test fallback to direct endpoint when filter endpoint returns 500.

        ChEMBL API has two code paths:
        1. Filter: /target?target_id__in=CHEMBL123 (may fail with 500)
        2. Direct: /target/CHEMBL123 (often works when filter fails)
        """
        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
        call_count = 0

        async def mock_get(url, params=None):
            await asyncio.sleep(0)
            nonlocal call_count
            call_count += 1

            # Filter endpoint (has __in param) - always fails with 500
            if params and "target_chembl_id__in" in params:
                raise RetryExhaustedError(
                    url, attempts=3, last_error=Exception("500 Internal Server Error")
                )

            # Direct endpoint (no __in param, URL contains ID) - succeeds
            if "/target/CHEMBL123" in url:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "target_chembl_id": "CHEMBL123",
                    "target_type": "SINGLE PROTEIN",
                    "pref_name": "Test Target",
                }
                return mock_response

            # Unknown endpoint
            raise RuntimeError(f"Unexpected URL: {url}")

        mock_http_client.get = mock_get

        records = []
        async for record in adapter.fetch_filtered(
            entity_type="target",
            filter_ids=["CHEMBL123"],
            filter_field="target_id",
        ):
            records.append(record)

        # Should get 1 record via direct endpoint fallback
        assert len(records) == 1
        assert records[0]["target_chembl_id"] == "CHEMBL123"

        # Verify direct_endpoint_fallback_success was logged
        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and c.args[0] == "direct_endpoint_fallback_success"
        ]
        assert len(info_calls) == 1

    @pytest.mark.asyncio
    async def test_direct_endpoint_fallback_also_fails(
        self, mock_http_client, mock_logger
    ):
        """Test logging when both filter and direct endpoints fail."""
        adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)

        async def mock_get(url, params=None):
            # Both endpoints fail
            raise RetryExhaustedError(
                url, attempts=3, last_error=Exception("500 Internal Server Error")
            )

        mock_http_client.get = mock_get

        records = []
        async for record in adapter.fetch_filtered(
            entity_type="target",
            filter_ids=["CHEMBL123"],
            filter_field="target_id",
        ):
            records.append(record)

        # No records returned
        assert len(records) == 0

        # Verify direct_endpoint_fallback_failed was logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "direct_endpoint_fallback_failed"
        ]
        assert len(warning_calls) == 1

        # Verify single_id_fetch_failed was logged (final failure)
        error_calls = [
            c
            for c in mock_logger.error.call_args_list
            if c.args and c.args[0] == "single_id_fetch_failed"
        ]
        assert len(error_calls) == 1


@pytest.mark.unit
class TestChemblAdapterExtractionParams:
    """Tests for extraction_params support in ChemblAdapter."""

    def test_build_params_without_extraction_params(
        self, mock_http_client, mock_logger
    ):
        """Regression: _build_params returns only format+limit+offset without extraction_params."""
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=500),
        )

        params = adapter._build_params(offset=0)

        assert params == {"format": "json", "limit": 500, "offset": 0}

    def test_build_params_with_extraction_params(self, mock_http_client, mock_logger):
        """Test that extraction_params are merged into _build_params output."""
        from bioetl.domain.models.filter import ExtractionParams

        ep = ExtractionParams(
            params={
                "standard_type__in": "IC50,Ki",
                "pchembl_value__isnull": False,
            }
        )
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=500),
            extraction_params=ep,
        )

        params = adapter._build_params(offset=0)

        assert params["format"] == "json"
        assert params["limit"] == 500
        assert params["offset"] == 0
        assert params["standard_type__in"] == "IC50,Ki"
        assert params["pchembl_value__isnull"] is False

    def test_build_params_extraction_params_merged_with_pagination_target(
        self, mock_http_client, mock_logger
    ):
        """Test extraction_params merge with pagination for target entity."""
        from bioetl.domain.models.filter import ExtractionParams

        ep = ExtractionParams(params={"standard_units": "nM"})
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            extraction_params=ep,
        )

        # "target" uses limit/offset pagination.
        params = adapter._build_params(offset=0, entity_type="target")

        assert params["format"] == "json"
        assert params["limit"] == adapter._get_effective_batch_size()
        assert params["offset"] == 0
        assert params["standard_units"] == "nM"

    def test_build_params_empty_extraction_params_no_effect(
        self, mock_http_client, mock_logger
    ):
        """Test that empty ExtractionParams doesn't add extra keys."""
        from bioetl.domain.models.filter import ExtractionParams

        ep = ExtractionParams.empty()
        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            adapter_config=AdapterConfig(page_size=500),
            extraction_params=ep,
        )

        params = adapter._build_params(offset=0)

        assert params == {"format": "json", "limit": 500, "offset": 0}

    def test_init_logs_extraction_params_when_configured(
        self, mock_http_client, mock_logger
    ):
        """Test that non-empty extraction_params are logged at init."""
        from bioetl.domain.models.filter import ExtractionParams

        ep = ExtractionParams(
            params={
                "standard_type__in": "IC50,Ki",
                "pchembl_value__isnull": False,
            }
        )
        ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            extraction_params=ep,
        )

        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and c.args[0] == "chembl_extraction_params_configured"
        ]
        assert len(info_calls) == 1
        kwargs = info_calls[0].kwargs
        assert kwargs["provider"] == "chembl"
        assert kwargs["param_count"] == 2
        assert "standard_type__in" in kwargs["query_string"]

    def test_init_no_log_when_extraction_params_empty(
        self, mock_http_client, mock_logger
    ):
        """Test that empty extraction_params don't trigger logging."""
        ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and c.args[0] == "chembl_extraction_params_configured"
        ]
        assert len(info_calls) == 0

    def test_init_accepts_fallback_fetch_service(
        self, mock_http_client, mock_logger
    ) -> None:
        """Test constructor compatibility with helper-service DI wiring."""
        fallback_fetch_service = MagicMock(spec=FallbackFetchOrchestrator)

        adapter = ChemblAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            fallback_fetch_service=fallback_fetch_service,
        )

        assert adapter.fallback_fetch_service is fallback_fetch_service
