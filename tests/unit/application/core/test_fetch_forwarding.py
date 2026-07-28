"""Focused unit coverage for fetch kwargs forwarding (T-TEST-010 / #6780)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from bioetl.application.core._fetch_forwarding import (
    build_forwarded_fetch_kwargs,
    forward_fetch_records,
)
from bioetl.domain.types import JsonDict

pytestmark = pytest.mark.unit


def test_build_forwarded_fetch_kwargs_omits_unset_filters() -> None:
    kwargs = build_forwarded_fetch_kwargs(
        entity_type="target",
        limit=10,
        query="CHEMBL",
        offset=5,
    )
    assert kwargs == {
        "entity_type": "target",
        "limit": 10,
        "query": "CHEMBL",
        "offset": 5,
    }
    assert "filter_ids" not in kwargs
    assert "filter_field" not in kwargs


def test_build_forwarded_fetch_kwargs_includes_explicit_none_filters() -> None:
    kwargs = build_forwarded_fetch_kwargs(
        entity_type="activity",
        filter_ids=None,
        filter_field=None,
    )
    assert kwargs["filter_ids"] is None
    assert kwargs["filter_field"] is None


@pytest.mark.asyncio
async def test_forward_fetch_records_yields_from_async_iterator() -> None:
    async def _fetch(**kwargs: object) -> AsyncIterator[JsonDict]:
        assert kwargs["entity_type"] == "molecule"
        assert kwargs["limit"] == 2
        yield {"id": "a"}
        yield {"id": "b"}

    rows = [
        row
        async for row in forward_fetch_records(
            _fetch,
            entity_type="molecule",
            limit=2,
        )
    ]
    assert rows == [{"id": "a"}, {"id": "b"}]
