"""PubMed MeSH/keyword payload parsing and publication-term enrichment."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as defused_ET  # type: ignore[import-untyped]
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]

from bioetl.application.core.publication_term_runtime import (
    mesh_terms_from_pubmed_headings,
    publication_pubmed_id,
)
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.domain.ports import FilterableDataSourcePort, LoggerPort
    from bioetl.domain.types import BronzeRecord

__all__ = [
    "PubMedPublicationTermEnrichmentService",
    "PubMedPublicationTermPayloadEnricher",
    "parse_pubmed_mesh_xml",
    "pubmed_term_payload",
]


def parse_pubmed_mesh_xml(
    xml_text: str,
) -> tuple[list[dict[str, object]], list[str]]:
    """Parse MeshHeadingList and KeywordList from a PubMed efetch XML payload."""
    try:
        root = defused_ET.fromstring(xml_text)
    except (
        defused_ET.ParseError,
        DefusedXmlException,
    ):
        return [], []

    return _parse_mesh_headings(root), _parse_keywords(root)


def _parse_mesh_headings(root: Element) -> list[dict[str, object]]:
    """Extract valid MeSH descriptor headings from an efetch root element."""
    headings: list[dict[str, object]] = []
    for heading in root.findall(".//MeshHeading"):
        parsed = _parse_mesh_heading(heading)
        if parsed is not None:
            headings.append(parsed)
    return headings


def _parse_mesh_heading(heading: Element) -> dict[str, object] | None:
    """Parse one descriptor and its non-empty qualifiers."""
    descriptor = heading.find("DescriptorName")
    if descriptor is None:
        return None
    name = (descriptor.text or "").strip()
    if not name:
        return None
    qualifiers = [
        {"name": qualifier_name}
        for qualifier in heading.findall("QualifierName")
        if (qualifier_name := (qualifier.text or "").strip())
    ]
    return {
        "descriptor_name": name,
        "descriptor_ui": descriptor.get("UI"),
        "qualifiers": qualifiers,
    }


def _parse_keywords(root: Element) -> list[str]:
    """Extract non-empty keyword strings from an efetch root element."""
    return [
        text
        for keyword in root.findall(".//Keyword")
        if (text := (keyword.text or "").strip())
    ]


def pubmed_term_payload(record: BronzeRecord) -> tuple[object, object]:
    """Prefer structured PubMed fields, then ``_raw_xml`` MeshHeadingList."""
    headings = record.get("mesh_headings")
    keywords = record.get("keywords")
    raw_xml = record.get("_raw_xml")
    xml_headings: object = None
    xml_keywords: object = None
    if isinstance(raw_xml, str) and raw_xml.strip():
        xml_headings, xml_keywords = parse_pubmed_mesh_xml(raw_xml)
    if not headings:
        headings = xml_headings
    if not keywords:
        keywords = xml_keywords
    return headings, keywords


def _as_pmid(value: object) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value) if value > 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _unique_pmids(records: Sequence[BronzeRecord]) -> list[str]:
    pmids: list[str] = []
    seen: set[str] = set()
    for record in records:
        pmid = publication_pubmed_id(record)
        if pmid is None or pmid in seen:
            continue
        seen.add(pmid)
        pmids.append(pmid)
    return pmids


def _attach_pubmed_terms(
    records: Sequence[BronzeRecord],
    pubmed_by_pmid: dict[str, BronzeRecord],
) -> list[BronzeRecord]:
    enriched: list[BronzeRecord] = []
    for record in records:
        pmid = publication_pubmed_id(record)
        matched_record = pubmed_by_pmid.get(pmid) if pmid is not None else None
        if matched_record is None:
            enriched.append(record)
            continue
        headings, keywords = pubmed_term_payload(matched_record)
        mesh_terms, keyword_terms = mesh_terms_from_pubmed_headings(headings, keywords)
        if not mesh_terms and not keyword_terms:
            enriched.append(record)
            continue
        attached = dict(record)
        if mesh_terms:
            attached["mesh_terms"] = mesh_terms
        if keyword_terms:
            attached["keywords"] = keyword_terms
        enriched.append(attached)
    return enriched


class PubMedPublicationTermEnrichmentService:
    """Attach PubMed MeSH/keywords onto ChEMBL document records via ``pubmed_id``."""

    def __init__(
        self,
        pubmed_source: FilterableDataSourcePort,
        logger: LoggerPort,
    ) -> None:
        self._pubmed_source = pubmed_source
        self._logger = logger

    async def _fetch_pubmed_records(
        self, pmids: Sequence[str]
    ) -> dict[str, BronzeRecord]:
        pubmed_by_pmid: dict[str, BronzeRecord] = {}
        async with AsyncExitStack() as stack:
            enter = getattr(self._pubmed_source, "__aenter__", None)
            if callable(enter):
                await stack.enter_async_context(self._pubmed_source)
            async for pubmed_record in self._pubmed_source.fetch_filtered(
                entity_type="publication",
                filter_ids=sorted(pmids),
                filter_field="pmid",
                limit=len(pmids),
            ):
                pmid = _as_pmid(pubmed_record.get("pmid"))
                if pmid is not None:
                    pubmed_by_pmid[pmid] = pubmed_record
        return pubmed_by_pmid

    async def enrich_many(
        self, records: Sequence[BronzeRecord]
    ) -> Sequence[BronzeRecord]:
        pmids = _unique_pmids(records)
        if not pmids:
            return list(records)
        try:
            pubmed_by_pmid = await self._fetch_pubmed_records(pmids)
        except (BioETLError, OSError, RuntimeError, ValueError) as exc:
            self._logger.warning(
                "publication_term_pubmed_enrichment_failed",
                error=str(exc),
                reason_code=(
                    exc.get_reason_code()
                    if isinstance(exc, BioETLError) and exc.get_reason_code()
                    else "publication_term_enrichment_failed"
                ),
                pmid_count=len(pmids),
            )
            return list(records)
        return _attach_pubmed_terms(records, pubmed_by_pmid)


PubMedPublicationTermPayloadEnricher = PubMedPublicationTermEnrichmentService
