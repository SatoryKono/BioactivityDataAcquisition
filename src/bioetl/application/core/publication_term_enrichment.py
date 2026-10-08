"""Optional payload enrichment before publication-term extraction."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

from bioetl.application.core.derived_scan_budget import batched_source_records
from bioetl.application.core.publication_term_runtime import publication_pubmed_id
from bioetl.domain.ports import PublicationTermEnrichmentPort
from bioetl.domain.types import BronzeRecord

__all__ = [
    "PUBLICATION_TERM_PUBMED_ENRICH_BATCH_SIZE",
    "yield_terms_from_publications",
]

PUBLICATION_TERM_PUBMED_ENRICH_BATCH_SIZE = 200

_ExtractTerms = Callable[[BronzeRecord, str], list[BronzeRecord]]
_ClosePublications = Callable[[AsyncIterator[BronzeRecord]], Awaitable[None]]


def _publication_id(record: BronzeRecord) -> str | None:
    value = record.get("publication_id") or record.get("document_chembl_id")
    return (str(value).strip() or None) if value is not None else None


async def _attach_pubmed_payloads(
    records: list[BronzeRecord],
    *,
    extract_terms: _ExtractTerms,
    enricher: PublicationTermEnrichmentPort,
) -> list[BronzeRecord]:
    need = [
        record
        for record in records
        if (publication_id := _publication_id(record)) is not None
        and publication_pubmed_id(record) is not None
        and not extract_terms(record, publication_id)
    ]
    if not need:
        return records
    enriched = list(await enricher.enrich_many(need))
    if len(enriched) != len(need):
        return records
    replacements = {
        id(original): replacement
        for original, replacement in zip(need, enriched, strict=True)
    }
    return [replacements.get(id(record), record) for record in records]


def _iter_terms(
    records: list[BronzeRecord], *, extract_terms: _ExtractTerms
) -> Iterator[BronzeRecord]:
    for record in records:
        publication_id = _publication_id(record)
        if publication_id is not None:
            yield from extract_terms(record, publication_id)


async def yield_terms_from_publications(
    publications: AsyncIterator[BronzeRecord],
    *,
    limit: int | None,
    scan_limit: int,
    extract_terms: _ExtractTerms,
    enricher: PublicationTermEnrichmentPort | None,
    close_publications: _ClosePublications,
) -> AsyncIterator[BronzeRecord]:
    """Expand publications into term records, enriching empty PubMed-linked docs."""
    term_count = 0
    try:
        async for batch in batched_source_records(
            publications,
            batch_size=PUBLICATION_TERM_PUBMED_ENRICH_BATCH_SIZE,
            max_records=scan_limit,
        ):
            # Extraction yields zero or many terms per record, even after
            # enrichment (missing PubMed matches or empty/invalid payloads).
            # The remaining term limit therefore cannot bound the records
            # needed; truncating this batch could discard later usable terms.
            if enricher is not None:
                batch = await _attach_pubmed_payloads(
                    batch, extract_terms=extract_terms, enricher=enricher
                )
            for term in _iter_terms(batch, extract_terms=extract_terms):
                term_count += 1
                yield term
                if limit is not None and term_count >= limit:
                    return
    finally:
        await close_publications(publications)
