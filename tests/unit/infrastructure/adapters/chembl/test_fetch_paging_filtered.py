from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.chembl._fetch_paging_filtered import (
    _ChemblFetchPagingFilteredMixin,
)


pytestmark = pytest.mark.unit


class _PagingFilteredAdapter(_ChemblFetchPagingFilteredMixin):
    CHEMBL_ADAPTER_ERRORS = (RuntimeError,)

    def __init__(self) -> None:
        self._logger = MagicMock()
        self._adapter_metrics = MagicMock()
        self._mapper = SimpleNamespace(
            get_resource_url=lambda entity_type: f"https://example.test/{entity_type}"
        )
        self._page_size = 2
        self.fetch_calls: list[dict[str, object]] = []
        self.page_responses: list[tuple[list[dict[str, object]], bool]] = []

    def _build_params(self, offset: int, entity_type: str) -> dict[str, object]:
        return {"offset": offset, "limit": self._page_size, "entity_type": entity_type}

    def _build_filter_params(
        self,
        entity_type: str,
        filter_field: str,
        id_batch: list[str],
    ) -> dict[str, str]:
        del entity_type
        return {f"{filter_field}__in": ",".join(id_batch)}

    def _get_api_pk_field(self, entity_type: str) -> str:
        del entity_type
        return "chembl_id"

    def _get_api_dedup_fields(self, entity_type: str) -> tuple[str, ...]:
        del entity_type
        return ("chembl_id",)

    def _normalize_filter_field(self, entity_type: str, filter_field: str) -> str:
        del entity_type
        return filter_field

    def _compute_composite_key(
        self,
        record: dict[str, object],
        composite_fields: tuple[str, ...],
    ) -> str:
        return "|".join(str(record.get(field, "")) for field in composite_fields)

    async def _fetch_page(
        self,
        url: str,
        params: dict[str, object],
        entity_type: str,
    ) -> tuple[list[dict[str, object]], bool]:
        self.fetch_calls.append({"url": url, "params": params.copy(), "entity_type": entity_type})
        return self.page_responses.pop(0)


def test_yield_deduplicated_filters_duplicate_records() -> None:
    adapter = _PagingFilteredAdapter()
    records = list(
        adapter._yield_deduplicated(
            [{"chembl_id": "1"}, {"chembl_id": "1"}, {"chembl_id": "2"}],
            seen_ids=set(),
            pk_field="chembl_id",
            entity_type="activity",
            filter_field="molecule",
        )
    )

    assert records == [{"chembl_id": "1"}, {"chembl_id": "2"}]


@pytest.mark.asyncio
async def test_fetch_with_filter_skips_explicit_pagination_for_small_pk_batches() -> None:
    adapter = _PagingFilteredAdapter()
    adapter.page_responses = [([{"chembl_id": "1"}], False)]

    rows = await collect_async_iterator(
        adapter._fetch_with_filter(
            entity_type="activity",
            id_batch=["CHEMBL1"],
            filter_field="chembl_id",
            limit=None,
        )
    )

    assert rows == [{"chembl_id": "1"}]
    assert adapter.fetch_calls[0]["params"] == {
        "entity_type": "activity",
        "chembl_id__in": "CHEMBL1",
    }


@pytest.mark.asyncio
async def test_fetch_with_filter_continues_when_more_pages_are_available() -> None:
    adapter = _PagingFilteredAdapter()
    adapter.page_responses = [([{"chembl_id": "1"}], True)]

    async def _paginate(*args, **kwargs):
        del args, kwargs
        yield {"chembl_id": "2"}

    adapter._paginate_filter_results = _paginate  # type: ignore[method-assign]

    rows = await collect_async_iterator(
        adapter._fetch_with_filter(
            entity_type="activity",
            id_batch=["CHEMBL1", "CHEMBL2"],
            filter_field="molecule",
            limit=None,
        )
    )

    assert rows == [{"chembl_id": "1"}, {"chembl_id": "2"}]


@pytest.mark.asyncio
async def test_paginate_filter_results_logs_and_stops_on_adapter_error() -> None:
    adapter = _PagingFilteredAdapter()

    async def _boom(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("stop")

    adapter._fetch_page = _boom  # type: ignore[method-assign]

    rows = await collect_async_iterator(
        adapter._paginate_filter_results(
            "https://example.test/activity",
            ["CHEMBL1"],
            "molecule",
            "activity",
            "chembl_id",
            set(),
            0,
            None,
        )
    )

    assert rows == []
    adapter._logger.warning.assert_called_once_with(
        "chembl_pagination_interrupted",
        entity_type="activity",
        offset=0,
        records_yielded=0,
    )
