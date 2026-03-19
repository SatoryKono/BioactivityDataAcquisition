"""Key extraction helpers for post-seed composite runner flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "CompositeEnrichmentKeyContext",
    "CompositeEnrichmentKeyResult",
    "extract_enrichment_keys",
]


@dataclass(frozen=True, slots=True)
class CompositeEnrichmentKeyContext:
    """Canonical context for extracting composite enrichment keys."""

    composite_name: str
    silver_table: str
    output_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompositeEnrichmentKeyResult:
    """Extracted keys and derived metadata for enrichment orchestration."""

    keys_df: pl.DataFrame
    keys_count: int


async def extract_enrichment_keys(
    *,
    key_extractor: KeyExtractorService,
    logger: LoggerPort,
    request: CompositeEnrichmentKeyContext,
) -> CompositeEnrichmentKeyResult:
    """Extract enrichment keys and emit the canonical observability payload."""
    keys_df = await key_extractor.extract(
        silver_table=request.silver_table,
        keys=request.output_keys,
    )
    result = CompositeEnrichmentKeyResult(
        keys_df=keys_df,
        keys_count=len(keys_df),
    )
    logger.info(
        "Extracted keys for enrichment",
        composite=request.composite_name,
        keys_count=result.keys_count,
    )
    return result


CompositeEnrichmentKeyRequest = CompositeEnrichmentKeyContext
