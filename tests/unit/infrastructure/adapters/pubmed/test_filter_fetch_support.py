"""Unit coverage for PubMed filter/fetch support helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.pubmed import _filter_fetch_support as support


pytestmark = pytest.mark.unit


class _Logger:
    def __init__(self) -> None:
        self.warnings: list[dict[str, object]] = []
        self.infos: list[dict[str, object]] = []

    def warning(self, event: str, **context: object) -> None:
        self.warnings.append({"event": event, **context})

    def info(self, event: str, **context: object) -> None:
        self.infos.append({"event": event, **context})


async def _iter_records(records: list[BronzeRecord]) -> AsyncIterator[BronzeRecord]:
    for record in records:
        yield record


class _FallbackDecorator:
    def __init__(self) -> None:
        self.primary_empty_records: list[BronzeRecord] = []
        self.calls: list[dict[str, object]] = []

    async def execute(
        self,
        *,
        filter_ids: list[str],
        fallback_mapping: dict[str, str],
        primary_record_fetcher: Callable[
            [list[str], int | None],
            AsyncIterator[BronzeRecord],
        ],
        limit: int | None,
        filter_field: str,
    ) -> AsyncIterator[BronzeRecord]:
        self.calls.append(
            {
                "filter_ids": filter_ids,
                "fallback_mapping": fallback_mapping,
                "limit": limit,
                "filter_field": filter_field,
            }
        )
        self.primary_empty_records = [
            record async for record in primary_record_fetcher([], limit)
        ]
        async for record in primary_record_fetcher(filter_ids, limit):
            yield record
        for fallback_id, title in fallback_mapping.items():
            yield {"pmid": fallback_id, "title": title, "_lookup_method": "title"}


class _PubMedHost:
    def __init__(self) -> None:
        self._logger = _Logger()
        self.logger = self._logger
        self._fallback_decorator = _FallbackDecorator()
        self.yield_calls: list[tuple[list[str], int | None]] = []
        self.filter_calls: list[dict[str, object]] = []
        self.filter_id_calls: list[dict[str, object]] = []
        self.validated_entities: list[str] = []
        self.pmids_for_query: list[str] = ["1", "2", "3"]
        self.search_calls: list[tuple[str, int]] = []

    def _yield_articles_from_pmids(
        self,
        pmids: list[str],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        self.yield_calls.append((pmids, limit))
        selected = pmids if limit is None else pmids[:limit]
        return _iter_records([{"pmid": pmid} for pmid in selected])

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        self.filter_calls.append(
            {
                "entity_type": entity_type,
                "filter_ids": filter_ids,
                "filter_field": filter_field,
                "limit": limit,
            }
        )
        return _iter_records([{"pmid": pmid} for pmid in filter_ids])

    def _fetch_from_filter_ids(
        self,
        *,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        self.filter_id_calls.append(
            {
                "entity_type": entity_type,
                "filter_ids": filter_ids,
                "filter_field": filter_field,
                "limit": limit,
            }
        )
        return _iter_records([{"pmid": pmid} for pmid in filter_ids])

    @staticmethod
    def _validate_publication_entity(entity_type: str) -> None:
        support.validate_publication_entity(entity_type)

    def _resolve_resume_offset(
        self,
        *,
        limit: int | None,
        offset: int | None,
    ) -> int | None:
        return support.resolve_resume_offset(self, limit=limit, offset=offset)

    async def _resolve_pmids_for_fetch(
        self,
        *,
        query: str | None,
        limit: int | None,
    ) -> list[str]:
        return await support.resolve_pmids_for_fetch(self, query=query, limit=limit)

    def _apply_resume_offset(
        self,
        *,
        pmids: list[str],
        resume_offset: int,
    ) -> list[str]:
        return support.apply_resume_offset(
            self,
            pmids=pmids,
            resume_offset=resume_offset,
        )

    async def _get_pmids(self, search_term: str, max_count: int) -> list[str]:
        self.search_calls.append((search_term, max_count))
        return self.pmids_for_query[:max_count]


async def _collect(iterator: AsyncIterator[BronzeRecord]) -> list[BronzeRecord]:
    return [record async for record in iterator]


async def _collect_awaitable(
    iterator: Awaitable[AsyncIterator[BronzeRecord]],
) -> list[BronzeRecord]:
    return [record async for record in await iterator]


@pytest.mark.asyncio
async def test_pubmed_filter_fetch_support_filtered_and_fallback_paths() -> None:
    host = _PubMedHost()

    assert await _collect(support.empty_async_iterator()) == []
    with pytest.raises(ValueError, match="only supports 'publication'"):
        await _collect(
            support.fetch_filtered_records(
                host,
                entity_type="gene",
                filter_ids=["1"],
                filter_field="pmid",
                limit=1,
            )
        )

    records = await _collect(
        support.fetch_filtered_records(
            host,
            entity_type="publication",
            filter_ids=["1", "2"],
            filter_field="doi",
            limit=1,
        )
    )
    assert records == [
        {"pmid": "1", "_lookup_method": "pmid"},
    ]
    assert host.yield_calls[-1] == (["1", "2"], 1)
    assert host._logger.warnings[-1]["event"] == "unsupported_filter_field"

    with pytest.raises(ValueError, match="only supports 'publication'"):
        await _collect(
            support.fetch_filtered_with_fallback_records(
                host,
                entity_type="gene",
                filter_ids=["1"],
                filter_field="pmid",
                fallback_mapping={},
                limit=1,
            )
        )
    fallback_records = await _collect(
        support.fetch_filtered_with_fallback_records(
            host,
            entity_type="publication",
            filter_ids=["3"],
            filter_field="pmid",
            fallback_mapping={"fallback-1": "Fallback title"},
            limit=None,
        )
    )
    assert fallback_records == [
        {"pmid": "3"},
        {"pmid": "fallback-1", "title": "Fallback title", "_lookup_method": "title"},
    ]
    assert host._fallback_decorator.primary_empty_records == []
    assert host.filter_calls[-1]["filter_ids"] == ["3"]


@pytest.mark.asyncio
async def test_pubmed_filter_fetch_support_query_resume_and_filter_id_paths() -> None:
    host = _PubMedHost()

    filtered = await _collect(
        support.fetch_records(
            host,
            entity_type="publication",
            limit=2,
            query=None,
            filter_ids=["10", "11"],
            filter_field=None,
            offset=None,
        )
    )
    assert filtered == [{"pmid": "10"}, {"pmid": "11"}]
    assert host.filter_id_calls[-1]["filter_field"] is None

    with pytest.raises(ValueError, match="only supports 'publication'"):
        await _collect(
            support.fetch_records(
                host,
                entity_type="gene",
                limit=1,
                query=None,
                filter_ids=None,
                filter_field=None,
                offset=None,
            )
        )

    assert (
        await _collect(
            support.fetch_records(
                host,
                entity_type="publication",
                limit=2,
                query="custom",
                filter_ids=None,
                filter_field=None,
                offset=2,
            )
        )
        == []
    )
    assert host._logger.infos[-1]["event"] == "pubmed_resume_offset_reached_limit"

    host.pmids_for_query = []
    assert (
        await _collect(
            support.fetch_records(
                host,
                entity_type="publication",
                limit=2,
                query="custom",
                filter_ids=None,
                filter_field=None,
                offset=0,
            )
        )
        == []
    )

    host.pmids_for_query = ["1", "2", "3", "4"]
    records = await _collect(
        support.fetch_records(
            host,
            entity_type="publication",
            limit=3,
            query=None,
            filter_ids=None,
            filter_field=None,
            offset=1,
        )
    )
    assert records == [{"pmid": "2"}, {"pmid": "3"}]
    assert host.search_calls[-1] == ("pharmacogenomics[Title/Abstract]", 3)
    assert host.yield_calls[-1] == (["2", "3"], 2)
    assert host._logger.infos[-1]["event"] == "pubmed_resume_skip_processed"

    assert support.resolve_resume_offset(host, limit=None, offset=-5) == 0
    assert await support.resolve_pmids_for_fetch(host, query="term", limit=None) == [
        "1",
        "2",
        "3",
        "4",
    ]
    assert support.apply_resume_offset(host, pmids=["1", "2"], resume_offset=0) == [
        "1",
        "2",
    ]
