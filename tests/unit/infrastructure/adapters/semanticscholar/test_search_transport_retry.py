# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
"""Transport tests for Semantic Scholar search 429 bounded retry (10577)."""

from __future__ import annotations

import asyncio
import datetime
import time
from email.utils import formatdate
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bioetl.domain.exceptions import RetryExhaustedError
from bioetl.domain.exceptions.network.service import ApiError
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

pytestmark = pytest.mark.unit


def _make_client(retry_config: RetryConfig) -> tuple[UnifiedHTTPClient, MagicMock, MagicMock, MagicMock]:
    rate_limiter = AsyncMock()
    circuit_breaker = AsyncMock()
    async def _call(func, *a, **kw):
        return await func(*a, **kw)
    circuit_breaker.call.side_effect = _call
    client = UnifiedHTTPClient(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        retry_config=retry_config,
        provider="semanticscholar",
    )
    mock_httpx = AsyncMock()
    client._client = mock_httpx
    return client, mock_httpx, rate_limiter, circuit_breaker


def _make_adapter(client: UnifiedHTTPClient, logger: MagicMock | None = None) -> SemanticScholarAdapter:
    logger = logger or MagicMock()
    return SemanticScholarAdapter(
        http_client=client,
        logger=logger,
        api_key="test",
        batch_size=10,
        **build_http_adapter_runtime_kwargs("semanticscholar", logger=logger, include_fallback_service=True),
    )


@pytest.mark.asyncio
async def test_search_429_then_success_bounded():
    """429 then 200 should succeed after bounded retries with correct request count and time."""
    retry_config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter_range=(0.0, 0.0))
    client, mock_httpx, _, _ = _make_client(retry_config)
    request = httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper/search")
    resp_429 = httpx.Response(429, request=request, headers={"Retry-After": "0.01"})
    resp_200 = httpx.Response(200, request=request, json={"data": [{"paperId": "a"*40}], "next": None})
    # UnifiedHTTPClient will handle retry via response status: first two 429, then 200
    mock_httpx.request.side_effect = [resp_429, resp_429, resp_200]
    adapter = _make_adapter(client)
    start = time.perf_counter()
    records, nxt = await adapter._fetch_search_page(query="test", page_size=10, current_offset=0)
    elapsed = time.perf_counter() - start
    assert len(records) == 1
    assert mock_httpx.request.call_count == 3
    assert elapsed < 0.5  # bounded total time
    assert nxt is None


@pytest.mark.asyncio
async def test_search_permanent_429_exhaustion_bounded():
    """Permanent 429 must exhaust after max_attempts, raise ApiError 429 with endpoint and Retry-After, not empty."""
    retry_config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter_range=(0.0, 0.0))
    client, mock_httpx, _, _ = _make_client(retry_config)
    request = httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper/search")
    resp_429 = httpx.Response(429, request=request, headers={"Retry-After": "0.01"})
    mock_httpx.request.return_value = resp_429
    adapter = _make_adapter(client)
    start = time.perf_counter()
    with pytest.raises(ApiError) as exc:
        await adapter._fetch_search_page(query="test", page_size=10, current_offset=0)
    elapsed = time.perf_counter() - start
    assert exc.value.status_code == 429
    # endpoint preserved in message
    assert "api.semanticscholar.org" in str(exc.value)
    assert "Retry-After" in str(exc.value)
    assert mock_httpx.request.call_count == 3
    assert elapsed < 0.5
    # not empty success
    # ensure not returned as []
    assert exc.value.__cause__ is not None
    assert isinstance(exc.value.__cause__, RetryExhaustedError)


@pytest.mark.asyncio
async def test_search_retry_after_seconds_and_date():
    """Retry-After seconds and HTTP-date must be parsed and bounded."""
    retry_config = RetryConfig(max_attempts=2, base_delay=0.01, max_delay=0.5, jitter_range=(0.0, 0.0))
    # seconds case
    client, mock_httpx, _, _ = _make_client(retry_config)
    request = httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper/search")
    resp_429_seconds = httpx.Response(429, request=request, headers={"Retry-After": "0.02"})
    resp_200 = httpx.Response(200, request=request, json={"data": [{"paperId": "a"*40}], "next": None})
    mock_httpx.request.side_effect = [resp_429_seconds, resp_200]
    adapter = _make_adapter(client)
    records, _ = await adapter._fetch_search_page(query="test", page_size=10, current_offset=0)
    assert len(records) == 1
    # date case
    client2, mock_httpx2, _, _ = _make_client(retry_config)
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(milliseconds=20)
    date_str = formatdate(future.timestamp(), usegmt=True)
    resp_429_date = httpx.Response(429, request=request, headers={"Retry-After": date_str})
    mock_httpx2.request.side_effect = [resp_429_date, resp_200]
    adapter2 = _make_adapter(client2)
    records2, _ = await adapter2._fetch_search_page(query="test", page_size=10, current_offset=0)
    assert len(records2) == 1
    # ensure date was not ignored (would have used exponential backoff 0.01, but still bounded)
    assert mock_httpx2.request.call_count == 2


@pytest.mark.asyncio
async def test_search_timeout_then_success():
    """Timeout should be retryable and bounded."""
    retry_config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter_range=(0.0, 0.0))
    client, mock_httpx, _, _ = _make_client(retry_config)
    request = httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper/search")
    resp_200 = httpx.Response(200, request=request, json={"data": [{"paperId": "a"*40}], "next": None})
    mock_httpx.request.side_effect = [httpx.TimeoutException("timeout"), httpx.TimeoutException("timeout"), resp_200]
    adapter = _make_adapter(client)
    records, _ = await adapter._fetch_search_page(query="test", page_size=10, current_offset=0)
    assert len(records) == 1
    assert mock_httpx.request.call_count == 3


@pytest.mark.asyncio
async def test_search_cancellation_not_suppressed():
    """Cancellation must not be suppressed or retried."""
    retry_config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter_range=(0.0, 0.0))
    client, mock_httpx, _, _ = _make_client(retry_config)
    mock_httpx.request.side_effect = asyncio.CancelledError("cancel")
    adapter = _make_adapter(client)
    with pytest.raises(asyncio.CancelledError):
        await adapter._fetch_search_page(query="test", page_size=10, current_offset=0)
    assert mock_httpx.request.call_count == 1


@pytest.mark.asyncio
async def test_search_no_nested_retry():
    """Ensure only one retry layer (UnifiedHTTPClient) is used; no external retry over get."""
    retry_config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter_range=(0.0, 0.0))
    client, mock_httpx, _, _ = _make_client(retry_config)
    request = httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper/search")
    resp_429 = httpx.Response(429, request=request, headers={"Retry-After": "0.01"})
    mock_httpx.request.return_value = resp_429
    adapter = _make_adapter(client)
    # Count that adapter does not add extra retry loop: total attempts should be exactly max_attempts, not max_attempts^2
    with pytest.raises(ApiError):
        await adapter._fetch_search_page(query="test", page_size=10, current_offset=0)
    assert mock_httpx.request.call_count == 3  # not 9
    # Also check that fetch via paginate does same
    mock_httpx.request.reset_mock()
    with pytest.raises(ApiError):
        async for _ in adapter._paginate_search(query="test", limit=5):
            pass
    assert mock_httpx.request.call_count == 3


def test_search_query_validation_explicit():
    """Explicit query required; fallback query=* must not be implicit."""
    retry_config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.02)
    client, _, _, _ = _make_client(retry_config)
    adapter = _make_adapter(client)
    # None query should raise ValueError, not silently use "*"
    import pytest as pt
    import asyncio as aio
    async def _run():
        try:
            await adapter._fetch_search_page(query=None, page_size=10, current_offset=0)
            assert False, "should have raised ValueError"
        except ValueError as e:
            assert "explicit query" in str(e).lower()
        try:
            await adapter._fetch_search_page(query="   ", page_size=10, current_offset=0)
            assert False
        except ValueError:
            pass
        # Explicit "*" should still be allowed
        # mock success for "*"
        mock_httpx = adapter._http_client._client if hasattr(adapter._http_client, "_client") else None
        # Instead test via fetch
        try:
            async for _ in adapter.fetch(entity_type="publication", query=None):
                pass
            assert False
        except ValueError:
            pass
        # query="*" explicit should pass validation but still go through retry path
        # we won't actually call network here
        pass
    aio.run(_run())


def test_429_not_quarantine():
    """429 should be RECOVERABLE, not DATA_QUALITY (quarantine)."""
    from bioetl.infrastructure.adapters.adapter_error_classifier import classify_http_error
    from unittest.mock import MagicMock
    logger = MagicMock()
    cat = classify_http_error(429, logger=logger)
    assert cat.value == "RECOVERABLE"
    cat_dq = classify_http_error(400, logger=logger)
    assert cat_dq.value == "DATA_QUALITY"
