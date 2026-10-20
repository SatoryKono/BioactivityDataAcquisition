"""Behavioral DataSourcePort checks for the eight registered providers.

Fixtures stay in-process. These tests do not open sockets.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from bioetl.application.core.data_sources.idmapping import IDMappingDataSource
from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.domain.exceptions import ServiceUnavailableError
from bioetl.domain.types import CircuitBreakerState, HealthStatus, JsonDict
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.extensions: dict[str, object] = {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _ClosedBreaker:
    def get_state(self) -> CircuitBreakerState:
        return CircuitBreakerState.CLOSED

    def get_failure_count(self) -> int:
        return 0


class FakeHttp:
    """In-memory client with explicit enter depth and scripted calls."""

    def __init__(self) -> None:
        self.exit_calls = 0
        self.get_once_result: _Response | None = None
        self.get_once_error: BaseException | None = None
        self.get_result: _Response | None = None
        self.get_error: BaseException | None = None
        self._client_enter_depth = 0
        self.circuit_breaker = _ClosedBreaker()

    async def __aenter__(self) -> FakeHttp:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        self.exit_calls += 1

    def _enter_depth(self) -> int:
        return self._client_enter_depth

    async def get_once(self, *args: object, **kwargs: object) -> _Response:
        if self.get_once_error is not None:
            raise self.get_once_error
        if self.get_once_result is None:
            raise AssertionError("get_once was not scripted")
        return self.get_once_result

    async def get(self, *args: object, **kwargs: object) -> _Response:
        if self.get_error is not None:
            raise self.get_error
        if self.get_result is None:
            raise AssertionError("get was not scripted")
        return self.get_result


class _MappingClient:
    def __init__(self) -> None:
        self.exit_calls = 0
        self.health = HealthStatus.HEALTHY
        self.error: BaseException | None = None
        self.rows: dict[str, JsonDict] = {"CHEMBL1": {"uniprot_accession": "P12345"}}

    async def __aenter__(self) -> _MappingClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        self.exit_calls += 1

    async def health_check(self) -> HealthStatus:
        return self.health

    async def map_ids(
        self,
        *,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> dict[str, JsonDict]:
        if self.error is not None:
            raise self.error
        return {item: self.rows[item] for item in ids if item in self.rows}


class _Reader:
    def __init__(self, *, exists: bool = True, ids: list[str] | None = None) -> None:
        self.exists = exists
        self.ids = ids or []

    async def source_exists(self, *, source_path: str) -> bool:
        return self.exists

    async def read_ids(self, *, source_path: str, id_column: str) -> list[str]:
        return list(self.ids)


def _idmapping(
    client: _MappingClient,
    reader: _Reader | None = None,
    *,
    seed_ids: list[str] | None = None,
) -> IDMappingDataSource:
    return IDMappingDataSource(
        idmapping_client=client,  # type: ignore[arg-type]
        id_source_reader=reader or _Reader(),  # type: ignore[arg-type]
        input_path="memory.csv",
        logger=NoOpLogger(),
        seed_ids=seed_ids,
    )


async def _rows(stream: AsyncIterator[JsonDict]) -> list[JsonDict]:
    return [row async for row in stream]


def _http_kwargs(provider: str) -> dict[str, object]:
    return build_http_adapter_runtime_kwargs(
        provider,
        logger=NoOpLogger(),
        include_fallback_service=True,
    )


@pytest.mark.asyncio
async def test_idmapping_fetch_yields_mapped_record() -> None:
    source = _idmapping(_MappingClient(), seed_ids=["CHEMBL1"])
    rows = await _rows(source.fetch("idmapping"))
    assert rows == [{"target_id": "CHEMBL1", "uniprot_accession": "P12345"}]


@pytest.mark.asyncio
async def test_idmapping_fetch_yields_nothing_when_no_ids() -> None:
    source = _idmapping(_MappingClient(), _Reader(ids=[]))
    assert await _rows(source.fetch("idmapping")) == []


@pytest.mark.asyncio
async def test_idmapping_fetch_propagates_timeout_and_cancellation() -> None:
    timeout_source = _idmapping(_MappingClient(), seed_ids=["CHEMBL1"])
    timeout_source._client.error = TimeoutError("mapping timed out")  # type: ignore[attr-defined]
    with pytest.raises(TimeoutError, match="mapping timed out"):
        await _rows(timeout_source.fetch("idmapping"))

    cancelled = _idmapping(_MappingClient(), seed_ids=["CHEMBL1"])
    cancelled._client.error = asyncio.CancelledError()  # type: ignore[attr-defined]
    with pytest.raises(asyncio.CancelledError):
        await _rows(cancelled.fetch("idmapping"))


@pytest.mark.asyncio
async def test_idmapping_health_and_close_follow_injected_ports() -> None:
    healthy = _idmapping(_MappingClient(), _Reader(exists=True))
    assert await healthy.health_check() is HealthStatus.HEALTHY

    missing = _idmapping(_MappingClient(), _Reader(exists=False))
    assert await missing.health_check() is HealthStatus.UNHEALTHY

    degraded_client = _MappingClient()
    degraded_client.health = HealthStatus.DEGRADED
    degraded = _idmapping(degraded_client, _Reader(exists=True))
    assert await degraded.health_check() is HealthStatus.DEGRADED

    client = _MappingClient()
    source = _idmapping(client, seed_ids=["CHEMBL1"])
    await source.__aenter__()
    await source.aclose()
    await source.aclose()
    assert client.exit_calls == 1
    assert source._is_open is False


@pytest.mark.asyncio
async def test_chembl_fetch_yields_one_activity_and_propagates_cancellation() -> None:
    client = FakeHttp()
    client.get_result = _Response(
        {"activities": [{"activity_id": 1}], "page_meta": {"next": None}}
    )
    adapter = ChemblAdapter(http_client=client, logger=NoOpLogger())  # type: ignore[arg-type]
    rows = await _rows(adapter.fetch("activity"))
    assert rows == [{"activity_id": 1}]

    failing = FakeHttp()
    failing.get_error = asyncio.CancelledError()
    cancelled = ChemblAdapter(http_client=failing, logger=NoOpLogger())  # type: ignore[arg-type]
    with pytest.raises(asyncio.CancelledError):
        await _rows(cancelled.fetch("activity"))


@pytest.mark.asyncio
async def test_chembl_fetch_timeout_is_not_a_successful_record() -> None:
    client = FakeHttp()
    client.get_error = httpx.TimeoutException("chembl timed out")
    adapter = ChemblAdapter(http_client=client, logger=NoOpLogger())  # type: ignore[arg-type]
    with pytest.raises(ServiceUnavailableError, match="chembl timed out"):
        await _rows(adapter.fetch("activity"))


@pytest.mark.asyncio
async def test_pubmed_and_semanticscholar_health_success_timeout_and_cancel() -> None:
    pubmed_client = FakeHttp()
    pubmed_client.get_once_result = _Response({}, status_code=200)
    pubmed = PubMedAdapter(
        http_client=pubmed_client,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        email="test@example.com",
        **_http_kwargs("pubmed"),
    )
    assert await pubmed.health_check() is HealthStatus.HEALTHY

    pubmed_timeout = FakeHttp()
    pubmed_timeout.get_once_error = httpx.TimeoutException("pubmed timed out")
    pubmed_failed = PubMedAdapter(
        http_client=pubmed_timeout,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        email="test@example.com",
        **_http_kwargs("pubmed"),
    )
    failed = await pubmed_failed.health_check()
    assert isinstance(failed, HealthStatus)
    assert failed is not HealthStatus.HEALTHY

    pubmed_cancel = FakeHttp()
    pubmed_cancel.get_once_error = asyncio.CancelledError()
    pubmed_cancelled = PubMedAdapter(
        http_client=pubmed_cancel,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        email="test@example.com",
        **_http_kwargs("pubmed"),
    )
    with pytest.raises(asyncio.CancelledError):
        await pubmed_cancelled.health_check()

    scholar_client = FakeHttp()
    scholar_client.get_once_result = _Response({}, status_code=200)
    scholar = SemanticScholarAdapter(
        http_client=scholar_client,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        api_key="",
        batch_size=10,
        **_http_kwargs("semanticscholar"),
    )
    assert await scholar.health_check() is HealthStatus.HEALTHY

    scholar_timeout = FakeHttp()
    scholar_timeout.get_once_error = httpx.TimeoutException("scholar timed out")
    scholar_failed = SemanticScholarAdapter(
        http_client=scholar_timeout,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        api_key="",
        batch_size=10,
        **_http_kwargs("semanticscholar"),
    )
    scholar_status = await scholar_failed.health_check()
    assert scholar_status is not HealthStatus.HEALTHY

    scholar_cancel = FakeHttp()
    scholar_cancel.get_once_error = asyncio.CancelledError()
    scholar_cancelled = SemanticScholarAdapter(
        http_client=scholar_cancel,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        api_key="",
        batch_size=10,
        **_http_kwargs("semanticscholar"),
    )
    with pytest.raises(asyncio.CancelledError):
        await scholar_cancelled.health_check()


@pytest.mark.asyncio
async def test_aclose_releases_or_skips_the_injected_client() -> None:
    pubmed_client = FakeHttp()
    pubmed = PubMedAdapter(
        http_client=pubmed_client,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        email="test@example.com",
        **_http_kwargs("pubmed"),
    )
    await pubmed.aclose()
    await pubmed.aclose()
    assert pubmed_client.exit_calls == 2

    openalex_client = FakeHttp()
    openalex = OpenAlexAdapter(
        http_client=openalex_client,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        mailto="test@example.com",
        batch_size=10,
        **_http_kwargs("openalex"),
    )
    await openalex.aclose()
    assert openalex_client.exit_calls == 1

    scholar_client = FakeHttp()
    scholar = SemanticScholarAdapter(
        http_client=scholar_client,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        api_key="",
        batch_size=10,
        **_http_kwargs("semanticscholar"),
    )
    await scholar.aclose()
    assert scholar_client.exit_calls == 1

    crossref_client = FakeHttp()
    crossref_client._client_enter_depth = 0
    crossref = create_crossref_adapter(
        http_client=crossref_client,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        settings=None,
        mailto="test@example.com",
        batch_size=10,
    )
    await crossref.aclose()
    assert crossref_client.exit_calls == 0
    crossref_client._client_enter_depth = 1
    await crossref.aclose()
    await crossref.aclose()
    assert crossref_client.exit_calls == 2

    chembl_client = FakeHttp()
    chembl = ChemblAdapter(http_client=chembl_client, logger=NoOpLogger())  # type: ignore[arg-type]
    await chembl.aclose()
    await chembl.aclose()
    assert chembl_client.exit_calls == 0

    uniprot_client = FakeHttp()
    uniprot = UniProtAdapter(
        http_client=uniprot_client,  # type: ignore[arg-type]
        logger=NoOpLogger(),
        **_http_kwargs("uniprot"),
    )
    await uniprot.aclose()
    assert uniprot_client.exit_calls == 0


@pytest.mark.asyncio
async def test_pubchem_aclose_shuts_down_only_an_owned_pool() -> None:
    from concurrent.futures import ThreadPoolExecutor

    from bioetl.infrastructure.adapters.common.adapter_defaults import (
        create_default_error_handler,
    )
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

    logger = NoOpLogger()
    borrowed = ThreadPoolExecutor(max_workers=1)
    owned = ThreadPoolExecutor(max_workers=1)
    try:
        borrowed_adapter = PubChemAdapter(
            logger=logger,
            rate_limiter=TokenBucketRateLimiter(
                rate=5.0, capacity=10, provider="pubchem"
            ),
            circuit_breaker=CircuitBreakerGuard(provider="pubchem"),
            thread_pool=borrowed,
            owns_thread_pool=False,
            error_handler=create_default_error_handler(logger=logger, metrics=None),
            request_collector=APIRequestCollector(),
            entity_mapper=PubChemEntityMapper(),
            fetch_strategies=object(),  # type: ignore[arg-type]
        )
        await borrowed_adapter.aclose()
        assert borrowed._shutdown is False

        owned_adapter = PubChemAdapter(
            logger=logger,
            rate_limiter=TokenBucketRateLimiter(
                rate=5.0, capacity=10, provider="pubchem"
            ),
            circuit_breaker=CircuitBreakerGuard(provider="pubchem"),
            thread_pool=owned,
            owns_thread_pool=True,
            error_handler=create_default_error_handler(logger=logger, metrics=None),
            request_collector=APIRequestCollector(),
            entity_mapper=PubChemEntityMapper(),
            fetch_strategies=object(),  # type: ignore[arg-type]
        )
        await owned_adapter.aclose()
        await owned_adapter.aclose()
        assert owned._shutdown is True
    finally:
        borrowed.shutdown(wait=False, cancel_futures=True)
        if not owned._shutdown:
            owned.shutdown(wait=False, cancel_futures=True)
