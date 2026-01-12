"""PubMed Publication Transformer.

See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html

Refactored to use BasePublicationTransformer pattern for consistency
with other publication pipelines (CrossRef, OpenAlex, SemanticScholar).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.pubmed.extractors import (
    AbstractExtractor,
    AuthorExtractor,
    ClassificationExtractor,
    DateExtractor,
    IdentifierExtractor,
)
from bioetl.application.pipelines.pubmed.xml_utils import get_text
from bioetl.domain.entities import Publication
from bioetl.domain.normalization import strip_html_tags
from bioetl.domain.services import DataNormalizationService, IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


class PubMedPublicationTransformer(BasePublicationTransformer):
    """Transformer for PubMed publication records.

    Implements BasePublicationTransformer pattern for unified transformation flow:
    1. Pre-extraction validation (XML parsing)
    2. Business data extraction from parsed XML
    3. Entity ID and content hash computation
    4. Domain entity creation

    The parsed XML root is cached during _pre_extract_validation and reused
    in _extract_business_data to avoid parsing twice.
    """

    # Instance variable to cache parsed XML root between validation and extraction
    _cached_xml_root: ET.Element | None

    def __init__(
        self,
        provider: str = "pubmed",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ):
        """Initialize PubMed publication transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels. Defaults to 'publication'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Optional data normalization service for DOI normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )
        self._cached_xml_root = None
        self._data_normalizer = data_normalizer or DataNormalizationService()

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate raw XML and parse it before extraction.

        Parses the XML upfront and caches the root element. This allows
        ET.ParseError to be caught and converted to ValueError, which
        BaseTransformer.transform() handles gracefully.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record containing _raw_xml field.
            index: Sequential index of the record (unused).

        Raises:
            ValueError: If _raw_xml is missing, empty, or malformed XML.

        """
        raw_xml = record.get("_raw_xml")
        if not raw_xml or not isinstance(raw_xml, str):
            raise ValueError("Missing or invalid _raw_xml field")

        try:
            self._cached_xml_root = ET.fromstring(raw_xml)
        except ET.ParseError as e:
            # Log the parse error with context
            context.logger.warning(
                "XML_parse_error",
                error=str(e),
                pmid=record.get("pmid"),
            )
            raise ValueError(f"XML parse error: {e}") from e

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract all business fields from PubMed XML.

        Uses the cached XML root from _pre_extract_validation.

        Args:
            record: Raw Bronze record (unused, XML already parsed).

        Returns:
            Dictionary of extracted and normalized fields.

        """
        # Use cached XML root from _pre_extract_validation
        root = self._cached_xml_root
        if root is None:
            # This should not happen if _pre_extract_validation ran successfully
            return {"pmid": None}

        pmid = get_text(root.find(".//PMID"))

        medline = root.find(".//MedlineCitation")
        article = root.find(".//Article")
        pubmed_data = root.find(".//PubmedData")

        if article is None:
            return {"pmid": pmid}

        journal_data = self._extract_journal_data(article)
        date_data = self._extract_date_data(article, pubmed_data)

        # Extract and hash PII fields (RULES.md §5.4)
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = AuthorExtractor.parse_authors(article)
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Extract and normalize DOI (lowercase, stripped) for cross-provider consistency
        raw_doi = IdentifierExtractor.extract_doi(root)
        normalized_doi = self._data_normalizer.normalize_doi(raw_doi)

        return {
            "pmid": pmid,
            "doi": normalized_doi,
            "title": get_text(article.find(".//ArticleTitle")),
            "abstract": strip_html_tags(AbstractExtractor.extract_abstract(article)),
            "authors": self.serialize_json_list(hashed_authors),
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

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for PubMed publications.

        Returns:
            'pmid' - the PubMed-specific identifier field.

        """
        return "pmid"

    def _get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class for PubMed publications.

        Returns:
            Publication class.

        """
        return cast("type[BaseEntity]", Publication)

    def _should_log_fallback_lookup(self) -> bool:
        """Disable fallback lookup logging for PubMed.

        PubMed uses PMID-only lookup without title fallback mechanism.

        Returns:
            False - no fallback logging needed.

        """
        return False

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
            "year": pub_year,
            "publication_year": pub_year,
            "accepted_date": DateExtractor.extract_history_date(history, "accepted"),
            "received_date": DateExtractor.extract_history_date(history, "received"),
            "revised_date": DateExtractor.extract_history_date(history, "revised"),
            "epub_date": DateExtractor.extract_article_date(article, "Electronic"),
        }
