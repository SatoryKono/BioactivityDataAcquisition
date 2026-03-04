from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from bioetl.domain.exceptions import ExternalServiceError, RetryExhaustedError
from bioetl.infrastructure.adapters.common.fetch_retry_policy import (
    is_retry_exhausted_error,
    run_fetch_with_fallback_policy,
    split_filter_ids_for_fallback,
)


def test_split_filter_ids_for_fallback_supports_markers_and_empty() -> None:
    primary, title_only = split_filter_ids_for_fallback(
        ["10.1/a", "", "  ", "__title_only_0__", "10.2/b"]
    )
    assert primary == ["10.1/a", "10.2/b"]
    assert title_only == ["", "  ", "__title_only_0__"]


def test_is_retry_exhausted_error_direct_and_wrapped() -> None:
    retry_error = RetryExhaustedError("http://x", attempts=3)
    wrapped = ExternalServiceError("wrapped")
    wrapped.__cause__ = retry_error
    unrelated = ValueError("nope")

    assert is_retry_exhausted_error(retry_error) is True
    assert is_retry_exhausted_error(wrapped) is True
    assert is_retry_exhausted_error(unrelated) is False


class _FallbackStub:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def process_missing_dois(
        self,
        dois: list[str],
        found_dois: set[str],
        fallback_mapping: dict[str, str],
        normalize_fn,
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[dict[str, object]]:
        self.calls.append("phase2")
        assert "10.1/a" in dois
        assert "10.2/b" in found_dois
        assert fallback_mapping["10.1/a"] == "Missing title"
        assert normalize_fn("10.1/a") == "10.1/a"
        yield {"id": "phase2"}

    async def process_title_only_entries(
        self,
        entries: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[dict[str, object]]:
        self.calls.append("phase3")
        assert "__title_only_0__" in entries
        assert fallback_mapping["__title_only_0__"] == "Title only"
        yield {"id": "phase3"}


@pytest.mark.asyncio
async def test_run_fetch_with_fallback_policy_orchestrates_three_phases() -> None:
    async def primary_records() -> AsyncIterator[dict[str, object]]:
        yield {"id": "phase1-a", "doi": "10.2/B"}
        yield {"id": "phase1-b", "doi": "10.3/C", "_lookup_method": "existing"}

    fallback = _FallbackStub()
    seen_summary: list[tuple[int, int]] = []
    results = [
        record
        async for record in run_fetch_with_fallback_policy(
            primary_records=primary_records(),
            primary_ids=["10.1/a", "10.2/b"],
            title_only_entries=["__title_only_0__"],
            fallback_mapping={
                "10.1/a": "Missing title",
                "__title_only_0__": "Title only",
            },
            normalize_id=lambda value: value.lower().strip(),
            extract_record_id=lambda rec: str(rec.get("doi", "")),
            fallback_handler=fallback,
            primary_lookup_method="doi",
            phase1_summary_logger=lambda total, found: seen_summary.append(
                (total, found)
            ),
        )
    ]

    assert [str(item["id"]) for item in results] == [
        "phase1-a",
        "phase1-b",
        "phase2",
        "phase3",
    ]
    assert results[0]["_lookup_method"] == "doi"
    assert results[1]["_lookup_method"] == "existing"
    assert fallback.calls == ["phase2", "phase3"]
    assert seen_summary == [(2, 2)]


@pytest.mark.asyncio
async def test_run_fetch_with_fallback_policy_respects_limit() -> None:
    async def primary_records() -> AsyncIterator[dict[str, object]]:
        yield {"id": "p1", "doi": "10.1/a"}
        yield {"id": "p2", "doi": "10.2/b"}

    fallback = _FallbackStub()
    results = [
        record
        async for record in run_fetch_with_fallback_policy(
            primary_records=primary_records(),
            primary_ids=["10.1/a", "10.2/b"],
            title_only_entries=["__title_only_0__"],
            fallback_mapping={
                "10.1/a": "Missing title",
                "__title_only_0__": "Title only",
            },
            normalize_id=lambda value: value.lower().strip(),
            extract_record_id=lambda rec: str(rec.get("doi", "")),
            fallback_handler=fallback,
            primary_lookup_method="doi",
            limit=1,
        )
    ]

    assert [str(item["id"]) for item in results] == ["p1"]
    assert fallback.calls == []
