"""Classification upstreams must fetch and paginate instead of succeeding empty."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.chembl import ChemblAdapter

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("entity", "collection", "primary_key"),
    [
        ("protein_class", "protein_classifications", "protein_class_id"),
        ("target_component", "target_components", "component_id"),
    ],
)
@pytest.mark.parametrize("limit", [None, 1, 3, 0])
async def test_classification_fetches_pages(entity, collection, primary_key, limit):
    records = [{primary_key: value} for value in (1, 2, 3)]
    calls = []

    async def get(url, *, params):
        calls.append(dict(params))
        start, size = params["offset"], params["limit"]
        page = records[start : start + size]
        return httpx.Response(
            200,
            json={
                collection: page,
                "page_meta": {"next": "/next" if start + size < 3 else None},
            },
        )

    client = MagicMock()
    client.get = AsyncMock(side_effect=get)
    client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    client.circuit_breaker.get_failure_count.return_value = 0
    adapter = ChemblAdapter(
        http_client=client,
        logger=MagicMock(),
        adapter_config=AdapterConfig(page_size=2),
    )
    result = [row async for row in adapter.fetch(entity, limit=limit)]
    assert result == records[:limit]
    assert [call["offset"] for call in calls] == (
        [] if limit == 0 else [0] if limit == 1 else [0, 2]
    )
