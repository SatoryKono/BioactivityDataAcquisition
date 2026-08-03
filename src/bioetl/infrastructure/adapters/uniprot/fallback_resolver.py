"""UniProt fallback resolution helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping, Sequence

from bioetl.domain.types import BronzeRecord

_FetchStrategy = Callable[..., AsyncIterator[BronzeRecord]]


def resolve_uniprot_missing_ids(
    *,
    filter_ids: Sequence[str],
    found_ids: set[str],
    fallback_mapping: Mapping[str, str],
) -> list[str]:
    """Resolve missing IDs that are eligible for fallback lookup.

    Returns:
        List of IDs that were not found and have a fallback mapping entry.
    """
    if not fallback_mapping:
        return []

    missing_ids: list[str] = []
    seen_missing: set[str] = set()
    for filter_id in filter_ids:
        if filter_id in found_ids:
            continue
        if filter_id not in fallback_mapping:
            continue
        if filter_id in seen_missing:
            continue
        seen_missing.add(filter_id)
        missing_ids.append(filter_id)
    return missing_ids


def _reached_limit(fetched: int, limit: int | None) -> bool:
    return limit is not None and fetched >= limit


async def _fetch_first_record(
    strategy: _FetchStrategy,
    fallback_value: str,
) -> BronzeRecord | None:
    async for record in strategy(query=fallback_value, limit=1):
        return dict(record)
    return None


async def iter_uniprot_fallback_records(
    *,
    strategy: _FetchStrategy,
    missing_ids: Sequence[str],
    fallback_mapping: Mapping[str, str],
    limit: int | None,
    already_fetched: int,
) -> AsyncIterator[BronzeRecord]:
    """Iterate fallback records with per-value cache reuse."""
    fetched = already_fetched
    cache: dict[str, BronzeRecord | None] = {}
    for missing_id in missing_ids:
        if _reached_limit(fetched, limit):
            return

        fallback_value = fallback_mapping.get(missing_id)
        if not fallback_value:
            continue

        if fallback_value not in cache:
            cache[fallback_value] = await _fetch_first_record(strategy, fallback_value)

        record = cache[fallback_value]
        if record is not None:
            yield dict(record)
            fetched += 1


__all__ = [
    "iter_uniprot_fallback_records",
    "resolve_uniprot_missing_ids",
]
