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
"""Unit tests for PubMedAdapter.

Tests the PubMed adapter's health check and lifecycle methods.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.pagination import PaginationTruncatedError
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from bioetl.infrastructure.adapters.pubmed._filter_fetch_support import (
    resolve_pmids_for_fetch,
)
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


pytestmark = pytest.mark.unit


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
async def test_pubmed_client_aclose_closes_http_client(adapter, mock_http_client):
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
async def test_pubmed_pubmed_client__on_slow_response__3c82ad83(
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


def test_pubmed_pubmed_client__provider_name__971b8628(adapter):
    """Test that provider_name is set correctly."""
    assert adapter.provider_name == "pubmed"


def test_pubmed_pubmed_client__health_endpoint__37d580de(adapter):
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


def _esearch_page(*, count: object, ids: list[str]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = {"esearchresult": {"count": count, "idlist": ids}}
    return response


@pytest.mark.asyncio
async def test_get_pmids_pages_retstart_until_count(adapter, mock_http_client) -> None:
    """A short first idlist is incomplete while count is still larger."""
    pages = {
        0: _esearch_page(count="5", ids=["1", "2"]),
        2: _esearch_page(count="5", ids=["3", "4", "5"]),
    }

    async def get(_url: str, params: dict[str, str]) -> MagicMock:
        retstart = int(params.get("retstart", "0"))
        return pages[retstart]

    mock_http_client.get = AsyncMock(side_effect=get)

    assert await adapter._get_pmids("cancer", 10) == ["1", "2", "3", "4", "5"]
    first_params = mock_http_client.get.await_args_list[0].kwargs["params"]
    second_params = mock_http_client.get.await_args_list[1].kwargs["params"]
    assert "retstart" not in first_params
    assert first_params["retmax"] == "10"
    assert second_params["retstart"] == "2"
    assert second_params["retmax"] == "8"


@pytest.mark.asyncio
async def test_get_pmids_keeps_filled_limit_below_count(
    adapter, mock_http_client
) -> None:
    """An idlist that fills the requested ceiling is complete even if count is larger."""
    mock_http_client.get = AsyncMock(
        return_value=_esearch_page(count=100, ids=["1", "2"])
    )

    assert await adapter._get_pmids("cancer", 2) == ["1", "2"]
    assert mock_http_client.get.await_count == 1
    assert mock_http_client.get.await_args_list[0].kwargs["params"]["retmax"] == "2"


@pytest.mark.asyncio
async def test_get_pmids_raises_when_next_page_is_empty(
    adapter, mock_http_client
) -> None:
    """An empty follow-up page must not turn a short idlist into a full result."""
    pages = {
        0: _esearch_page(count=5, ids=["1"]),
        1: _esearch_page(count=5, ids=[]),
    }

    async def get(_url: str, params: dict[str, str]) -> MagicMock:
        return pages[int(params.get("retstart", "0"))]

    mock_http_client.get = AsyncMock(side_effect=get)

    with pytest.raises(PaginationTruncatedError) as caught:
        await adapter._get_pmids("cancer", 5)

    assert caught.value.reason == "empty_page"
    assert mock_http_client.get.await_args_list[1].kwargs["params"]["retstart"] == "1"


@pytest.mark.asyncio
async def test_get_pmids_raises_when_page_repeats(adapter, mock_http_client) -> None:
    """A repeated idlist must not be returned as the whole count."""
    mock_http_client.get = AsyncMock(return_value=_esearch_page(count=5, ids=["1"]))

    with pytest.raises(PaginationTruncatedError) as caught:
        await adapter._get_pmids("cancer", 5)

    assert caught.value.reason == "repeated_page"
    assert mock_http_client.get.await_args_list[1].kwargs["params"]["retstart"] == "1"


@pytest.mark.asyncio
async def test_get_pmids_raises_when_repeated_page_fills_count(
    adapter, mock_http_client
) -> None:
    """A duplicate page must not satisfy count by length alone."""
    pages = {
        0: _esearch_page(count=4, ids=["1", "2"]),
        2: _esearch_page(count=4, ids=["1", "2"]),
    }

    async def get(_url: str, params: dict[str, str]) -> MagicMock:
        return pages[int(params.get("retstart", "0"))]

    mock_http_client.get = AsyncMock(side_effect=get)

    with pytest.raises(PaginationTruncatedError) as caught:
        await adapter._get_pmids("cancer", 4)

    assert caught.value.reason == "repeated_page"


@pytest.mark.asyncio
async def test_get_pmids_raises_when_pages_overlap(adapter, mock_http_client) -> None:
    """Partial page overlap must not pad list length up to count."""
    pages = {
        0: _esearch_page(count=4, ids=["1", "2"]),
        2: _esearch_page(count=4, ids=["2", "3"]),
    }

    async def get(_url: str, params: dict[str, str]) -> MagicMock:
        return pages[int(params.get("retstart", "0"))]

    mock_http_client.get = AsyncMock(side_effect=get)

    with pytest.raises(PaginationTruncatedError) as caught:
        await adapter._get_pmids("cancer", 4)

    assert caught.value.reason == "overlapping_page"
    assert mock_http_client.get.await_args_list[1].kwargs["params"]["retstart"] == "2"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"error": "upstream failure"},
        {"esearchresult": None},
        {"esearchresult": {}},
        {"esearchresult": {"idlist": "1"}},
        {"esearchresult": {"count": "2", "idlist": ["1", {}]}},
    ],
)
async def test_get_pmids_rejects_malformed_esearch_payload(
    adapter, mock_http_client, payload: object
) -> None:
    """A broken ESearch body must not look like a successful empty search."""
    response = MagicMock()
    response.json.return_value = payload
    mock_http_client.get = AsyncMock(return_value=response)

    with pytest.raises(PaginationTruncatedError) as caught:
        await adapter._get_pmids("cancer", 10)

    assert caught.value.reason == "malformed_payload"


@pytest.mark.asyncio
async def test_get_pmids_accepts_explicit_empty_idlist(
    adapter, mock_http_client
) -> None:
    """A result object with an empty idlist is a real empty search."""
    mock_http_client.get = AsyncMock(return_value=_esearch_page(count="0", ids=[]))

    assert await adapter._get_pmids("cancer", 10) == []


@pytest.mark.asyncio
async def test_resolve_pmids_for_fetch_pages_above_default_ceiling(
    adapter, mock_http_client
) -> None:
    """limit=None uses the 10000 ceiling and still reconciles a short first page."""
    pages = {
        0: _esearch_page(count=4, ids=["1", "2"]),
        2: _esearch_page(count=4, ids=["3", "4"]),
    }

    async def get(_url: str, params: dict[str, str]) -> MagicMock:
        return pages[int(params.get("retstart", "0"))]

    mock_http_client.get = AsyncMock(side_effect=get)

    assert await resolve_pmids_for_fetch(adapter, query="term", limit=None) == [
        "1",
        "2",
        "3",
        "4",
    ]
    first_params = mock_http_client.get.await_args_list[0].kwargs["params"]
    assert first_params["retmax"] == "10000"
    assert mock_http_client.get.await_args_list[1].kwargs["params"]["retstart"] == "2"


@pytest.mark.asyncio
async def test_resolve_pmids_for_fetch_signals_short_default_ceiling(
    adapter, mock_http_client
) -> None:
    """The default 10000 ceiling is not a complete result when count is larger."""
    mock_http_client.get = AsyncMock(return_value=_esearch_page(count=12000, ids=["1"]))

    with pytest.raises(PaginationTruncatedError) as caught:
        await resolve_pmids_for_fetch(adapter, query=None, limit=None)

    assert caught.value.reason == "repeated_page"
    assert mock_http_client.get.await_args_list[1].kwargs["params"]["retstart"] == "1"


def test_xml_parser_enforces_elapsed_time_budget(monkeypatch):
    from bioetl.infrastructure.adapters.pubmed import xml_processor as subject

    target = subject.LimitedParseTarget()
    target.max_time = 0.1
    monkeypatch.setattr(subject.time, "monotonic", lambda: target.start_time + 1)
    with pytest.raises(ValueError, match="XML time limit exceeded"):
        target._raise_if_time_exceeded()
