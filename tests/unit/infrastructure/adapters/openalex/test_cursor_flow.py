from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.openalex.cursor_flow import OpenAlexCursorFlow


pytestmark = pytest.mark.unit


def _build_flow() -> OpenAlexCursorFlow:
    return OpenAlexCursorFlow(
        mailto="test@example.com",
        batch_size=2,
        title_search_cache_size=1,
        normalize_doi=lambda value: value.strip().lower() if value.strip() else None,
        escape_title_for_search=lambda value: value.replace(" ", "+"),
        query_executor=AsyncMock(),
        response_mapper=MagicMock(),
        logger=MagicMock(),
        runtime_errors=(RuntimeError,),
        api_key=None,
    )


@pytest.mark.asyncio
async def test_iter_query_results_paginates_and_honors_limit() -> None:
    flow = _build_flow()
    flow.query_executor.request_works_payload.side_effect = [{"page": 1}, {"page": 2}]
    flow.response_mapper.extract_results.side_effect = [
        [{"id": "W1"}, {"id": "W2"}],
        [{"id": "W3"}],
    ]
    flow.response_mapper.extract_next_cursor.side_effect = ["cursor-2", None]

    rows = await collect_async_iterator(
        flow.iter_query_results(query="biology", limit=2)
    )

    assert rows == [{"id": "W1"}, {"id": "W2"}]
    assert flow.query_executor.request_works_payload.await_count == 2


@pytest.mark.asyncio
async def test_iter_filtered_by_title_skips_blank_titles_and_logs_summary() -> None:
    flow = _build_flow()
    flow.query_executor.request_works_payload.side_effect = [
        {"results": []},
        {"results": [{"id": "W2"}]},
    ]
    flow.response_mapper.extract_results.side_effect = [[], [{"id": "W2"}]]
    flow.response_mapper.mark_lookup.side_effect = lambda record, **kwargs: {
        **record,
        **kwargs,
    }

    rows = await collect_async_iterator(
        flow.iter_filtered_by_title(["", "missing", "Found Title"], limit=None)
    )

    assert rows == [
        {
            "id": "W2",
            "lookup_method": "title",
            "original_id": "Found Title",
            "search_title": "Found Title",
        }
    ]
    assert flow.query_executor.request_works_payload.await_count == 2
    assert (
        flow.logger.info.call_args_list[-1].args[0] == "openalex_title_lookup_summary"
    )


@pytest.mark.asyncio
async def test_fetch_by_dois_logs_partial_results_and_normalizes_ids() -> None:
    flow = _build_flow()
    flow.query_executor.request_works_payload.return_value = {"results": []}
    flow.response_mapper.extract_results.return_value = [{"id": "W1"}]

    rows = await flow.fetch_by_dois([" 10.1/A ", "", "10.2/B"])

    assert rows == [{"id": "W1"}]
    flow.logger.debug.assert_called_once_with("openalex_batch_doi_request", doi_count=2)
    flow.logger.info.assert_called_once_with(
        "openalex_batch_partial_results",
        requested=2,
        found=1,
        hit_rate=50.0,
    )


@pytest.mark.asyncio
async def test_fetch_by_dois_returns_empty_when_normalization_drops_all_ids() -> None:
    flow = _build_flow()

    rows = await flow.fetch_by_dois(["", "   "])

    assert rows == []
    flow.query_executor.request_works_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_by_title_caches_results_and_evicts_oldest() -> None:
    flow = _build_flow()
    flow.query_executor.request_works_payload.side_effect = [
        {"results": [{"id": "W1"}]},
        {"results": [{"id": "W2"}]},
    ]
    flow.response_mapper.extract_results.side_effect = [[{"id": "W1"}], [{"id": "W2"}]]

    first = await flow.search_by_title("Alpha", limit=1)
    cached = await flow.search_by_title("Alpha", limit=1)
    second = await flow.search_by_title("Beta", limit=1)

    assert first == [{"id": "W1"}]
    assert cached == [{"id": "W1"}]
    assert second == [{"id": "W2"}]
    assert flow.query_executor.request_works_payload.await_count == 2
    assert ("alpha", 1) not in flow._title_search_cache
    assert ("beta", 1) in flow._title_search_cache


@pytest.mark.asyncio
async def test_search_by_title_returns_empty_and_caches_runtime_errors() -> None:
    flow = _build_flow()
    flow.query_executor.request_works_payload.side_effect = RuntimeError("down")

    first = await flow.search_by_title("Gamma", limit=2)
    second = await flow.search_by_title("Gamma", limit=2)

    assert first == []
    assert second == []
    assert flow.query_executor.request_works_payload.await_count == 1
    flow.logger.debug.assert_called_with(
        "openalex_title_search_failed",
        title="Gamma",
        error="down",
    )


@pytest.mark.asyncio
async def test_iter_filtered_by_title_breaks_immediately_when_limit_is_zero() -> None:
    flow = _build_flow()

    rows = await collect_async_iterator(
        flow.iter_filtered_by_title(["Title A"], limit=0)
    )

    assert rows == []
    flow.query_executor.request_works_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_iter_doi_batches_for_fallback_marks_lookup_and_stops_at_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _build_flow()

    async def _iter_by_dois(_self, dois: list[str]):
        for doi in dois:
            yield {"id": doi}

    monkeypatch.setattr(OpenAlexCursorFlow, "iter_by_dois", _iter_by_dois)
    flow.response_mapper.mark_lookup.side_effect = lambda record, **kwargs: {
        **record,
        **kwargs,
    }

    rows = await collect_async_iterator(
        flow.iter_doi_batches_for_fallback(
            ["10.1/A", "10.2/B", "10.3/C"],
            limit=2,
            start_count=0,
        )
    )

    assert rows == [
        {"id": "10.1/A", "lookup_method": "doi"},
        {"id": "10.2/B", "lookup_method": "doi"},
    ]
