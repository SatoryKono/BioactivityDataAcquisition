from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.async_utils import collect_async_iterator

import bioetl.infrastructure.adapters.common.fallback_fetch_service as fallback_service
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    DefaultFallbackExecution,
    FallbackFetchOrchestrator,
    FallbackFetchRequest,
)

pytestmark = pytest.mark.unit


def _normalize_strip_lower(value: str) -> str:
    return value.strip().lower()


def _normalize_identity(value: str) -> str:
    return value


def _extract_record_id(record: dict[str, object]) -> str:
    return str(record.get("id", ""))


async def _empty_records(
    _ids: list[str],
    _limit: int | None,
) -> AsyncIterator[dict[str, object]]:
    if False:
        yield {}


@pytest.mark.asyncio
async def test_execute_splits_and_trims_primary_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orchestrator = FallbackFetchOrchestrator()
    seen: dict[str, Any] = {}
    primary_call: dict[str, Any] = {}

    async def fake_policy(
        *,
        primary_records: AsyncIterator[dict[str, object]],
        primary_ids: list[str],
        title_only_entries: list[str],
        fallback_mapping: dict[str, str],
        normalize_id,
        extract_record_id,
        fallback_handler,
        limit: int | None = None,
        primary_lookup_method: str | None = None,
        phase1_summary_logger=None,
    ) -> AsyncIterator[dict[str, object]]:
        seen["primary_ids"] = primary_ids
        seen["title_only_entries"] = title_only_entries
        seen["fallback_mapping"] = fallback_mapping
        seen["limit"] = limit
        seen["primary_lookup_method"] = primary_lookup_method
        seen["normalize_result"] = normalize_id("  ABC  ")
        seen["phase1_summary_logger"] = phase1_summary_logger
        seen["fallback_handler"] = fallback_handler
        seen["extract_result"] = extract_record_id({"id": "rec-1"})

        async for record in primary_records:
            yield record
        yield {"id": "from-policy"}

    monkeypatch.setattr(fallback_service, "run_fetch_with_fallback_policy", fake_policy)

    async def primary_fetcher(
        primary_ids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, object]]:
        primary_call["primary_ids"] = list(primary_ids)
        primary_call["limit"] = limit
        for primary_id in primary_ids:
            yield {"id": f"primary:{primary_id}"}

    request = FallbackFetchRequest(
        filter_ids=["10.1/a", "", "__title_only_0__", "10.2/b"],
        fallback_mapping={"10.1/a": "Title A", "__title_only_0__": "Title Only"},
        primary_record_fetcher=primary_fetcher,
        normalize_id=_normalize_strip_lower,
        extract_record_id=_extract_record_id,
        fallback_handler=None,
        limit=1,
        primary_lookup_method="doi",
        trim_primary_ids_to_limit=True,
    )

    results = await collect_async_iterator(orchestrator.execute(request))

    assert [str(item["id"]) for item in results] == ["primary:10.1/a", "from-policy"]
    assert primary_call == {"primary_ids": ["10.1/a"], "limit": 1}
    assert seen["primary_ids"] == ["10.1/a"]
    assert seen["title_only_entries"] == ["", "__title_only_0__"]
    assert seen["fallback_mapping"] == {
        "10.1/a": "Title A",
        "__title_only_0__": "Title Only",
    }
    assert seen["limit"] == 1
    assert seen["primary_lookup_method"] == "doi"
    assert seen["normalize_result"] == "abc"
    assert seen["phase1_summary_logger"] is None
    assert seen["fallback_handler"] is None
    assert seen["extract_result"] == "rec-1"


@pytest.mark.asyncio
async def test_execute_without_trim_keeps_all_primary_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orchestrator = FallbackFetchOrchestrator()
    seen_primary_ids: list[str] = []

    async def fake_policy(
        *,
        primary_records: AsyncIterator[dict[str, object]],
        primary_ids: list[str],
        title_only_entries: list[str],
        fallback_mapping: dict[str, str],
        normalize_id,
        extract_record_id,
        fallback_handler,
        limit: int | None = None,
        primary_lookup_method: str | None = None,
        phase1_summary_logger=None,
    ) -> AsyncIterator[dict[str, object]]:
        del (
            title_only_entries,
            fallback_mapping,
            normalize_id,
            extract_record_id,
            fallback_handler,
            limit,
            primary_lookup_method,
            phase1_summary_logger,
        )
        seen_primary_ids.extend(primary_ids)
        async for record in primary_records:
            yield record

    monkeypatch.setattr(fallback_service, "run_fetch_with_fallback_policy", fake_policy)

    async def primary_fetcher(
        primary_ids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, object]]:
        del limit
        for primary_id in primary_ids:
            yield {"id": primary_id}

    request = FallbackFetchRequest(
        filter_ids=["A", "B", ""],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        normalize_id=_normalize_identity,
        extract_record_id=_extract_record_id,
        fallback_handler=None,
        limit=1,
        trim_primary_ids_to_limit=False,
    )

    results = await collect_async_iterator(orchestrator.execute(request))

    assert [str(item["id"]) for item in results] == ["A", "B"]
    assert seen_primary_ids == ["A", "B"]


@pytest.mark.asyncio
async def test_execute_records_unified_fallback_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_adapter_metrics = MagicMock()
    orchestrator = FallbackFetchOrchestrator(mock_adapter_metrics)

    async def fake_policy(
        *,
        primary_records: AsyncIterator[dict[str, object]],
        primary_ids: list[str],
        title_only_entries: list[str],
        fallback_mapping: dict[str, str],
        normalize_id,
        extract_record_id,
        fallback_handler,
        limit: int | None = None,
        primary_lookup_method: str | None = None,
        phase1_summary_logger=None,
    ) -> AsyncIterator[dict[str, object]]:
        del (
            primary_ids,
            title_only_entries,
            fallback_mapping,
            normalize_id,
            extract_record_id,
            fallback_handler,
            limit,
            primary_lookup_method,
            phase1_summary_logger,
        )
        async for record in primary_records:
            yield record
        yield {"id": "fallback-hit", "_lookup_method": "title_fallback"}

    monkeypatch.setattr(fallback_service, "run_fetch_with_fallback_policy", fake_policy)

    async def primary_fetcher(
        primary_ids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, object]]:
        del limit
        for primary_id in primary_ids[:1]:
            yield {"id": primary_id, "_lookup_method": "doi"}

    request = FallbackFetchRequest(
        filter_ids=["10.1/a", "10.2/b", "__title_only_0__"],
        fallback_mapping={"10.2/b": "Missing title", "__title_only_0__": "Title only"},
        primary_record_fetcher=primary_fetcher,
        normalize_id=_normalize_strip_lower,
        extract_record_id=_extract_record_id,
        fallback_handler=MagicMock(),
        primary_lookup_method="doi",
    )

    _ = await collect_async_iterator(orchestrator.execute(request))

    mock_adapter_metrics.record_fallback_outcome.assert_called_once_with(
        "fetch_filtered_with_fallback",
        candidates=2,
        hits=1,
    )


def test_default_fallback_execution_delegates_hooks_and_handler() -> None:
    handler = MagicMock()
    strategy = DefaultFallbackExecution(
        normalize_id_hook=_normalize_strip_lower,
        extract_record_id_hook=_extract_record_id,
        fallback_handler_hook=handler,
    )

    assert strategy.normalize_id("  A  ") == "a"
    assert strategy.extract_record_id({"id": "record-1"}) == "record-1"
    assert strategy.fallback_handler is handler


def test_request_resolve_methods_prefer_explicit_hooks_over_strategy() -> None:
    strategy = DefaultFallbackExecution(
        normalize_id_hook=lambda _value: "from-strategy",
        extract_record_id_hook=lambda _record: "from-strategy",
        fallback_handler_hook=MagicMock(name="strategy-handler"),
    )
    explicit_handler = MagicMock(name="explicit-handler")
    request = FallbackFetchRequest(
        filter_ids=[],
        fallback_mapping={},
        primary_record_fetcher=_empty_records,
        normalize_id=_normalize_identity,
        extract_record_id=_extract_record_id,
        fallback_handler=explicit_handler,
        strategy=strategy,
    )

    assert request.resolve_normalize_id() is _normalize_identity
    assert request.resolve_extract_record_id() is _extract_record_id
    assert request.resolve_fallback_handler() is explicit_handler


def test_request_resolve_methods_fall_back_to_strategy_hooks() -> None:
    handler = MagicMock(name="strategy-handler")
    strategy = DefaultFallbackExecution(
        normalize_id_hook=_normalize_strip_lower,
        extract_record_id_hook=_extract_record_id,
        fallback_handler_hook=handler,
    )
    request = FallbackFetchRequest(
        filter_ids=[],
        fallback_mapping={},
        primary_record_fetcher=_empty_records,
        strategy=strategy,
    )

    assert request.resolve_normalize_id()("  A  ") == "a"
    assert request.resolve_extract_record_id()({"id": "record-2"}) == "record-2"
    assert request.resolve_fallback_handler() is handler


@pytest.mark.parametrize(
    ("resolver_name", "expected_message"),
    [
        ("resolve_normalize_id", "normalize_id"),
        ("resolve_extract_record_id", "extract_record_id"),
    ],
)
def test_request_resolve_methods_raise_without_explicit_or_strategy(
    resolver_name: str,
    expected_message: str,
) -> None:
    request = FallbackFetchRequest(
        filter_ids=[],
        fallback_mapping={},
        primary_record_fetcher=_empty_records,
    )

    resolver = getattr(request, resolver_name)
    with pytest.raises(ValueError, match=expected_message):
        resolver()
