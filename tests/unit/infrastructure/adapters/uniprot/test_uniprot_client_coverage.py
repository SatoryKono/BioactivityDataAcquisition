"""Additional coverage tests for UniProtAdapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import CircuitBreakerState, HealthStatus
from bioetl.infrastructure.adapters.common.deduplication import (
    deduplicate_preserving_order,
)
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


pytestmark = pytest.mark.unit

async def _drain_async_iter(async_iter: AsyncIterator[object]) -> None:
    """Consume an async iterator until completion."""
    async for _ in async_iter:
        continue


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    client.circuit_breaker.get_failure_count.return_value = 0
    return client


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client, mock_logger):
    return UniProtAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        **build_http_adapter_runtime_kwargs(
            "uniprot",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


@pytest.mark.asyncio
async def test_probe_health_healthy(adapter, mock_http_client):
    """Test health probe returns HEALTHY."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"primaryAccession": "P0CG48"}]}
    mock_http_client.get_once.return_value = mock_response

    status = await adapter._probe_health()
    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_client_coverage__health_degraded__874078aa(adapter, mock_http_client):
    """Test health probe returns HEALTHY on empty search (status 200)."""

    mock_response = MagicMock()

    mock_response.status_code = 200

    mock_response.json.return_value = {"results": []}

    mock_http_client.get_once.return_value = mock_response

    status = await adapter._probe_health()

    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_probe_health_error(adapter, mock_http_client):
    """Test health probe raises exception on failure."""

    mock_http_client.get_once.side_effect = Exception("API Error")

    with pytest.raises(Exception):
        await adapter._probe_health()


@pytest.mark.asyncio
async def test_fetch_with_filter_batching(adapter, mock_http_client):
    """Test fetch_filtered handles batching."""

    # Mock http_client.get to return fake records

    mock_response = MagicMock()

    mock_response.status_code = 200

    mock_response.json.return_value = {"results": [{"primaryAccession": "P1"}]}

    mock_http_client.get.return_value = mock_response

    ids = ["P1"] * 120  # 120 IDs, batch size 100 -> 2 batches

    records = []

    async for record in adapter.fetch_filtered("protein", ids, "accession"):
        records.append(record)

    # Should be called 2 times (once per batch)

    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_routes_to_fetch_filtered_when_ids_passed(adapter):
    async def fake_filtered(**kwargs):
        assert kwargs["entity_type"] == "protein"
        assert kwargs["filter_ids"] == ["P1"]
        assert kwargs["filter_field"] == "accession"
        yield {"accession": "P1"}

    adapter.fetch_filtered = fake_filtered  # type: ignore[assignment]
    records = []
    async for record in adapter.fetch(
        "protein", filter_ids=["P1"], filter_field="accession", limit=1
    ):
        records.append(record)
    assert records == [{"accession": "P1"}]


@pytest.mark.asyncio
async def test_fetch_filtered_unsupported_entity_raises(adapter):
    with pytest.raises(ValueError, match="Unsupported entity type"):
        await _drain_async_iter(adapter.fetch_filtered("unknown", ["P1"], "accession"))


@pytest.mark.asyncio
async def test_fetch_filtered_non_protein_uses_individual_strategy(adapter):
    async def feature_strategy(query=None, limit=None):
        yield {"feature_id": query, "limit": limit}

    adapter._fetch_strategies["feature"] = feature_strategy
    records = []
    async for record in adapter.fetch_filtered("feature", ["F1", "F2"], "accession"):
        records.append(record)

    assert [r["feature_id"] for r in records] == ["F1", "F2"]


def test_common_deduplicate_preserving_order_supports_uniprot_filter_ids() -> None:
    assert deduplicate_preserving_order(["P2", "P1", "P2", "P3", "P1"]) == [
        "P2",
        "P1",
        "P3",
    ]


@pytest.mark.asyncio
async def test_fetch_non_protein_filtered_limit_breaks(adapter):
    async def strategy(query=None, limit=None):
        yield {"query": query, "limit": limit, "idx": 1}
        yield {"query": query, "limit": limit, "idx": 2}

    records = []
    async for record in adapter._fetch_non_protein_filtered(strategy, ["A", "B"], 1):
        records.append(record)
    assert records == [{"query": "A", "limit": 1, "idx": 1}]


@pytest.mark.asyncio
async def test_fetch_proteins_batched_limit_paths(adapter):
    async def strategy(query=None, limit=None):
        yield {"query": query, "limit": limit, "idx": 1}
        yield {"query": query, "limit": limit, "idx": 2}

    limited = []
    async for record in adapter._fetch_proteins_batched(
        strategy, ["P1", "P2"], "accession", 1
    ):
        limited.append(record)
    assert len(limited) == 1

    no_rows = []
    async for record in adapter._fetch_proteins_batched(
        strategy, ["P1", "P2"], "accession", -1
    ):
        no_rows.append(record)
    assert no_rows == []


@pytest.mark.asyncio
async def test_fetch_multi_filtered_paths(adapter):
    async def protein_strategy(query=None, limit=None):
        yield {"query": query, "limit": limit}

    adapter._fetch_strategies["protein"] = protein_strategy

    empty = []
    async for record in adapter.fetch_multi_filtered("protein", {}):
        empty.append(record)
    assert empty == []

    with pytest.raises(ValueError, match="Unsupported entity type"):
        await _drain_async_iter(adapter.fetch_multi_filtered("unknown", {"x": ["1"]}))

    records = []
    async for record in adapter.fetch_multi_filtered(
        "protein",
        {"accession": ["P1", "P2"], "organism_id": ["9606"]},
        limit=1,
    ):
        records.append(record)
    assert len(records) == 1
    assert "AND" in records[0]["query"]

    none_records = []
    async for record in adapter.fetch_multi_filtered("protein", {"accession": []}):
        none_records.append(record)
    assert none_records == []


@pytest.mark.asyncio
async def test_do_fallback_search_and_should_do_fallback(adapter):
    assert adapter._should_do_fallback(["P1"], {"P1"}, {}) == []
    assert adapter._should_do_fallback(["P1", "P2"], {"P1"}, {"P2": "GENE2"}) == ["P2"]
    assert adapter._should_do_fallback(
        ["P1", "P2", "P2", "P3"],
        {"P1"},
        {"P2": "GENE2"},
    ) == ["P2"]

    no_strategy_records = []
    async for record in adapter._do_fallback_search(
        "missing",
        ["P2"],
        {"P2": "GENE2"},
        limit=1,
        already_fetched=0,
    ):
        no_strategy_records.append(record)
    assert no_strategy_records == []

    async def protein_strategy(query=None, limit=None):
        yield {"accession": "P2", "query": query, "limit": limit}

    adapter._fetch_strategies["protein"] = protein_strategy
    records = []
    async for record in adapter._do_fallback_search(
        "protein",
        ["P2", "P3"],
        {"P2": "GENE2"},
        limit=1,
        already_fetched=0,
    ):
        records.append(record)
    assert len(records) == 1
    assert records[0]["query"] == "GENE2"

    mixed_records = []
    async for record in adapter._do_fallback_search(
        "protein",
        ["P2", "P3"],
        {"P2": "GENE2"},
        limit=10,
        already_fetched=0,
    ):
        mixed_records.append(record)
    assert mixed_records == [{"accession": "P2", "query": "GENE2", "limit": 1}]

    prelimited = []
    async for record in adapter._do_fallback_search(
        "protein",
        ["P2"],
        {"P2": "GENE2"},
        limit=-1,
        already_fetched=0,
    ):
        prelimited.append(record)
    assert prelimited == []


@pytest.mark.asyncio
async def test_do_fallback_search_reuses_query_cache(adapter):
    call_queries: list[str | None] = []

    async def protein_strategy(query=None, limit=None):
        call_queries.append(query)
        yield {"accession": "PX", "query": query, "limit": limit}

    adapter._fetch_strategies["protein"] = protein_strategy

    records = []
    async for record in adapter._do_fallback_search(
        "protein",
        ["P1", "P2"],
        {"P1": "GENE_X", "P2": "GENE_X"},
        limit=10,
        already_fetched=0,
    ):
        records.append(record)

    # Two IDs should still yield two records, but only one upstream query.
    assert len(records) == 2
    assert call_queries == ["GENE_X"]


@pytest.mark.asyncio
async def test_do_primary_fetch_yields_record_and_accession(adapter):
    async def fake_fetch_filtered(*args, **kwargs):
        yield {"accession": "P1"}

    adapter.fetch_filtered = fake_fetch_filtered  # type: ignore[assignment]

    results = []
    async for item in adapter._do_primary_fetch("protein", ["P1"], "accession", 1):
        results.append(item)

    assert results == [({"accession": "P1"}, "P1")]


@pytest.mark.asyncio
async def test_fetch_filtered_with_fallback_branches(adapter):
    empty_records = []
    async for record in adapter.fetch_filtered_with_fallback(
        "protein", [], "accession", {"P1": "GENE1"}
    ):
        empty_records.append(record)
    assert empty_records == []

    async def primary_all(*args, **kwargs):
        yield {"accession": "P1"}, "P1"

    async def fallback_unused(*args, **kwargs):
        for record in ():
            yield record

    adapter._do_primary_fetch = primary_all  # type: ignore[assignment]
    adapter._do_fallback_search = fallback_unused  # type: ignore[assignment]

    records = []
    async for record in adapter.fetch_filtered_with_fallback(
        "protein", ["P1"], "accession", {"P1": "GENE1"}
    ):
        records.append(record)
    assert records == [{"accession": "P1"}]

    async def primary_partial(*args, **kwargs):
        yield {"accession": "P1"}, "P1"

    async def fallback_used(*args, **kwargs):
        yield {"accession": "P2"}

    adapter._do_primary_fetch = primary_partial  # type: ignore[assignment]
    adapter._do_fallback_search = fallback_used  # type: ignore[assignment]

    fallback_records = []
    async for record in adapter.fetch_filtered_with_fallback(
        "protein", ["P1", "P2"], "accession", {"P2": "GENE2"}
    ):
        fallback_records.append(record)
    assert fallback_records == [{"accession": "P1"}, {"accession": "P2"}]

    async def primary_many(*args, **kwargs):
        yield {"accession": "P1"}, "P1"
        yield {"accession": "P2"}, "P2"

    adapter._do_primary_fetch = primary_many  # type: ignore[assignment]
    adapter._do_fallback_search = fallback_unused  # type: ignore[assignment]
    early_stop = []
    async for record in adapter.fetch_filtered_with_fallback(
        "protein", ["P1", "P2"], "accession", {"P1": "GENE1"}, limit=1
    ):
        early_stop.append(record)
    assert early_stop == [{"accession": "P1"}]


def test_build_params_parse_response_and_repr(adapter):
    params = adapter._build_protein_fetch_params(
        "q", 500, fetched=0, limit=10, cursor="c1"
    )
    assert params["cursor"] == "c1"
    assert params["size"] == 10

    bad_response = MagicMock()
    bad_response.status_code = 500
    assert adapter._parse_response(bad_response) == ([], None)

    assert "without API key" in repr(adapter)
    logger = adapter.logger
    with_key = UniProtAdapter(
        http_client=adapter._http_client,
        logger=logger,
        api_key="secret",
        **build_http_adapter_runtime_kwargs(
            "uniprot",
            logger=logger,
            include_fallback_service=True,
        ),
    )
    assert "with API key" in repr(with_key)


def test_handle_fetch_error_paths(adapter):
    adapter._handle_fetch_error("protein", "q", cursor="c1", error=None)
    adapter.logger.error.assert_called()

    logger = MagicMock()
    strict = UniProtAdapter(
        http_client=adapter._http_client,
        logger=logger,
        strict_error_handling=True,
        **build_http_adapter_runtime_kwargs(
            "uniprot",
            logger=logger,
            include_fallback_service=True,
        ),
    )
    wrapped = RuntimeError("wrapped")
    strict._error_handler.wrap_error = MagicMock(return_value=wrapped)  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="wrapped"):
        strict._handle_fetch_error("protein", "q", error=RuntimeError("boom"))


@pytest.mark.asyncio
async def test_features_and_sequences_error_paths(adapter, mock_http_client):
    non_200 = MagicMock(status_code=404)
    non_200.json.return_value = {}
    non_200.text = ""
    mock_http_client.get.return_value = non_200

    assert await adapter._get_features_json("P1") == []
    assert await adapter._get_sequence_fasta("P1") is None

    mock_http_client.get.side_effect = RuntimeError("network")
    assert await adapter._get_features_json("P1") == []
    assert await adapter._get_sequence_fasta("P1") is None

    with pytest.raises(ValueError, match="Query is required for feature search"):
        await _drain_async_iter(adapter._fetch_features(None, limit=None))

    with pytest.raises(ValueError, match="Query is required for sequence fetch"):
        await _drain_async_iter(adapter._fetch_sequences(None, limit=None))


@pytest.mark.asyncio
async def test_fetch_sequences_limit_and_probe_health_degraded(
    adapter, mock_http_client
):
    async def parsed_sequences(_query):
        yield {"id": "S1"}
        yield {"id": "S2"}

    adapter._get_parsed_sequences = parsed_sequences  # type: ignore[assignment]

    records = []
    async for seq in adapter._fetch_sequences("P1", limit=1):
        records.append(seq)
    assert records == [{"id": "S1"}]

    degraded_response = MagicMock()
    degraded_response.status_code = 503
    degraded_response.json.return_value = {}
    mock_http_client.get_once.return_value = degraded_response
    status = await adapter._probe_health()
    assert status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_fetch_features_stops_on_limit(adapter):
    adapter._get_features_json = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            {"type": "CHAIN", "location": {"start": 1}, "description": "first"},
            {"type": "DOMAIN", "location": {"start": 2}, "description": "second"},
        ]
    )

    records = []
    async for record in adapter._fetch_features("P1", limit=1):
        records.append(record)

    assert len(records) == 1
    assert records[0]["type"] == "CHAIN"


@pytest.mark.asyncio
async def test_fetch_filtered_empty_ids_returns_nothing(adapter):
    records = []
    async for record in adapter.fetch_filtered("protein", [], "accession"):
        records.append(record)
    assert records == []
