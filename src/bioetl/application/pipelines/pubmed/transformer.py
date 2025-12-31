"""PubMed Publication Transformer.

See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.pipelines.pubmed.extractors import (
    AbstractExtractor,
    AuthorExtractor,
    ClassificationExtractor,
    DateExtractor,
    IdentifierExtractor,
)
from bioetl.application.pipelines.pubmed.xml_utils import get_text
from bioetl.domain.entities import Publication
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PubMedPublicationTransformer(BaseTransformer):
    """Transformer for PubMed publication records."""

    def __init__(
        self,
        provider: str = "pubmed",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ):
        """Initialize PubMed publication transformer.

        Args:
            provider: Data provider identifier.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).

        """
        super().__init__(
            provider,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )

    async def _transform_impl(
        self, context: PipelineContext, record: BronzeRecord, index: int
    ) -> SilverRecord | None:
        """Transform raw PubMed XML record to Silver format."""
        raw_xml = record.get("_raw_xml")
        if not raw_xml or not isinstance(raw_xml, str):
            return None

        try:
            root = ET.fromstring(raw_xml)
            pmid = get_text(root.find(".//PMID"))
            if not pmid:
                return None

            business_data = self._extract_business_data(root, pmid)
            entity_id = self.compute_entity_id(
                source_id=pmid,
                record={"pmid": pmid},
            )
            content_hash = self.compute_content_hash(business_data, exclude_none=False)
            entity = self._create_entity(
                Publication,
                context,
                entity_id=entity_id,
                content_hash=content_hash,
                index=index,
                **business_data,
            )
            return cast("SilverRecord", self.entity_to_silver_record(entity))

        except ET.ParseError as e:
            context.logger.warning(
                "XML_parse_error", error=str(e), pmid=record.get("pmid")
            )
            return None

    def _extract_business_data(self, root: ET.Element, pmid: str) -> dict[str, Any]:
        """Extract all business fields from PubMedArticle XML."""
        medline = root.find(".//MedlineCitation")
        article = root.find(".//Article")
        pubmed_data = root.find(".//PubmedData")

        if article is None:
            return {"pmid": pmid}

        journal_data = self._extract_journal_data(article)
        date_data = self._extract_date_data(article, pubmed_data)

        # Extract and hash PII fields (RULES.md §5.4)
        raw_authors = AuthorExtractor.parse_authors(article)
        hashed_authors = self.hash_pii_list(raw_authors) or []

        return {
            "pmid": pmid,
            "doi": IdentifierExtractor.extract_doi(root),
            "title": get_text(article.find(".//ArticleTitle")),
            "abstract": AbstractExtractor.extract_abstract(article),
            "authors": hashed_authors,
            **journal_data,
            **date_data,
            "publication_types": ClassificationExtractor.parse_publication_types(
                article
            ),
            "keywords": ClassificationExtractor.parse_keywords(medline),
            "mesh_terms": ClassificationExtractor.parse_mesh_terms(medline),
            "language": get_text(article.find(".//Language")),
            "country": (
                get_text(medline.find(".//MedlineJournalInfo/Country"))
                if medline
                else None
            ),
            "pmc_id": IdentifierExtractor.extract_pmc_id(root),
        }

    def _extract_journal_data(self, article: ET.Element) -> dict[str, Any]:
        """Extract journal-related data from article XML."""
        journal = article.find(".//Journal")
        if not journal:
            return {
                "journal": None,
                "journal_abbrev": None,
                "issn": None,
                "volume": None,
                "issue": None,
                "pages": get_text(article.find(".//Pagination/MedlinePgn")),
            }

        journal_issue = journal.find("JournalIssue")
        return {
            "journal": get_text(journal.find("Title")),
            "journal_abbrev": get_text(journal.find("ISOAbbreviation")),
            "issn": get_text(journal.find("ISSN")),
            "volume": get_text(journal_issue.find("Volume")) if journal_issue else None,
            "issue": get_text(journal_issue.find("Issue")) if journal_issue else None,
            "pages": get_text(article.find(".//Pagination/MedlinePgn")),
        }

    def _extract_date_data(
        self, article: ET.Element, pubmed_data: ET.Element | None
    ) -> dict[str, Any]:
        """Extract date-related data from article XML."""
        journal = article.find(".//Journal")
        journal_issue = journal.find("JournalIssue") if journal else None
        pub_date_node = journal_issue.find("PubDate") if journal_issue else None
        pub_date, pub_year = DateExtractor.extract_date(pub_date_node)
        history = pubmed_data.find("History") if pubmed_data else None

        return {
            "pub_date": pub_date,
            "pub_year": pub_year,
            "publication_year": pub_year,
            "accepted_date": DateExtractor.extract_history_date(history, "accepted"),
            "received_date": DateExtractor.extract_history_date(history, "received"),
            "revised_date": DateExtractor.extract_history_date(history, "revised"),
            "epub_date": DateExtractor.extract_article_date(article, "Electronic"),
        }
