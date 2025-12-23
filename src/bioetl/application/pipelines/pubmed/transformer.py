"""PubMed Publication Transformer.

Extracts comprehensive metadata from PubMed XML records.
See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Publication
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


def _get_text(node: ET.Element | None) -> str | None:
    """Extract text from an XML node, returning None if node is None or empty."""
    if node is not None and node.text:
        return node.text.strip()
    return None


def _get_int(node: ET.Element | None) -> int | None:
    """Extract integer from a node, returning None if invalid."""
    text = _get_text(node)
    if text:
        try:
            return int(text)
        except ValueError:
            pass
    return None


def _format_date(year: str | None, month: str | None, day: str | None) -> str | None:
    """Format date components into ISO date string (YYYY-MM-DD or partial)."""
    if not year:
        return None

    parts = [year]
    if month:
        # Handle month names like "Jan", "Feb", etc.
        month_map = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        }
        month_lower = month.lower()[:3]
        month_num = month_map.get(month_lower, month.zfill(2))
        parts.append(month_num)

        if day:
            parts.append(day.zfill(2))

    return "-".join(parts)


def _extract_date(date_node: ET.Element | None) -> tuple[str | None, int | None]:
    """Extract date string and year from a date element.

    Returns:
        Tuple of (formatted_date_string, year_int)
    """
    if date_node is None:
        return None, None

    year = _get_text(date_node.find("Year"))
    month = _get_text(date_node.find("Month"))
    day = _get_text(date_node.find("Day"))

    date_str = _format_date(year, month, day)
    year_int = _get_int(date_node.find("Year"))

    return date_str, year_int


def _extract_history_date(
    history_node: ET.Element | None, pub_status: str
) -> str | None:
    """Extract a specific date from PubMedPubDate history.

    Args:
        history_node: The History element from PubmedData.
        pub_status: PubStatus value to look for (received, revised, accepted, etc.)

    Returns:
        ISO formatted date string or None.
    """
    if history_node is None:
        return None

    for date_node in history_node.findall("PubMedPubDate"):
        if date_node.get("PubStatus") == pub_status:
            date_str, _ = _extract_date(date_node)
            return date_str
    return None


def _extract_article_date(article_node: ET.Element | None, date_type: str) -> str | None:
    """Extract date from ArticleDate element by DateType attribute.

    Args:
        article_node: The Article element.
        date_type: DateType attribute value (e.g., "Electronic").

    Returns:
        ISO formatted date string or None.

    Note:
        ArticleDate is used for electronic publication dates, while
        PubMedPubDate in History is used for processing dates.
    """
    if article_node is None:
        return None

    for date_node in article_node.findall(".//ArticleDate"):
        if date_node.get("DateType") == date_type:
            date_str, _ = _extract_date(date_node)
            return date_str
    return None


def _parse_authors(article_node: ET.Element) -> list[str]:
    """Extract list of authors in 'LastName, Initials' format."""
    author_list = article_node.find(".//AuthorList")
    if author_list is None:
        return []

    authors = []
    for author in author_list.findall("Author"):
        last_name = _get_text(author.find("LastName"))
        initials = _get_text(author.find("Initials"))
        fore_name = _get_text(author.find("ForeName"))

        if last_name:
            if initials:
                authors.append(f"{last_name}, {initials}")
            elif fore_name:
                authors.append(f"{last_name}, {fore_name}")
            else:
                authors.append(last_name)
        else:
            # Collective/group author
            collective = _get_text(author.find("CollectiveName"))
            if collective:
                authors.append(collective)

    return authors


def _parse_publication_types(article_node: ET.Element) -> list[str]:
    """Extract publication types."""
    pub_types = []
    type_list = article_node.find(".//PublicationTypeList")
    if type_list is not None:
        for pub_type in type_list.findall("PublicationType"):
            if pub_type.text:
                pub_types.append(pub_type.text.strip())
    return pub_types


def _parse_keywords(article_node: ET.Element) -> list[str]:
    """Extract keywords from KeywordList."""
    keywords = []
    keyword_list = article_node.find(".//KeywordList")
    if keyword_list is not None:
        for kw in keyword_list.findall("Keyword"):
            if kw.text:
                keywords.append(kw.text.strip())
    return keywords


def _parse_mesh_terms(medline_citation: ET.Element) -> list[str]:
    """Extract MeSH terms from MeshHeadingList."""
    mesh_terms = []
    mesh_list = medline_citation.find(".//MeshHeadingList")
    if mesh_list is not None:
        for heading in mesh_list.findall("MeshHeading"):
            descriptor = heading.find("DescriptorName")
            if descriptor is not None and descriptor.text:
                mesh_terms.append(descriptor.text.strip())
    return mesh_terms


def _extract_doi(article_node: ET.Element) -> str | None:
    """Extract DOI from ArticleIdList or ELocationID."""
    # Try ELocationID first
    for eloc in article_node.findall(".//ELocationID"):
        if eloc.get("EIdType") == "doi" and eloc.text:
            return eloc.text.strip()

    # Fallback to ArticleIdList
    article_id_list = article_node.find(".//ArticleIdList")
    if article_id_list is not None:
        for aid in article_id_list.findall("ArticleId"):
            if aid.get("IdType") == "doi" and aid.text:
                return aid.text.strip()

    return None


def _extract_pmc_id(article_node: ET.Element) -> str | None:
    """Extract PubMed Central ID."""
    article_id_list = article_node.find(".//ArticleIdList")
    if article_id_list is not None:
        for aid in article_id_list.findall("ArticleId"):
            if aid.get("IdType") == "pmc" and aid.text:
                return aid.text.strip()
    return None


def _extract_abstract(article_node: ET.Element) -> str | None:
    """Extract abstract, handling structured abstracts with multiple sections."""
    abstract_node = article_node.find(".//Abstract")
    if abstract_node is None:
        return None

    # Collect all AbstractText sections
    texts = []
    for abstract_text in abstract_node.findall("AbstractText"):
        label = abstract_text.get("Label")
        text = abstract_text.text or ""

        # Handle inline elements
        full_text = "".join(abstract_text.itertext())

        if label and full_text.strip():
            texts.append(f"{label}: {full_text.strip()}")
        elif full_text.strip():
            texts.append(full_text.strip())

    return " ".join(texts) if texts else None


def _extract_business_data(root: ET.Element, pmid: str) -> dict[str, Any]:
    """Extract all business fields from PubMedArticle XML."""
    medline = root.find(".//MedlineCitation")
    article = root.find(".//Article")
    pubmed_data = root.find(".//PubmedData")

    if article is None:
        return {"pmid": pmid}

    # Journal info
    journal_node = article.find(".//Journal")
    journal_issue = journal_node.find("JournalIssue") if journal_node else None

    # Dates
    pub_date_node = journal_issue.find("PubDate") if journal_issue else None
    pub_date, pub_year = _extract_date(pub_date_node)

    # History dates
    history = pubmed_data.find("History") if pubmed_data else None
    accepted_date = _extract_history_date(history, "accepted")
    received_date = _extract_history_date(history, "received")
    revised_date = _extract_history_date(history, "revised")
    epub_date = _extract_article_date(article, "Electronic")

    # Pagination
    pagination = article.find(".//Pagination/MedlinePgn")

    return {
        "pmid": pmid,
        "doi": _extract_doi(root),
        "title": _get_text(article.find(".//ArticleTitle")),
        "abstract": _extract_abstract(article),
        # Journal
        "journal": _get_text(journal_node.find("Title")) if journal_node else None,
        "journal_abbrev": (
            _get_text(journal_node.find("ISOAbbreviation")) if journal_node else None
        ),
        "issn": _get_text(journal_node.find("ISSN")) if journal_node else None,
        "volume": _get_text(journal_issue.find("Volume")) if journal_issue else None,
        "issue": _get_text(journal_issue.find("Issue")) if journal_issue else None,
        "pages": _get_text(pagination),
        # Authors
        "authors": _parse_authors(article),
        # Dates
        "pub_date": pub_date,
        "pub_year": pub_year,
        "publication_year": pub_year,  # Legacy alias
        "accepted_date": accepted_date,
        "received_date": received_date,
        "revised_date": revised_date,
        "epub_date": epub_date,
        # Classification
        "publication_types": _parse_publication_types(article),
        "keywords": _parse_keywords(medline) if medline else [],
        "mesh_terms": _parse_mesh_terms(medline) if medline else [],
        # Metadata
        "language": _get_text(article.find(".//Language")),
        "country": (
            _get_text(medline.find(".//MedlineJournalInfo/Country"))
            if medline
            else None
        ),
        "pmc_id": _extract_pmc_id(root),
    }


class PubMedPublicationTransformer(BaseTransformer):
    """Transformer for PubMed publication records.

    Extracts comprehensive metadata from PubMed XML including:
    - Basic info: PMID, DOI, title, abstract
    - Journal: name, abbreviation, ISSN, volume, issue, pages
    - Authors: formatted as 'LastName, Initials'
    - Dates: publication, accepted, received, revised, epub
    - Classification: publication types, keywords, MeSH terms
    - Metadata: language, country, PMC ID
    """

    def __init__(self, provider: str = "pubmed"):
        super().__init__(provider)

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw PubMed XML record to Silver format."""
        raw_xml = record.get("_raw_xml")
        if not raw_xml or not isinstance(raw_xml, str):
            return None

        try:
            root = ET.fromstring(raw_xml)
            pmid = _get_text(root.find(".//PMID"))
            if not pmid:
                return None

            business_data = _extract_business_data(root, pmid)

            entity_id = generate_entity_id(
                record={"pmid": pmid},
                provider=self.provider,
                id_field="pmid",
            )
            content_hash = self.compute_content_hash(business_data, exclude_none=False)

            publication = Publication(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )
            return cast("SilverRecord", self.entity_to_silver_record(publication))

        except ET.ParseError as e:
            context.logger.warning(
                "XML_parse_error", error=str(e), pmid=record.get("pmid")
            )
            return None
