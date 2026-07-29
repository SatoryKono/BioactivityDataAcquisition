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
"""Unit tests for CrossRefAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import RequestError

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_bundle


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_http_client():
    """Fixture for mock HTTP client."""
    return AsyncMock()


@pytest.fixture
def mock_logger():
    """Fixture for mock logger."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    """Fixture for CrossRefAdapter instance."""
    return create_crossref_adapter(
        http_client=mock_http_client,
        logger=mock_logger,
        settings=None,
        mailto="test@example.com",
    )


def test_post_init_preserves_injected_crossref_runtime_collaborators(
    mock_http_client, mock_logger
):
    """Injected CrossRef runtime collaborators should survive __post_init__ wiring."""
    query_builder = MagicMock()
    response_mapper = MagicMock()
    batch_fetcher = MagicMock()
    search_paginator = MagicMock()
    title_fallback_handler = MagicMock()
    fetch_flow = MagicMock()
    runtime_bundle = build_http_adapter_runtime_bundle("crossref", logger=mock_logger)

    adapter = CrossRefAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        mailto="test@example.com",
        dependency_context=runtime_bundle.dependency_context,
        fallback_fetch_service=runtime_bundle.fallback_fetch_service,
        query_builder=query_builder,
        response_mapper=response_mapper,
        batch_fetcher=batch_fetcher,
        search_paginator=search_paginator,
        title_fallback_handler=title_fallback_handler,
        fetch_flow=fetch_flow,
    )

    assert adapter._query_builder is query_builder
    assert adapter._response_mapper is response_mapper
    assert adapter._batch_fetcher is batch_fetcher
    assert adapter._search_paginator is search_paginator
    assert adapter._fallback_handler is title_fallback_handler
    assert adapter._fetch_flow is fetch_flow


def test_crossref_client__base_collaborators__e6edb72e(
    mock_http_client, mock_logger
) -> None:
    """Dataclass adapter should delegate shared base initialization."""
    error_handler = MagicMock()
    metrics = MagicMock()
    adapter_metrics = AdapterMetricsRecorder(metrics, "crossref")
    request_collector = APIRequestCollector()

    adapter = create_crossref_adapter(
        http_client=mock_http_client,
        logger=mock_logger,
        settings=None,
        mailto="test@example.com",
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
async def test_fetch_by_doi_success(adapter, mock_http_client):
    """Test successful fetch by DOI."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"items": [{"title": ["Test Title"]}]}
    }
    mock_http_client.get.return_value = mock_response

    results = [
        res
        async for res in adapter.fetch(
            entity_type="work", filter_ids=["10.1234/test"], filter_field="doi"
        )
    ]

    assert len(results) == 1
    assert results[0]["title"] == ["Test Title"]
    assert results[0]["_lookup_method"] == "doi"
    mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_by_doi_not_found(adapter, mock_http_client, mock_logger):
    """Test fetch by DOI when DOI is not found (404)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"items": []}}
    mock_http_client.get.return_value = mock_response

    results = [
        res
        async for res in adapter.fetch(
            entity_type="work", filter_ids=["10.1234/notfound"], filter_field="doi"
        )
    ]

    assert len(results) == 0


@pytest.mark.asyncio
async def test_fetch_by_doi_http_error(adapter, mock_http_client, mock_logger):
    """Test fetch by DOI with HTTP error (e.g., 500)."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http_client.get.return_value = mock_response

    results = [
        res
        async for res in adapter.fetch(
            entity_type="work", filter_ids=["10.1234/error"], filter_field="doi"
        )
    ]

    assert len(results) == 0
    mock_logger.warning.assert_called_with(
        "crossref_batch_fetch_failed",
        status_code=500,
        doi_count=1,
    )


@pytest.mark.asyncio
async def test_fetch_by_doi_request_error(adapter, mock_http_client, mock_logger):
    """Test fetch by DOI with a request error (e.g., network issue)."""
    mock_http_client.get.side_effect = RequestError("Network error")

    results = [
        res
        async for res in adapter.fetch(
            entity_type="work",
            filter_ids=["10.1234/network-error"],
            filter_field="doi",
        )
    ]

    assert len(results) == 0
    mock_logger.warning.assert_called_with(
        "crossref_batch_fetch_error",
        error="Network error",
        doi_count=1,
    )


@pytest.mark.asyncio
async def test_crossref_client__health_check_healthy__089dc662(
    adapter, mock_http_client
):
    """Test health_check returns HEALTHY on success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_check_degraded_on_transient_error(adapter, mock_http_client):
    """Test health_check returns DEGRADED on transient HTTP errors."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_health_check_unhealthy_on_auth_error(adapter, mock_http_client):
    """Test health_check returns UNHEALTHY on auth failures."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_health_check_unhealthy_on_request_error(adapter, mock_http_client):
    """Test health_check returns UNHEALTHY on request error."""
    mock_http_client.get_once = AsyncMock(
        side_effect=RequestError("Connection refused")
    )

    result = await adapter.health_check()

    assert result == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_health_check_returns_degraded_on_slow_response(
    adapter, mock_http_client, mock_logger
):
    """Test health_check returns DEGRADED when response takes >5 seconds."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_http_client.get_once = AsyncMock(return_value=mock_response)

    # Simulate slow response by patching time.monotonic in both modules
    # (helper module and health_check_mixin where HealthCheckContext uses it)
    call_count = 0

    def mock_monotonic_func():
        nonlocal call_count
        call_count += 1
        # First call (start_time) returns 0, subsequent calls return 6 (elapsed = 6 sec)
        return 0.0 if call_count <= 2 else 6.0

    mock_monotonic = MagicMock(side_effect=mock_monotonic_func)

    with (
        patch(
            "bioetl.infrastructure.adapters.crossref.client_observability_helpers.time.monotonic",
            new=mock_monotonic,
        ),
        patch(
            "bioetl.infrastructure.adapters.health_check_mixin.time.monotonic",
            new=mock_monotonic,
        ),
    ):
        result = await adapter.health_check()

    assert result == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_crossref_client__fetch_multi_filtered__raises_not_implemented(
    adapter,
) -> None:
    """CrossRef adapter should keep rejecting unsupported multi-filter fetches."""
    with pytest.raises(NotImplementedError, match="does not support multi-field"):
        await adapter.fetch_multi_filtered(
            entity_type="work",
            filters={"doi": ["10.1000/test"]},
        ).__anext__()


@pytest.mark.asyncio
async def test_aclose_delegates_to_http_client_exit(adapter, mock_http_client) -> None:
    """Adapter close should delegate to the underlying HTTP client."""
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    await adapter.aclose()

    mock_http_client.__aexit__.assert_awaited_once_with(None, None, None)
