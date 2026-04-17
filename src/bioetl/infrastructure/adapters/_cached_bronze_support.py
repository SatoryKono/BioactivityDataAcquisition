"""Private support helpers for CachedBronzeDataSource."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from bioetl.domain.exceptions import CachedBronzeEmptyError
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict


class BronzeBatchReader(Protocol):
    """Minimal reader surface required by CachedBronzeDataSource helpers."""

    base_path: Path
    _flat_structure: bool

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        """Return available Bronze batch paths for the requested scope."""
        ...

    def read_bronze(
        self,
        path: str,
    ) -> AsyncIterator[JsonDict]:
        """Stream Bronze records from one persisted batch path."""
        ...


def parse_bronze_date(date_str: str | None) -> datetime | None:
    """Parse YYYY-MM-DD bronze date to a UTC-aware datetime."""
    if date_str is None:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)


async def list_sorted_batches(
    reader: BronzeBatchReader,
    *,
    provider: str,
    entity_type: str,
    bronze_date: str | None,
) -> list[str]:
    """Return batch paths in deterministic sorted order."""
    if getattr(reader, "_flat_structure", False):
        batches = await reader.list_batches(
            provider="",
            entity="",
            date=parse_bronze_date(bronze_date),
        )
    else:
        batches = await reader.list_batches(
            provider=provider,
            entity=entity_type,
            date=parse_bronze_date(bronze_date),
        )
    return sorted(batches)


def log_unsupported_fetch_params(
    logger: LoggerPort,
    *,
    query: str | None,
    filter_ids: list[str] | None,
) -> None:
    """Log ignored cached-Bronze fetch parameters."""
    if query:
        logger.warning(
            "cached_bronze_query_ignored",
            query=query,
            reason="query parameter not supported for cached Bronze",
        )
    if filter_ids:
        logger.warning(
            "cached_bronze_filter_ignored",
            filter_count=len(filter_ids),
            reason="filter_ids not supported for cached Bronze",
        )


def resolve_bronze_path(
    reader: BronzeBatchReader,
    *,
    provider: str,
    entity_type: str,
) -> str:
    """Resolve effective bronze directory path for empty-cache errors."""
    bronze_path = str(reader.base_path)
    if getattr(reader, "_flat_structure", False):
        return bronze_path
    return str(Path(bronze_path) / provider / entity_type)


def raise_if_empty_batches(
    batches: list[str],
    *,
    reader: BronzeBatchReader,
    provider: str,
    entity_type: str,
    bronze_date: str | None,
) -> None:
    """Raise CachedBronzeEmptyError when no batch files are available."""
    if batches:
        return
    raise CachedBronzeEmptyError(
        provider=provider,
        entity_type=entity_type,
        bronze_path=resolve_bronze_path(
            reader,
            provider=provider,
            entity_type=entity_type,
        ),
        date_filter=bronze_date,
    )


async def iter_batch_records(
    reader: BronzeBatchReader,
    logger: LoggerPort,
    batches: list[str],
) -> AsyncIterator[JsonDict]:
    """Iterate records from sorted batch paths."""
    for batch_path in batches:
        logger.debug("cached_bronze_reading_batch", batch_path=batch_path)
        records = reader.read_bronze(batch_path)
        try:
            async for record in records:
                yield record
        finally:
            aclose = getattr(records, "aclose", None)
            if callable(aclose):
                await aclose()


async def count_batch_records(
    reader: BronzeBatchReader,
    logger: LoggerPort,
    batches: list[str],
) -> int:
    """Count records across all cached bronze batches."""
    total = 0
    logger.info(
        "Estimating total records in Bronze cache...",
        batch_count=len(batches),
    )
    for batch_path in batches:
        records = reader.read_bronze(batch_path)
        try:
            async for _ in records:
                total += 1
        finally:
            aclose = getattr(records, "aclose", None)
            if callable(aclose):
                await aclose()
    logger.info("Total records estimated", total=total)
    return total
