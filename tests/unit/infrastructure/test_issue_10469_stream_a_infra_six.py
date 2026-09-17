"""Remaining L12 + high-missing adapter residuals for #10469 / #10516."""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl._entity_mapping_lookup import (
    is_known_entity_type,
)
from bioetl.infrastructure.adapters.chembl.entity_mapper import ChemblEntityMapper
from bioetl.infrastructure.adapters.chembl.fetch_paging_mixin import ChemblFetchPagingMixin
from bioetl.infrastructure.adapters.common.composable_fallback import (
    _get_optional_str_attr,
)
from bioetl.infrastructure.adapters.crossref._client_ops import (
    crossref_fetch_filtered,
    crossref_fetch_filtered_with_fallback,
)
from bioetl.infrastructure.adapters.crossref._client_port_surface import (
    _CrossRefPortSurfaceMixin,
)
from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter
from bioetl.infrastructure.adapters.crossref.query_builder import (
    validate_crossref_entity_type,
)
from bioetl.infrastructure.adapters.http._client_retry_policy import (
    _status_code_from_error,
)
from bioetl.infrastructure.adapters.openalex._filter_fetch_flow import (
    iterate_fetch_request,
)
from bioetl.infrastructure.adapters.openalex._filter_fetch_requests import _FetchRequest
from bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin import (
    OpenAlexAdapterFilterFetchMixin,
)
from bioetl.infrastructure.adapters.openalex.health_adapter_mixin import (
    OpenAlexAdapterHealthMixin,
)
from bioetl.infrastructure.adapters.pubchem._client_fetch_surface import (
    _PubChemClientFetchMixin,
)
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.pubmed._fetch import PubMedFetchMixin
from bioetl.infrastructure.adapters.pubmed.adapter_filter_fetch_mixin import (
    PubMedAdapterFilterFetchMixin,
)
from bioetl.infrastructure.adapters.pubmed.xml_processor import PubMedXmlProcessor

pytestmark = pytest.mark.unit


async def _aiter(items: list[object]):
    for item in items:
        yield item


class _PortSurface(_CrossRefPortSurfaceMixin):
    CROSSREF_API_BASE = "https://api.crossref.org"
    CROSSREF_HEALTH_ERRORS = (RuntimeError,)

    def __init__(self, flow: object) -> None:
        self._fetch_flow = flow


class _OpenAlexFetchHost(OpenAlexAdapterFilterFetchMixin):
    def __init__(self) -> None:
        self._cursor_flow = SimpleNamespace(
            iter_query_results=lambda **_kwargs: _aiter([{"id": "oa"}])
        )


class _PagingHost(ChemblFetchPagingMixin):
    def __init__(self) -> None:
        self._mapper = SimpleNamespace(get_resource_url=lambda _entity: "https://x/activity")

    def _build_params(self, offset: int, entity_type: str) -> dict[str, int]:
        del offset, entity_type
        return {"limit": 25}


class _PubChemHost(_PubChemClientFetchMixin):
    def __init__(self) -> None:
        self._strategies = SimpleNamespace()


@pytest.mark.asyncio
async def test_crossref_client_ops_and_port_surface_yields() -> None:
    flow = SimpleNamespace(
        fetch_filtered=lambda **_kwargs: _aiter([{"DOI": "10.1/a"}]),
        fetch_filtered_with_fallback=lambda **_kwargs: _aiter([{"DOI": "10.1/b"}]),
    )
    filtered = [
        row
        async for row in crossref_fetch_filtered(
            flow=flow,  # type: ignore[arg-type]
            entity_type="publication",
            filter_ids=["10.1/a"],
            filter_field="doi",
            limit=1,
        )
    ]
    fallback = [
        row
        async for row in crossref_fetch_filtered_with_fallback(
            flow=flow,  # type: ignore[arg-type]
            entity_type="publication",
            filter_ids=["10.1/b"],
            filter_field="doi",
            fallback_mapping={"10.1/b": "title"},
            limit=1,
        )
    ]
    assert filtered == [{"DOI": "10.1/a"}]
    assert fallback == [{"DOI": "10.1/b"}]

    host = _PortSurface(flow)
    surface_rows = [
        row
        async for row in host.fetch_filtered("publication", ["10.1/a"], "doi", limit=1)
    ]
    surface_fallback = [
        row
        async for row in host.fetch_filtered_with_fallback(
            "publication",
            ["10.1/b"],
            "doi",
            {"10.1/b": "title"},
            limit=1,
        )
    ]
    assert surface_rows == [{"DOI": "10.1/a"}]
    assert surface_fallback == [{"DOI": "10.1/b"}]

    adapter_rows = [
        row
        async for row in CrossRefAdapter.fetch_filtered(
            host,  # type: ignore[arg-type]
            "publication",
            ["10.1/a"],
            "doi",
            1,
        )
    ]
    adapter_fallback = [
        row
        async for row in CrossRefAdapter.fetch_filtered_with_fallback(
            host,  # type: ignore[arg-type]
            "publication",
            ["10.1/b"],
            "doi",
            {"10.1/b": "title"},
            1,
        )
    ]
    assert adapter_rows == [{"DOI": "10.1/a"}]
    assert adapter_fallback == [{"DOI": "10.1/b"}]


@pytest.mark.asyncio
async def test_crossref_aclose_depth_and_query_builder() -> None:
    with pytest.raises(ValueError, match="got: dataset"):
        validate_crossref_entity_type("dataset")

    empty = SimpleNamespace(http_client=None)
    await CrossRefAdapter.aclose(empty)  # type: ignore[arg-type]

    class _DepthClient:
        def __init__(self) -> None:
            self.closed = False

        def _enter_depth(self) -> int:
            raise TypeError("descriptor")

        async def __aexit__(self, *_exc: object) -> None:
            self.closed = True

    typed_fail = SimpleNamespace(http_client=_DepthClient())
    typed_fail.http_client._enter_depth = _DepthClient._enter_depth  # type: ignore[method-assign]
    await CrossRefAdapter.aclose(typed_fail)  # type: ignore[arg-type]
    assert typed_fail.http_client.closed is True

    class _ZeroDepth:
        @classmethod
        def _enter_depth(cls, _self: object) -> int:
            return 0

        async def __aexit__(self, *_exc: object) -> None:
            raise AssertionError("must not close")

    zero = SimpleNamespace(http_client=_ZeroDepth())
    await CrossRefAdapter.aclose(zero)  # type: ignore[arg-type]

    attr_client = SimpleNamespace(_client_enter_depth=2, closed=False)

    async def _exit(*_exc: object) -> None:
        attr_client.closed = True

    attr_client.__aexit__ = _exit  # type: ignore[attr-defined]
    await CrossRefAdapter.aclose(SimpleNamespace(http_client=attr_client))  # type: ignore[arg-type]
    assert attr_client.closed is True


@pytest.mark.asyncio
async def test_openalex_filter_flow_query_and_health_aclose() -> None:
    class _Host:
        def _validate_entity_type(self, entity_type: str) -> None:
            del entity_type

        async def fetch_filtered(self, *_args: object, **_kwargs: object):
            yield {"id": "filtered"}
            return
            yield  # pragma: no cover

        async def _fetch_by_query(self, *, query: str, limit: int | None):
            yield {"query": query, "limit": limit}

    host = _Host()
    with pytest.raises(ValueError, match="filter_ids"):
        async for _row in iterate_fetch_request(
            host,  # type: ignore[arg-type]
            _FetchRequest(entity_type="work", query=None),
        ):
            raise AssertionError("should not yield")

    queried = [
        row
        async for row in iterate_fetch_request(
            host,  # type: ignore[arg-type]
            _FetchRequest(entity_type="work", query="kinase", limit=2),
        )
    ]
    assert queried == [{"query": "kinase", "limit": 2}]

    fetch_host = _OpenAlexFetchHost()
    by_query = [row async for row in fetch_host._fetch_by_query(query="kinase", limit=1)]
    assert by_query == [{"id": "oa"}]

    http = SimpleNamespace(closed=False)

    async def _aexit(*_exc: object) -> None:
        http.closed = True

    http.__aexit__ = _aexit  # type: ignore[attr-defined]
    health_host = SimpleNamespace(_http_client=http)
    await OpenAlexAdapterHealthMixin.aclose(health_host)  # type: ignore[arg-type]
    assert http.closed is True


@pytest.mark.asyncio
async def test_pubchem_fetch_surface_and_client_init_errors() -> None:
    host = _PubChemHost()
    with pytest.raises(ValueError, match="only supports 'compound'"):
        async for _row in host.fetch_filtered("assay", ["1"], "cid"):
            raise AssertionError("should not yield")
    with pytest.raises(ValueError, match="Unsupported filter_field"):
        async for _row in host.fetch_filtered("compound", ["1"], "name"):
            raise AssertionError("should not yield")

    with pytest.raises(TypeError, match="unexpected keyword"):
        PubChemAdapter(
            logger=MagicMock(),
            rate_limiter=MagicMock(),
            circuit_breaker=MagicMock(),
            thread_pool=MagicMock(),
            entity_mapper=MagicMock(),
            extra_kw="nope",
        )
    with pytest.raises(ValueError, match="fetch_strategies"):
        PubChemAdapter(
            logger=MagicMock(),
            rate_limiter=MagicMock(),
            circuit_breaker=MagicMock(),
            thread_pool=MagicMock(),
            entity_mapper=MagicMock(),
        )
    with pytest.raises(ValueError, match="error_handler"):
        PubChemAdapter(
            logger=MagicMock(),
            rate_limiter=MagicMock(),
            circuit_breaker=MagicMock(),
            thread_pool=MagicMock(),
            entity_mapper=MagicMock(),
            fetch_strategies=MagicMock(),
        )


@pytest.mark.asyncio
async def test_pubchem_health_empty_response() -> None:
    host = SimpleNamespace(
        rate_limiter=SimpleNamespace(acquire=AsyncMock()),
        circuit_breaker=SimpleNamespace(call=AsyncMock(return_value=[])),
        _run_in_executor=object(),
        logger=MagicMock(),
        provider_name="pubchem",
    )
    status = await PubChemAdapter._probe_health(host)  # type: ignore[arg-type]
    assert status is HealthStatus.DEGRADED
    host.logger.warning.assert_called()


def test_pubmed_xml_parse_error_and_entity_lookup() -> None:
    assert PubMedXmlProcessor.parse_response("<<<not-xml") is None
    assert is_known_entity_type("activity") is True
    assert ChemblEntityMapper.is_known_entity("activity") is True
    assert ChemblEntityMapper.is_known_entity("unknown_entity") is False
    assert _get_optional_str_attr(SimpleNamespace(name=None), "name", "fallback") == "fallback"

    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(503, request=request)
    error = httpx.HTTPStatusError("boom", request=request, response=response)
    assert _status_code_from_error(error) == 503
    assert _status_code_from_error(RuntimeError("x")) == 0
    config = RetryConfig()
    assert config.effective_retry_budget() >= 0


@pytest.mark.asyncio
async def test_chembl_page_iterator_stops_when_limit_exhausted() -> None:
    host = _PagingHost()
    pages = [page async for page in host._page_iterator("activity", limit=0)]
    assert pages == []


@pytest.mark.asyncio
async def test_pubmed_fetch_parse_error_limit_and_filter_mixin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FetchHost(PubMedFetchMixin):
        def __init__(self) -> None:
            self.email = "a@b.c"
            self.api_key = None
            self.provider_name = "pubmed"
            self.batch_size = 10
            self._logger = MagicMock()
            self._adapter_metrics = SimpleNamespace(
                measure_request=lambda *_a, **_k: nullcontext()
            )
            self._request_collector = SimpleNamespace(record_from_response=MagicMock())
            self.http_client = SimpleNamespace(
                get=AsyncMock(return_value=SimpleNamespace(text="<<<"))
            )
            self._error_handler = SimpleNamespace(handle_error=lambda **_k: RuntimeError("x"))

    fetch_host = _FetchHost()
    assert await fetch_host._fetch_batch(["1"]) == []
    fetch_host._logger.error.assert_called()

    async def _batch(_ids: list[str]) -> list[dict[str, str]]:
        return [{"pmid": "1"}, {"pmid": "2"}]

    fetch_host._fetch_batch = _batch  # type: ignore[method-assign]
    limited = [row async for row in fetch_host._yield_articles_from_pmids(["1", "2"], limit=1)]
    assert limited == [{"pmid": "1"}]

    async def _records(*_args: object, **_kwargs: object):
        yield {"pmid": "9"}

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.pubmed.adapter_filter_fetch_mixin.fetch_filtered_records",
        _records,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.pubmed.adapter_filter_fetch_mixin.fetch_records",
        _records,
    )
    mixin = PubMedAdapterFilterFetchMixin()
    filtered = [
        row async for row in mixin.fetch_filtered("publication", ["9"], "pmid", limit=1)
    ]
    fetched = [row async for row in mixin.fetch("publication", query="kinase")]
    assert filtered == [{"pmid": "9"}]
    assert fetched == [{"pmid": "9"}]


def test_chembl_client_request_helpers_delegate() -> None:
    from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

    host = SimpleNamespace(
        _mapper=MagicMock(),
        _logger=MagicMock(),
        _adapter_metrics=MagicMock(),
    )
    assert ChemblAdapter._build_filter_in_params(host, {"a": ["1", "2"]}) == {  # type: ignore[arg-type]
        "a__in": "1,2"
    }
    assert ChemblAdapter._get_projected_url_length(  # type: ignore[arg-type]
        host, "https://example.test/x", {"limit": 1}
    ) > 0
    seen: set[str] = set()
    duplicate = ChemblAdapter._is_duplicate_record_composite(  # type: ignore[arg-type]
        host,
        {"activity_id": "A1"},
        ("activity_id",),
        seen,
        "activity",
    )
    assert duplicate is False
    assert ChemblAdapter._is_duplicate_record_composite(  # type: ignore[arg-type]
        host,
        {"activity_id": "A1"},
        ("activity_id",),
        seen,
        "activity",
    ) is True
