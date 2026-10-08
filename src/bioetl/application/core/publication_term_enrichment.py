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


async def _emit_enrichment_batch(
    batch: list[BronzeRecord],
    *,
    limit: int | None,
    extract_terms: _ExtractTerms,
    enricher: PublicationTermEnrichmentPort | None,
    state: list[int],
) -> AsyncIterator[BronzeRecord]:
    prepared = batch
    if enricher is not None:
        prepared = await _attach_pubmed_payloads(
            batch, extract_terms=extract_terms, enricher=enricher
        )
    for record in prepared:
        publication_id = _publication_id(record)
        if publication_id is None:
            continue
        for term in extract_terms(record, publication_id):
            yield term
            state[0] += 1
            if limit is not None and state[0] >= limit:
                return


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
    state = [0]
    buffer: list[BronzeRecord] = []

    try:
        async for publication in bounded_source_records(
            publications, max_records=scan_limit
        ):
            buffer.append(publication)
            if len(buffer) == PUBLICATION_TERM_PUBMED_ENRICH_BATCH_SIZE:
                async for term in _emit_enrichment_batch(
                    buffer,
                    limit=limit,
                    extract_terms=extract_terms,
                    enricher=enricher,
                    state=state,
                ):
                    yield term
                buffer.clear()
                if limit is not None and state[0] >= limit:
                    return
        if buffer:
            async for term in _emit_enrichment_batch(
                buffer,
                limit=limit,
                extract_terms=extract_terms,
                enricher=enricher,
                state=state,
            ):
                yield term
    finally:
        await close_publications(publications)
