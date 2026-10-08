"""Optional payload enrichment before publication-term extraction."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

from bioetl.application.core.derived_scan_budget import bounded_source_records
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


def _needs_pubmed_enrichment(
    record: BronzeRecord, extract_terms: _ExtractTerms
) -> bool:
    publication_id = _publication_id(record)
    if publication_id is None:
        return False
    if publication_pubmed_id(record) is None:
        return False
    return not extract_terms(record, publication_id)


async def _attach_pubmed_payloads(
    records: list[BronzeRecord],
    *,
    extract_terms: _ExtractTerms,
    enricher: PublicationTermEnrichmentPort,
) -> list[BronzeRecord]:
    need = [
        record for record in records if _needs_pubmed_enrichment(record, extract_terms)
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


async def _emit_publication_terms(
    batch: list[BronzeRecord],
    *,
    extract_terms: _ExtractTerms,
    enricher: PublicationTermEnrichmentPort | None,
    term_count: int,
    limit: int | None,
) -> AsyncIterator[tuple[BronzeRecord, int]]:
    prepared = batch
    if enricher is not None:
        prepared = await _attach_pubmed_payloads(
            batch, extract_terms=extract_terms, enricher=enricher
        )
    count = term_count
    for record in prepared:
        publication_id = _publication_id(record)
        if publication_id is None:
            continue
        for term in extract_terms(record, publication_id):
            count += 1
            yield term, count
            if limit is not None and count >= limit:
                return


async def _yield_publication_batches(
    publications: AsyncIterator[BronzeRecord],
    *,
    limit: int | None,
    scan_limit: int,
    extract_terms: _ExtractTerms,
    enricher: PublicationTermEnrichmentPort | None,
) -> AsyncIterator[BronzeRecord]:
    term_count = 0
    buffer: list[BronzeRecord] = []
    async for publication in bounded_source_records(
        publications, max_records=scan_limit
    ):
        buffer.append(publication)
        if len(buffer) < PUBLICATION_TERM_PUBMED_ENRICH_BATCH_SIZE:
            continue
        async for term, count in _emit_publication_terms(
            buffer,
            extract_terms=extract_terms,
            enricher=enricher,
            term_count=term_count,
            limit=limit,
        ):
            term_count = count
            yield term
        if limit is not None and term_count >= limit:
            return
        buffer = []
    if buffer:
        async for term, _count in _emit_publication_terms(
            buffer,
            extract_terms=extract_terms,
            enricher=enricher,
            term_count=term_count,
            limit=limit,
        ):
            yield term


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
    try:
        async for term in _yield_publication_batches(
            publications,
            limit=limit,
            scan_limit=scan_limit,
            extract_terms=extract_terms,
            enricher=enricher,
        ):
            yield term
    finally:
        await close_publications(publications)
