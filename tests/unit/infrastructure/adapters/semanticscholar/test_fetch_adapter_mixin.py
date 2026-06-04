from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.semanticscholar.fetch_adapter_mixin import (
    SemanticScholarFetchAdapterMixin,
)


pytestmark = pytest.mark.unit


class _FallbackDecorator:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        yield {"id": "fallback"}


class _SemanticScholarAdapter(SemanticScholarFetchAdapterMixin):
    def __init__(self) -> None:
        self._logger = MagicMock()
        self.batch_size = 2
        self._fallback_decorator = _FallbackDecorator()
        self._validate_entity_type = MagicMock()
        self._paginate_search = MagicMock()
        self._normalize_doi = lambda value: value.strip().lower()


@pytest.mark.asyncio
async def test_fetch_delegates_to_filtered_path_when_filter_ids_are_present() -> None:
    adapter = _SemanticScholarAdapter()

    async def _fake_filtered(**kwargs):
        assert kwargs["entity_type"] == "publication"
        assert kwargs["filter_ids"] == ["10.1/A"]
        yield {"id": "filtered"}

    adapter._fetch_from_filter_ids = _fake_filtered  # type: ignore[method-assign]

    rows = await collect_async_iterator(
        adapter.fetch(
            entity_type="publication",
            filter_ids=["10.1/A"],
            filter_field="doi",
        )
    )

    assert rows == [{"id": "filtered"}]
    adapter._validate_entity_type.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_without_filters_validates_entity_type_and_uses_search() -> None:
    adapter = _SemanticScholarAdapter()

    async def _search(*, query: str | None, limit: int | None):
        assert query == "biology"
        assert limit == 1
        yield {"id": "search"}

    adapter._paginate_search = _search  # type: ignore[method-assign]

    rows = await collect_async_iterator(
        adapter.fetch(entity_type="publication", query="biology", limit=1)
    )

    assert rows == [{"id": "search"}]
    adapter._validate_entity_type.assert_called_once_with("publication")


@pytest.mark.asyncio
async def test_fetch_filtered_warns_on_non_doi_and_honors_limit() -> None:
    adapter = _SemanticScholarAdapter()

    async def _fetch_by_dois(batch: list[str]):
        for doi in batch:
            yield {"doi": doi}

    adapter._fetch_by_dois = _fetch_by_dois  # type: ignore[method-assign]

    rows = await collect_async_iterator(
        adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["a", "b", "c"],
            filter_field="pmid",
            limit=2,
        )
    )

    assert rows == [
        {"doi": "a", "_lookup_method": "doi"},
        {"doi": "b", "_lookup_method": "doi"},
    ]
    adapter._logger.warning.assert_called_once_with(
        "unsupported_filter_field",
        field="pmid",
        expected="doi",
    )


@pytest.mark.asyncio
async def test_batch_doi_phase_skips_nulls_and_stops_at_limit() -> None:
    adapter = _SemanticScholarAdapter()
    adapter._fetch_batch_with_nulls = AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            [{"paperId": "A"}, None],
            [{"paperId": "C"}],
        ]
    )
    resolved: set[str] = set()

    rows = await collect_async_iterator(
        adapter._batch_doi_phase(
            ["10.1/A", "10.2/B", "10.3/C"],
            resolved,
            limit=2,
            start_count=0,
        )
    )

    assert rows == [
        {"paperId": "A", "_lookup_method": "doi", "_resolved_doi": "10.1/A"},
        {"paperId": "C", "_lookup_method": "doi", "_resolved_doi": "10.3/C"},
    ]
    assert resolved == {"10.1/a", "10.3/c"}


@pytest.mark.asyncio
async def test_fetch_filtered_with_fallback_passes_primary_fetcher_and_extractor() -> None:
    adapter = _SemanticScholarAdapter()

    async def _primary_batch(valid_dois, resolved_dois, limit, start_count):
        del resolved_dois, limit, start_count
        for doi in valid_dois:
            yield {"_resolved_doi": doi, "paperId": doi}

    adapter._batch_doi_phase = _primary_batch  # type: ignore[method-assign]

    rows = await collect_async_iterator(
        adapter.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=["10.1/A"],
            filter_field="doi",
            fallback_mapping={"10.1/A": "Title"},
            limit=1,
        )
    )

    assert rows == [{"id": "fallback"}]
    call = adapter._fallback_decorator.calls[0]
    primary_rows = await collect_async_iterator(call["primary_record_fetcher"](["10.1/A"], 1))
    assert primary_rows == [{"_resolved_doi": "10.1/A", "paperId": "10.1/A"}]
    extracted = call["extract_record_id"]({"_resolved_doi": " 10.1/A "})
    assert extracted == "10.1/a"


@pytest.mark.asyncio
async def test_fetch_adapter_mixin__fetch_multi_filtered__raises_not_implemented() -> None:
    adapter = _SemanticScholarAdapter()
    with pytest.raises(NotImplementedError):
        await anext(adapter.fetch_multi_filtered("publication", {"doi": ["10.1/A"]}))
