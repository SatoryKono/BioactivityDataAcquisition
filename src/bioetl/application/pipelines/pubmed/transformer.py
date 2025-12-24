"""PubMed Publication Transformer.

Extracts comprehensive metadata from PubMed XML records.
See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.pipelines.pubmed.xml_helpers import PubMedXMLParser
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

    def __init__(self, provider: str = "pubmed"):
        """Initialize PubMed publication transformer.

        Args:
            provider: Data provider identifier.

        """
        super().__init__(provider)
        self._parser = PubMedXMLParser()

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
            pmid = self._parser.get_text(root.find(".//PMID"))
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

        result: dict[str, Any] = {"pmid": pmid}
        result.update(self._extract_basic_info(root, article))
        result.update(self._extract_journal_info(article))
        result.update(self._extract_all_dates(article, pubmed_data))
        result.update(self._extract_classification(article, medline))
        result.update(self._extract_metadata(root, article, medline))
        return result

    def _extract_basic_info(
        self, root: ET.Element, article: ET.Element
    ) -> dict[str, Any]:
        """Extract basic article info."""
        return {
            "doi": self._parser.extract_doi(root),
            "title": self._parser.get_text(article.find(".//ArticleTitle")),
            "abstract": self._parser.extract_abstract(article),
            "authors": self._parser.parse_authors(article),
        }

    def _extract_journal_info(self, article: ET.Element) -> dict[str, Any]:
        """Extract journal-related fields."""
        journal_node = article.find(".//Journal")
        journal_issue = journal_node.find("JournalIssue") if journal_node else None
        pagination = article.find(".//Pagination/MedlinePgn")

        return {
            "journal": (
                self._parser.get_text(journal_node.find("Title"))
                if journal_node
                else None
            ),
            "journal_abbrev": (
                self._parser.get_text(journal_node.find("ISOAbbreviation"))
                if journal_node
                else None
            ),
            "issn": (
                self._parser.get_text(journal_node.find("ISSN"))
                if journal_node
                else None
            ),
            "volume": (
                self._parser.get_text(journal_issue.find("Volume"))
                if journal_issue
                else None
            ),
            "issue": (
                self._parser.get_text(journal_issue.find("Issue"))
                if journal_issue
                else None
            ),
            "pages": self._parser.get_text(pagination),
        }

    def _extract_all_dates(
        self, article: ET.Element, pubmed_data: ET.Element | None
    ) -> dict[str, Any]:
        """Extract all date fields."""
        journal_node = article.find(".//Journal")
        journal_issue = journal_node.find("JournalIssue") if journal_node else None
        pub_date_node = journal_issue.find("PubDate") if journal_issue else None
        pub_date, pub_year = self._parser.extract_date(pub_date_node)

        history = pubmed_data.find("History") if pubmed_data else None

        return {
            "pub_date": pub_date,
            "pub_year": pub_year,
            "publication_year": pub_year,
            "accepted_date": self._parser.extract_history_date(history, "accepted"),
            "received_date": self._parser.extract_history_date(history, "received"),
            "revised_date": self._parser.extract_history_date(history, "revised"),
            "epub_date": self._parser.extract_article_date(article, "Electronic"),
        }

    def _extract_classification(
        self, article: ET.Element, medline: ET.Element | None
    ) -> dict[str, Any]:
        """Extract classification fields."""
        return {
            "publication_types": self._parser.parse_publication_types(article),
            "keywords": self._parser.parse_keywords(medline),
            "mesh_terms": self._parser.parse_mesh_terms(medline),
        }

    def _extract_metadata(
        self, root: ET.Element, article: ET.Element, medline: ET.Element | None
    ) -> dict[str, Any]:
        """Extract metadata fields."""
        return {
            "language": self._parser.get_text(article.find(".//Language")),
            "country": (
                self._parser.get_text(medline.find(".//MedlineJournalInfo/Country"))
                if medline
                else None
            ),
            "pmc_id": self._parser.extract_pmc_id(root),
        }
