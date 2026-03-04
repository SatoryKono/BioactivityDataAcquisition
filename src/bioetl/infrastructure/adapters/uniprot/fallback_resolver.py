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
    """Resolve missing IDs that are eligible for fallback lookup."""
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
    fallback_result_cache: dict[str, BronzeRecord | None] = {}
    for missing_id in missing_ids:
        if limit and fetched >= limit:
            break

        fallback_value = fallback_mapping.get(missing_id)
        if not fallback_value:
            continue

        if fallback_value in fallback_result_cache:
            cached_record = fallback_result_cache[fallback_value]
            if cached_record is None:
                continue
            yield dict(cached_record)
            fetched += 1
            if limit and fetched >= limit:
                return
            continue

        first_record: BronzeRecord | None = None
        async for record in strategy(query=fallback_value, limit=1):
            first_record = dict(record)
            break

        fallback_result_cache[fallback_value] = first_record
        if first_record is not None:
            yield dict(first_record)
            fetched += 1
            if limit and fetched >= limit:
                return


__all__ = [
    "iter_uniprot_fallback_records",
    "resolve_uniprot_missing_ids",
]
