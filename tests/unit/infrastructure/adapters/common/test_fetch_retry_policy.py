from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from hypothesis import HealthCheck
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from tests.async_utils import collect_async_iterator

from bioetl.domain.exceptions import ExternalServiceError, RetryExhaustedError
from bioetl.infrastructure.adapters.common.fetch_retry_policy import (
    TITLE_ONLY_MARKER_PREFIX,
    is_retry_exhausted_error,
    run_fetch_with_fallback_policy,
    split_filter_ids_for_fallback,
)


def _normalize_identity(value: str) -> str:
    return value


def _normalize_lower_strip(value: str) -> str:
    return value.lower().strip()


def _extract_doi(record: dict[str, object]) -> str:
    return str(record.get("doi", ""))


def _append_phase1_summary(
    target: list[tuple[int, int]], total: int, found: int
) -> None:
    target.append((total, found))


def _phase1_summary_logger(
    target: list[tuple[int, int]],
):
    def _log(total: int, found: int) -> None:
        _append_phase1_summary(target, total, found)

    return _log


_PARTITION_TEST_SETTINGS = settings(
    deadline=None,
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow],
)
_ASYNC_POLICY_TEST_SETTINGS = settings(
    deadline=None,
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow],
)
_FILTER_ID_TEXT = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters=("_", "-", "/", ".", " "),
    ),
    max_size=32,
)


def test_split_filter_ids_for_fallback_supports_markers_and_empty() -> None:
    primary, title_only = split_filter_ids_for_fallback(
        ["10.1/a", "", "  ", "__title_only_0__", "10.2/b"]
    )
    assert primary == ["10.1/a", "10.2/b"]
    assert title_only == ["", "  ", "__title_only_0__"]


@_PARTITION_TEST_SETTINGS
@given(filter_ids=st.lists(_FILTER_ID_TEXT, max_size=30))
def test_split_filter_ids_for_fallback_partition_property(
    filter_ids: list[str],
) -> None:
    """Property: every input ID is classified consistently by fallback predicate."""
    primary, title_only = split_filter_ids_for_fallback(filter_ids)
    assert len(primary) + len(title_only) == len(filter_ids)

    for raw_id in primary:
        assert raw_id.strip()
        assert not raw_id.strip().startswith(TITLE_ONLY_MARKER_PREFIX)

    for raw_id in title_only:
        assert not raw_id.strip() or raw_id.strip().startswith(TITLE_ONLY_MARKER_PREFIX)


def test_is_retry_exhausted_error_direct_and_wrapped() -> None:
    retry_error = RetryExhaustedError("https://x", attempts=3)
    wrapped = ExternalServiceError("wrapped")
    wrapped.__cause__ = retry_error
    unrelated = ValueError("nope")

    assert is_retry_exhausted_error(retry_error)
    assert is_retry_exhausted_error(wrapped)
    assert not is_retry_exhausted_error(unrelated)


@st.composite
def _fallback_chain_case(
    draw: st.DrawFn,
) -> tuple[list[str], set[str], list[str], int | None]:
    id_alphabet = st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        min_codepoint=48,
        max_codepoint=122,
    )
    primary_ids = draw(
        st.lists(
            st.text(id_alphabet, min_size=1, max_size=8),
            min_size=0,
            max_size=8,
            unique=True,
        )
    )
    if primary_ids:
        resolved_ids = draw(st.sets(st.sampled_from(primary_ids)))
    else:
        resolved_ids = set()
    title_entries = draw(
        st.lists(
            st.one_of(
                st.just(""),
                st.from_regex(r"__title_only_[0-9]{1,2}__", fullmatch=True),
            ),
            min_size=0,
            max_size=5,
        )
    )
    max_flow = len(primary_ids) + len(title_entries)
    limit = draw(st.one_of(st.none(), st.integers(min_value=0, max_value=max_flow + 2)))
    return primary_ids, resolved_ids, title_entries, limit


@_ASYNC_POLICY_TEST_SETTINGS
@given(case=_fallback_chain_case())
def test_run_fetch_with_fallback_policy_prefix_property(
    case: tuple[list[str], set[str], list[str], int | None],
) -> None:
    primary_ids, resolved_ids, title_only_entries, limit = case
    fallback_mapping = {
        **{doi: f"title:{doi}" for doi in primary_ids},
        **{entry: f"title:{entry or 'empty'}" for entry in title_only_entries},
    }

    async def primary_records() -> AsyncIterator[dict[str, object]]:
        for doi in primary_ids:
            if doi not in resolved_ids:
                continue
            yield {"id": f"p:{doi}", "doi": doi}

    class _Policy:
        async def process_missing_dois(
            self,
            dois: list[str],
            found_dois: set[str],
            fallback_mapping: dict[str, str],
            normalize_fn,
            limit: int | None,
            fetched: int,
        ) -> AsyncIterator[dict[str, object]]:
            del fallback_mapping, normalize_fn, limit, fetched
            for doi in dois:
                if doi.lower() in found_dois:
                    continue
                yield {"id": f"m:{doi}"}

        async def process_title_only_entries(
            self,
            entries: list[str],
            fallback_mapping: dict[str, str],
            limit: int | None,
            fetched: int,
        ) -> AsyncIterator[dict[str, object]]:
            del fallback_mapping, limit, fetched
            for entry in entries:
                yield {"id": f"t:{entry}"}

    # Production code tracks found IDs in lowercase (case-insensitive dedup).
    # Build the same lowercase set to predict which IDs phase-2 will skip.
    found_lower: set[str] = {
        doi.strip().lower() for doi in primary_ids if doi in resolved_ids
    }
    expected_ids = [
        *(f"p:{doi}" for doi in primary_ids if doi in resolved_ids),
        *(
            f"m:{doi}"
            for doi in primary_ids
            if doi not in resolved_ids and doi.strip().lower() not in found_lower
        ),
        *(f"t:{entry}" for entry in title_only_entries),
    ]
    if limit is not None:
        expected_ids = expected_ids[:limit]

    async def _collect_ids() -> list[str]:
        rows = await collect_async_iterator(
            run_fetch_with_fallback_policy(
                primary_records=primary_records(),
                primary_ids=primary_ids,
                title_only_entries=title_only_entries,
                fallback_mapping=fallback_mapping,
                normalize_id=_normalize_identity,
                extract_record_id=_extract_doi,
                fallback_handler=_Policy(),
                limit=limit,
                primary_lookup_method="doi",
            )
        )
        return [str(row["id"]) for row in rows]

    assert asyncio.run(_collect_ids()) == expected_ids


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
    results = await collect_async_iterator(
        run_fetch_with_fallback_policy(
            primary_records=primary_records(),
            primary_ids=["10.1/a", "10.2/b"],
            title_only_entries=["__title_only_0__"],
            fallback_mapping={
                "10.1/a": "Missing title",
                "__title_only_0__": "Title only",
            },
            normalize_id=_normalize_lower_strip,
            extract_record_id=_extract_doi,
            fallback_handler=fallback,
            primary_lookup_method="doi",
            phase1_summary_logger=_phase1_summary_logger(seen_summary),
        )
    )

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
    results = await collect_async_iterator(
        run_fetch_with_fallback_policy(
            primary_records=primary_records(),
            primary_ids=["10.1/a", "10.2/b"],
            title_only_entries=["__title_only_0__"],
            fallback_mapping={
                "10.1/a": "Missing title",
                "__title_only_0__": "Title only",
            },
            normalize_id=_normalize_lower_strip,
            extract_record_id=_extract_doi,
            fallback_handler=fallback,
            primary_lookup_method="doi",
            limit=1,
        )
    )

    assert [str(item["id"]) for item in results] == ["p1"]
    assert fallback.calls == []
