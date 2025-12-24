"""PubMed Publication Transformer.

Extracts comprehensive metadata from PubMed XML records.
See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Publication
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


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

    # Month name to number mapping
    MONTH_MAP: ClassVar[dict[str, str]] = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }

    def __init__(self, provider: str = "pubmed"):
        super().__init__(provider)

    async def _transform_impl(
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
            pmid = self._get_text(root.find(".//PMID"))
            if not pmid:
                return None

            business_data = self._extract_business_data(root, pmid)

            entity_id = generate_entity_id(
                record={"pmid": pmid},
                provider=self.provider,
                id_field="pmid",
            )
            content_hash = self.compute_content_hash(business_data, exclude_none=False)

            entity = self._create_entity(
                Publication,
                context,
                entity_id=entity_id,
                content_hash=content_hash,
                **business_data,
            )
            return cast("SilverRecord", self.entity_to_silver_record(entity))

        except ET.ParseError as e:
            context.logger.warning(
                "XML_parse_error", error=str(e), pmid=record.get("pmid")
            )
            return None

    # ==================== XML Helper Methods ====================

    @staticmethod
    def _get_text(node: ET.Element | None) -> str | None:
        """Extract text from an XML node, returning None if node is None or empty."""
        if node is not None and node.text:
            return node.text.strip()
        return None

    @staticmethod
    def _get_int(node: ET.Element | None) -> int | None:
        """Extract integer from a node, returning None if invalid."""
        if node is not None and node.text:
            text = node.text.strip()
            if text:
                try:
                    return int(text)
                except ValueError:
                    pass
        return None

    def _format_date(
        self,
        year: str | None,
        month: str | None,
        day: str | None,
    ) -> str | None:
        """Format date components into ISO date string (YYYY-MM-DD or partial)."""
        if not year:
            return None

        parts = [year]
        if month:
            month_lower = month.lower()[:3]
            month_num = self.MONTH_MAP.get(month_lower, month.zfill(2))
            parts.append(month_num)

            if day:
                parts.append(day.zfill(2))

        return "-".join(parts)

    def _extract_date(
        self,
        date_node: ET.Element | None,
    ) -> tuple[str | None, int | None]:
        """Extract date string and year from a date element.

        Returns:
            Tuple of (formatted_date_string, year_int)
        """
        if date_node is None:
            return None, None

        year = self._get_text(date_node.find("Year"))
        month = self._get_text(date_node.find("Month"))
        day = self._get_text(date_node.find("Day"))

        date_str = self._format_date(year, month, day)
        year_int = self._get_int(date_node.find("Year"))

        return date_str, year_int

    def _extract_history_date(
        self,
        history_node: ET.Element | None,
        pub_status: str,
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
                date_str, _ = self._extract_date(date_node)
                return date_str
        return None

    def _extract_article_date(
        self,
        article_node: ET.Element | None,
        date_type: str,
    ) -> str | None:
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
                date_str, _ = self._extract_date(date_node)
                return date_str
        return None

    def _parse_authors(self, article_node: ET.Element) -> list[str]:
        """Extract list of authors in 'LastName, Initials' format."""
        author_list = article_node.find(".//AuthorList")
        if author_list is None:
            return []

        authors = []
        for author in author_list.findall("Author"):
            last_name = self._get_text(author.find("LastName"))
            initials = self._get_text(author.find("Initials"))
            fore_name = self._get_text(author.find("ForeName"))

            if last_name:
                if initials:
                    authors.append(f"{last_name}, {initials}")
                elif fore_name:
                    authors.append(f"{last_name}, {fore_name}")
                else:
                    authors.append(last_name)
            else:
                # Collective/group author
                collective = self._get_text(author.find("CollectiveName"))
                if collective:
                    authors.append(collective)

        return authors

    def _parse_publication_types(self, article_node: ET.Element) -> list[str]:
        """Extract publication types."""
        pub_types = []
        type_list = article_node.find(".//PublicationTypeList")
        if type_list is not None:
            for pub_type in type_list.findall("PublicationType"):
                if pub_type.text:
                    pub_types.append(pub_type.text.strip())
        return pub_types

    def _parse_keywords(self, medline_citation: ET.Element | None) -> list[str]:
        """Extract keywords from KeywordList."""
        if medline_citation is None:
            return []

        keywords = []
        keyword_list = medline_citation.find(".//KeywordList")
        if keyword_list is not None:
            for kw in keyword_list.findall("Keyword"):
                if kw.text:
                    keywords.append(kw.text.strip())
        return keywords

    def _parse_mesh_terms(self, medline_citation: ET.Element | None) -> list[str]:
        """Extract MeSH terms from MeshHeadingList."""
        if medline_citation is None:
            return []

        mesh_terms = []
        mesh_list = medline_citation.find(".//MeshHeadingList")
        if mesh_list is not None:
            for heading in mesh_list.findall("MeshHeading"):
                descriptor = heading.find("DescriptorName")
                if descriptor is not None and descriptor.text:
                    mesh_terms.append(descriptor.text.strip())
        return mesh_terms

    def _extract_doi(self, root: ET.Element) -> str | None:
        """Extract DOI from ArticleIdList or ELocationID."""
        article = root.find(".//Article")
        if article is None:
            return None

        # Try ELocationID first
        for eloc in article.findall(".//ELocationID"):
            if eloc.get("EIdType") == "doi" and eloc.text:
                return eloc.text.strip()

        # Fallback to ArticleIdList
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    return aid.text.strip()

        return None

    def _extract_pmc_id(self, root: ET.Element) -> str | None:
        """Extract PubMed Central ID."""
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pmc" and aid.text:
                    return aid.text.strip()
        return None

    def _extract_abstract(self, article_node: ET.Element | None) -> str | None:
        """Extract abstract, handling structured abstracts with multiple sections."""
        if article_node is None:
            return None

        abstract_node = article_node.find(".//Abstract")
        if abstract_node is None:
            return None

        # Collect all AbstractText sections
        texts = []
        for abstract_text in abstract_node.findall("AbstractText"):
            label = abstract_text.get("Label")

            # Handle inline elements
            full_text = "".join(abstract_text.itertext())

            if label and full_text.strip():
                texts.append(f"{label}: {full_text.strip()}")
            elif full_text.strip():
                texts.append(full_text.strip())

        return " ".join(texts) if texts else None

    def _extract_business_data(
        self,
        root: ET.Element,
        pmid: str,
    ) -> dict[str, Any]:
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
        pub_date, pub_year = self._extract_date(pub_date_node)

        # History dates
        history = pubmed_data.find("History") if pubmed_data else None
        accepted_date = self._extract_history_date(history, "accepted")
        received_date = self._extract_history_date(history, "received")
        revised_date = self._extract_history_date(history, "revised")
        epub_date = self._extract_article_date(article, "Electronic")

        # Pagination
        pagination = article.find(".//Pagination/MedlinePgn")

        return {
            "pmid": pmid,
            "doi": self._extract_doi(root),
            "title": self._get_text(article.find(".//ArticleTitle")),
            "abstract": self._extract_abstract(article),
            # Journal
            "journal": self._get_text(journal_node.find("Title")) if journal_node else None,
            "journal_abbrev": (
                self._get_text(journal_node.find("ISOAbbreviation")) if journal_node else None
            ),
            "issn": self._get_text(journal_node.find("ISSN")) if journal_node else None,
            "volume": self._get_text(journal_issue.find("Volume")) if journal_issue else None,
            "issue": self._get_text(journal_issue.find("Issue")) if journal_issue else None,
            "pages": self._get_text(pagination),
            # Authors
            "authors": self._parse_authors(article),
            # Dates
            "pub_date": pub_date,
            "pub_year": pub_year,
            "publication_year": pub_year,  # Legacy alias
            "accepted_date": accepted_date,
            "received_date": received_date,
            "revised_date": revised_date,
            "epub_date": epub_date,
            # Classification
            "publication_types": self._parse_publication_types(article),
            "keywords": self._parse_keywords(medline),
            "mesh_terms": self._parse_mesh_terms(medline),
            # Metadata
            "language": self._get_text(article.find(".//Language")),
            "country": (
                self._get_text(medline.find(".//MedlineJournalInfo/Country"))
                if medline
                else None
            ),
            "pmc_id": self._extract_pmc_id(root),
        }
