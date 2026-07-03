"""Unit tests for UniProtFallbackPolicy.

Tests policy evaluation, missing-ID resolution, title-only entry processing,
deduplication logic, and edge-case/error paths.

Source: src/bioetl/infrastructure/adapters/uniprot/fallback_policy.py
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.uniprot.fallback_policy import (
    UniProtFallbackPolicy,
)
from tests.helpers.async_iterables import async_iterable


pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers — async generator factories
# ---------------------------------------------------------------------------


async def _async_records(*records: BronzeRecord) -> AsyncIterator[BronzeRecord]:
    """Yield a fixed sequence of records as an async generator."""
    for record in records:
        yield record


def _make_handler(
    *,
    entity_type: str = "protein",
    resolve_missing_ids: Any = None,
    search_fallback: Any = None,
) -> UniProtFallbackPolicy:
    """Build a UniProtFallbackPolicy with injectable callbacks."""

    def _default_resolve(
        ids: list[str], found: set[str], mapping: dict[str, str]
    ) -> list[str]:
        return [uid for uid in ids if uid not in found]

    async def _default_search(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        for uid in ids:
            yield {"accession": uid}

    return UniProtFallbackPolicy(
        entity_type=entity_type,
        resolve_missing_ids=resolve_missing_ids or _default_resolve,
        search_fallback=search_fallback or _default_search,
    )


def _normalize_lower(value: str) -> str:
    return value.lower()


def _normalize_identity(value: str) -> str:
    return value


# ---------------------------------------------------------------------------
# process_missing_dois — forward path (records yielded)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_missing_dois_yields_records_for_unresolved_ids() -> None:
    """Should yield one record per missing ID returned by resolve_missing_ids."""
    yielded: list[BronzeRecord] = []

    async def search_fallback(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        for uid in ids:
            yield {"accession": uid, "source": "search"}

    def resolve(ids: list[str], found: set[str], mapping: dict[str, str]) -> list[str]:
        return [uid for uid in ids if uid.lower() not in found]

    handler = _make_handler(
        resolve_missing_ids=resolve,
        search_fallback=search_fallback,
    )

    async for record in handler.process_missing_dois(
        dois=["P12345", "Q98765"],
        found_dois={"p12345"},  # Q98765 is missing
        fallback_mapping={},
        normalize_fn=_normalize_lower,
        limit=None,
        fetched=0,
    ):
        yielded.append(record)

    assert len(yielded) == 1
    assert yielded[0]["accession"] == "Q98765"


@pytest.mark.asyncio
async def test_process_missing_dois_yields_nothing_when_all_found() -> None:
    """When all primary IDs are found, resolve_missing_ids returns empty list."""

    def resolve(ids: list[str], found: set[str], mapping: dict[str, str]) -> list[str]:
        return [uid for uid in ids if uid.lower() not in found]

    handler = _make_handler(resolve_missing_ids=resolve)

    results: list[BronzeRecord] = []
    async for record in handler.process_missing_dois(
        dois=["P12345"],
        found_dois={"p12345"},
        fallback_mapping={},
        normalize_fn=_normalize_lower,
        limit=None,
        fetched=0,
    ):
        results.append(record)

    assert results == []


@pytest.mark.asyncio
async def test_process_missing_dois_passes_entity_type_to_search_fallback() -> None:
    """The entity_type injected at construction must be forwarded to search_fallback."""
    captured_entity: list[str] = []

    def search_fallback(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        del mapping, limit, fetched
        captured_entity.append(entity_type)
        del ids
        return async_iterable()

    def resolve(ids: list[str], found: set[str], mapping: dict[str, str]) -> list[str]:
        return ids  # pretend all are missing

    handler = _make_handler(
        entity_type="sequence",
        resolve_missing_ids=resolve,
        search_fallback=search_fallback,
    )

    async for _ in handler.process_missing_dois(
        dois=["P00001"],
        found_dois=set(),
        fallback_mapping={},
        normalize_fn=_normalize_identity,
        limit=None,
        fetched=0,
    ):
        raise AssertionError(
            "process_missing_dois should not yield when all IDs are found"
        )

    assert captured_entity == ["sequence"]


@pytest.mark.asyncio
async def test_process_missing_dois_passes_limit_and_fetched_to_search() -> None:
    """limit and fetched values must reach the search_fallback callable."""
    captured: dict[str, Any] = {}

    def search_fallback(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        del entity_type, ids, mapping
        captured["limit"] = limit
        captured["fetched"] = fetched
        return async_iterable()

    def resolve(ids: list[str], found: set[str], mapping: dict[str, str]) -> list[str]:
        return ids

    handler = _make_handler(
        resolve_missing_ids=resolve, search_fallback=search_fallback
    )

    async for _ in handler.process_missing_dois(
        dois=["P00002"],
        found_dois=set(),
        fallback_mapping={},
        normalize_fn=_normalize_identity,
        limit=50,
        fetched=10,
    ):
        raise AssertionError("process_missing_dois should not yield fallback rows here")

    assert captured["limit"] == 50
    assert captured["fetched"] == 10


@pytest.mark.asyncio
async def test_process_missing_dois_ignores_normalize_fn_parameter() -> None:
    """normalize_fn is accepted for protocol compatibility but unused internally."""
    # The implementation does `del normalize_fn` — passing any callable must not raise.
    handler = _make_handler()

    called: list[bool] = []

    def normalize_fn_called(x: str) -> str:
        called.append(True)
        return x

    results: list[BronzeRecord] = []
    async for record in handler.process_missing_dois(
        dois=["P00003"],
        found_dois=set(),
        fallback_mapping={},
        normalize_fn=normalize_fn_called,
        limit=None,
        fetched=0,
    ):
        results.append(record)

    # normalize_fn must NOT have been called (implementation deletes it)
    assert called == []


# ---------------------------------------------------------------------------
# process_title_only_entries — forward path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_title_only_entries_yields_records_for_mapped_entries() -> None:
    """Entries that are keys in fallback_mapping must produce search results."""
    yielded: list[BronzeRecord] = []

    async def search_fallback(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        for uid in ids:
            yield {"accession": uid}

    handler = _make_handler(search_fallback=search_fallback)

    async for record in handler.process_title_only_entries(
        entries=["accession_A"],
        fallback_mapping={"accession_A": "Human Protein A"},
        limit=None,
        fetched=0,
    ):
        yielded.append(record)

    assert len(yielded) == 1
    assert yielded[0]["accession"] == "accession_A"


@pytest.mark.asyncio
async def test_process_title_only_entries_yields_nothing_when_no_mapped_entries() -> (
    None
):
    """Entries not present in fallback_mapping produce no records."""
    handler = _make_handler()

    results: list[BronzeRecord] = []
    async for record in handler.process_title_only_entries(
        entries=["unknown_marker"],
        fallback_mapping={},
        limit=None,
        fetched=0,
    ):
        results.append(record)

    assert results == []


@pytest.mark.asyncio
async def test_process_title_only_entries_deduplicates_fallback_ids() -> None:
    """Each unique fallback ID must appear only once even with duplicate entries."""
    seen_ids: list[list[str]] = []

    async def search_fallback(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        seen_ids.append(list(ids))
        for uid in ids:
            yield {"accession": uid}

    handler = _make_handler(search_fallback=search_fallback)

    results: list[BronzeRecord] = []
    async for record in handler.process_title_only_entries(
        entries=["acc_X", "acc_X", "acc_Y"],  # acc_X duplicated
        fallback_mapping={"acc_X": "Title X", "acc_Y": "Title Y"},
        limit=None,
        fetched=0,
    ):
        results.append(record)

    # search_fallback must have been called once with de-duplicated IDs
    assert len(seen_ids) == 1
    passed_ids = seen_ids[0]
    assert passed_ids.count("acc_X") == 1
    assert "acc_Y" in passed_ids


@pytest.mark.asyncio
async def test_process_title_only_entries_with_empty_entries_list() -> None:
    """Empty entries list must produce no records and not call search_fallback."""
    search_called: list[bool] = []

    async def search_fallback(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        del entity_type, ids, mapping, limit, fetched
        search_called.append(True)
        for _ in ():
            yield {}

    handler = _make_handler(search_fallback=search_fallback)

    results: list[BronzeRecord] = []
    async for record in handler.process_title_only_entries(
        entries=[],
        fallback_mapping={"acc_X": "Title X"},
        limit=None,
        fetched=0,
    ):
        results.append(record)

    assert results == []
    assert search_called == []


# ---------------------------------------------------------------------------
# _collect_title_only_fallback_ids — static helper edge cases
# ---------------------------------------------------------------------------


def test_collect_title_only_fallback_ids_returns_mapped_entries() -> None:
    """Entries that are present in fallback_mapping must be included in output."""
    result = UniProtFallbackPolicy._collect_title_only_fallback_ids(
        entries=["accession_A", "accession_B"],
        fallback_mapping={"accession_A": "Title A", "accession_B": "Title B"},
    )
    assert "accession_A" in result
    assert "accession_B" in result


def test_collect_title_only_fallback_ids_excludes_unmapped_entries() -> None:
    """Entries absent from fallback_mapping must not appear in the output."""
    result = UniProtFallbackPolicy._collect_title_only_fallback_ids(
        entries=["not_in_mapping"],
        fallback_mapping={"different_key": "Title"},
    )
    assert result == []


def test_collect_title_only_fallback_ids_deduplicates_results() -> None:
    """Duplicate entries must appear only once in the output."""
    result = UniProtFallbackPolicy._collect_title_only_fallback_ids(
        entries=["acc_X", "acc_X", "acc_X"],
        fallback_mapping={"acc_X": "Title X"},
    )
    assert result == ["acc_X"]


def test_collect_title_only_fallback_ids_preserves_insertion_order() -> None:
    """Output order must follow the first occurrence in the entries list."""
    result = UniProtFallbackPolicy._collect_title_only_fallback_ids(
        entries=["acc_B", "acc_A", "acc_B"],
        fallback_mapping={"acc_A": "Title A", "acc_B": "Title B"},
    )
    assert result == ["acc_B", "acc_A"]


def test_collect_title_only_fallback_ids_with_empty_entries() -> None:
    """Empty entries list must return an empty list."""
    result = UniProtFallbackPolicy._collect_title_only_fallback_ids(
        entries=[],
        fallback_mapping={"acc_X": "Title X"},
    )
    assert result == []


def test_collect_title_only_fallback_ids_with_empty_mapping() -> None:
    """When fallback_mapping is empty, all entries are excluded."""
    result = UniProtFallbackPolicy._collect_title_only_fallback_ids(
        entries=["acc_A", "acc_B"],
        fallback_mapping={},
    )
    assert result == []


# ---------------------------------------------------------------------------
# FallbackPolicyPort protocol compliance
# ---------------------------------------------------------------------------


def test_handler_satisfies_fallback_policy_port_protocol() -> None:
    """UniProtFallbackPolicy must satisfy the FallbackPolicyPort protocol."""
    from bioetl.domain.ports import FallbackPolicyPort

    handler = _make_handler()
    assert isinstance(handler, FallbackPolicyPort)


# ---------------------------------------------------------------------------
# Integration — multiple records from search_fallback across both phases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_missing_dois_multiple_records_per_id() -> None:
    """search_fallback may yield multiple records per ID; all must be forwarded."""

    async def search_fallback(
        entity_type: str,
        ids: list[str],
        mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        for uid in ids:
            for i in range(3):
                yield {"accession": uid, "variant": i}

    def resolve(ids: list[str], found: set[str], mapping: dict[str, str]) -> list[str]:
        return [uid for uid in ids if uid not in found]

    handler = _make_handler(
        resolve_missing_ids=resolve,
        search_fallback=search_fallback,
    )

    results: list[BronzeRecord] = []
    async for record in handler.process_missing_dois(
        dois=["P00001", "P00002"],
        found_dois=set(),
        fallback_mapping={},
        normalize_fn=lambda x: x,
        limit=None,
        fetched=0,
    ):
        results.append(record)

    # 2 IDs × 3 records each = 6 total
    assert len(results) == 6
