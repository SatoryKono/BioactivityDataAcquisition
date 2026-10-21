"""Provider adapters retain HTTP failures and reject incomplete page evidence."""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from bioetl.domain.exceptions import ApiError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl._client_request_helpers import (
    process_chembl_response,
)
from bioetl.infrastructure.adapters.crossref import _doi_batch_processor as crossref
from bioetl.infrastructure.adapters.http._health_monitor_transitions import (
    check_clear_window,
)
from bioetl.infrastructure.adapters.openalex.health_probe import probe_openalex_health
from bioetl.infrastructure.adapters.semanticscholar._search_fetch_flow import (
    _SemanticScholarSearchFetchMixin,
)
from bioetl.infrastructure.adapters.semanticscholar.fallback import (
    SemanticScholarTitleFallbackHandler,
)

pytestmark = pytest.mark.unit


def test_invalid_chembl_pagination_metadata_cannot_confirm_complete_scan():
    response = httpx.Response(200, json={"molecules": [{"id": 1}], "page_meta": []})
    mapper = SimpleNamespace(get_plural_key=lambda entity: "molecules")
    with pytest.raises(ApiError, match="invalid page metadata"):
        process_chembl_response(
            response=response, entity_type="molecule", mapper=mapper
        )


def test_no_prior_provider_error_has_a_clear_recovery_window():
    assert check_clear_window(SimpleNamespace(last_error=None), now=0) is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 503])
async def test_crossref_raised_http_status_preserves_not_found_or_operational_error(
    monkeypatch, status
):
    request = httpx.Request("GET", "https://api.crossref.org/works/10.1000/example")
    error = httpx.HTTPStatusError(
        "upstream status",
        request=request,
        response=httpx.Response(status, request=request),
    )
    transport = AsyncMock(side_effect=error)
    monkeypatch.setattr(crossref, "perform_timed_crossref_get", transport)
    processor = crossref.DoiBatchProcessor(
        Mock(),
        Mock(),
        Mock(),
        "test@example.org",
        "https://api.crossref.org",
        lambda: {},
    )
    if status == 404:
        assert await processor.fetch_single("10.1000/example") is None
    else:
        with pytest.raises(crossref.CrossRefApiError) as caught:
            await processor.fetch_single("10.1000/example")
        assert caught.value.__cause__ is error
    transport.assert_awaited_once()


@pytest.mark.asyncio
async def test_openalex_raised_rate_limit_retains_degraded_health():
    request = httpx.Request("GET", "https://api.openalex.org/works")
    response = httpx.Response(429, request=request)
    error = httpx.HTTPStatusError("rate limited", request=request, response=response)
    client = SimpleNamespace(get_once=AsyncMock(side_effect=error))
    metrics = SimpleNamespace(measure_request=lambda route: nullcontext())
    status = await probe_openalex_health(
        api_base="https://api.openalex.org",
        mailto=None,
        api_key=None,
        http_client=client,
        logger=Mock(),
        adapter_metrics=metrics,
        headers={},
    )
    assert status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_semantic_scholar_transport_failure_is_not_an_empty_search():
    class Search(_SemanticScholarSearchFetchMixin):
        fields = "title"
        _adapter_metrics = SimpleNamespace(measure_request=lambda route: nullcontext())
        _http_client = SimpleNamespace(
            get=AsyncMock(side_effect=httpx.ConnectError("offline"))
        )

        def _build_headers(self):
            return {}

    with pytest.raises(ApiError, match="search transport failed") as caught:
        await Search()._fetch_search_page(
            query="publication", page_size=5, current_offset=0
        )
    assert isinstance(caught.value.__cause__, httpx.ConnectError)


@pytest.mark.asyncio
async def test_title_fallback_awaits_async_json_without_losing_the_record():
    record = {"paperId": "paper", "title": "A study"}
    response = SimpleNamespace(json=AsyncMock(return_value={"data": [record]}))
    client = SimpleNamespace(get=AsyncMock(return_value=response))
    handler = SemanticScholarTitleFallbackHandler(client, Mock())
    assert await handler._search_by_title("A study") == record
    response.json.assert_awaited_once_with()
