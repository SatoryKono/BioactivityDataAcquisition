"""OpenAlex-specific fallback resolution wrapper."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common import run_fetch_with_fallback_policy

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.openalex.fallback import TitleFallbackHandler


async def resolve_openalex_fallback(
    *,
    primary_records: AsyncIterator[BronzeRecord],
    primary_ids: list[str],
    title_only_entries: list[str],
    fallback_mapping: dict[str, str],
    normalize_id: Callable[[str], str | None],
    extract_record_id: Callable[[BronzeRecord], str | None],
    fallback_handler: TitleFallbackHandler,
    limit: int | None,
    phase1_summary_logger: Callable[[int, int], None] | None,
) -> AsyncIterator[BronzeRecord]:
    """Resolve DOI-first fetch with title fallback using shared policy."""
    async for work in run_fetch_with_fallback_policy(
        primary_records=primary_records,
        primary_ids=primary_ids,
        title_only_entries=title_only_entries,
        fallback_mapping=fallback_mapping,
        normalize_id=normalize_id,
        extract_record_id=extract_record_id,
        fallback_handler=fallback_handler,
        limit=limit,
        primary_lookup_method="doi",
        phase1_summary_logger=phase1_summary_logger,
    ):
        yield work


__all__ = ["resolve_openalex_fallback"]
