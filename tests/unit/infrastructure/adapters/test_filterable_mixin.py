"""Unit tests for filterable mixins used by adapter stubs."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from bioetl.infrastructure.adapters.filterable_mixin import (
    DelegatingFallbackMixin,
    FetchFilteredProtocol,
    NotSupportedMultiFilterMixin,
)


class _DummyUnsupportedAdapter(NotSupportedMultiFilterMixin):
    provider_name = "dummy-provider"


class _DummyDelegatingAdapter(DelegatingFallbackMixin):
    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        await asyncio.sleep(0)
        del entity_type, filter_field, limit
        for item in filter_ids:
            yield {"id": item}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multi_filter_stub_raises_with_provider_name() -> None:
    await asyncio.sleep(0)
    adapter = _DummyUnsupportedAdapter()

    with pytest.raises(NotImplementedError, match="dummy-provider"):
        async for _ in adapter.fetch_multi_filtered(
            entity_type="publication",
            filters={"doi": ["10.1000/test"]},
            limit=10,
        ):
            continue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_mixin_delegates_to_fetch_filtered() -> None:
    await asyncio.sleep(0)
    adapter = _DummyDelegatingAdapter()

    result: list[dict[str, str]] = []
    async for item in adapter.fetch_filtered_with_fallback(
        entity_type="publication",
        filter_ids=["A", "B"],
        filter_field="doi",
        fallback_mapping={"A": "Title A"},
        limit=5,
    ):
        result.append(item)

    assert result == [{"id": "A"}, {"id": "B"}]


@pytest.mark.unit
def test_has_fetch_filtered_protocol_stub_callable() -> None:
    assert (
        FetchFilteredProtocol.fetch_filtered(
            object(),
            entity_type="publication",
            filter_ids=["1"],
            filter_field="doi",
            limit=1,
        )
        is None
    )
