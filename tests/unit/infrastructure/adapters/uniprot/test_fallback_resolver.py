"""Unit tests for UniProt fallback resolver helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.uniprot.fallback_resolver import (
    iter_uniprot_fallback_records,
    resolve_uniprot_missing_ids,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def isolate_xdg_cache_home(monkeypatch):
    """Isolate fallback-cache scenario from XDG_CACHE_HOME."""
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def test_resolve_uniprot_missing_ids_filters_found_and_deduplicates() -> None:
    missing_ids = resolve_uniprot_missing_ids(
        filter_ids=["A", "B", "B", "C", "D"],
        found_ids={"A", "D"},
        fallback_mapping={"B": "query-b", "C": "query-c"},
    )

    assert missing_ids == ["B", "C"]


def test_resolve_uniprot_missing_ids_returns_empty_without_mapping() -> None:
    missing_ids = resolve_uniprot_missing_ids(
        filter_ids=["A", "B"],
        found_ids=set(),
        fallback_mapping={},
    )
    assert missing_ids == []


@pytest.mark.asyncio
async def test_iter_uniprot_fallback_records_reuses_cached_results() -> None:
    calls: list[str] = []

    async def strategy(*, query: str, limit: int) -> AsyncIterator[dict[str, str]]:
        calls.append(f"{query}:{limit}")
        if query == "match":
            yield {"accession": "P12345", "query": query}

    records = await collect_async_iterator(
        iter_uniprot_fallback_records(
            strategy=strategy,
            missing_ids=["id1", "id2", "id3"],
            fallback_mapping={"id1": "match", "id2": "match", "id3": "miss"},
            limit=None,
            already_fetched=0,
        )
    )

    assert len(records) == 2
    assert all(record["accession"] == "P12345" for record in records)
    assert calls == ["match:1", "miss:1"]


@pytest.mark.asyncio
async def test_iter_uniprot_fallback_records_respects_limit() -> None:
    calls: list[str] = []

    async def strategy(*, query: str, limit: int) -> AsyncIterator[dict[str, str]]:
        calls.append(f"{query}:{limit}")
        yield {"accession": "P99999", "query": query}

    records = await collect_async_iterator(
        iter_uniprot_fallback_records(
            strategy=strategy,
            missing_ids=["id1", "id2"],
            fallback_mapping={"id1": "first", "id2": "second"},
            limit=1,
            already_fetched=0,
        )
    )

    assert len(records) == 1
    assert records[0]["query"] == "first"
    assert calls == ["first:1"]
