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
from bioetl.domain.entities.pubmed import PubMedPublicationEntity
from bioetl.domain.normalization import normalize_pmc_id, parse_page_range
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear, PubMedId

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
            data_normalizer=data_normalizer,
        )
        self._cached_xml_root = None

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

        # Validate PMID using Value Object (returns None for invalid/empty)
        raw_pmid = get_text(root.find(".//PMID"))
        pmid_vo = PubMedId.from_raw(raw_pmid)
        pmid = str(pmid_vo) if pmid_vo else None

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

        # Validate DOI using Value Object (returns None for invalid/empty)
        raw_doi = IdentifierExtractor.extract_doi(root)
        doi_vo = DOI.from_raw(raw_doi)
        normalized_doi = str(doi_vo) if doi_vo else None

        return {
            "pmid": pmid,
            "doi": normalized_doi,
            "title": get_text(article.find(".//ArticleTitle")),
            "abstract": self._data_normalizer.strip_html_tags(
                AbstractExtractor.extract_abstract(article)
            ),
            "authors": self.serialize_json_list(hashed_authors),
            **journal_data,
            **date_data,
            "publication_types": ClassificationExtractor.parse_publication_types(
                article
            ),
            "keywords": ClassificationExtractor.parse_keywords(medline),
            "mesh_terms": ClassificationExtractor.parse_mesh_terms(medline),
            "chemicals": ClassificationExtractor.parse_chemicals(medline),
            "gene_symbols": ClassificationExtractor.parse_gene_symbols(medline),
            "databanks": ClassificationExtractor.parse_databanks(medline),
            "language": get_text(article.find(".//Language")),
            "country": (
                get_text(medline.find(".//MedlineJournalInfo/Country"))
                if medline
                else None
            ),
            "pmc_id": normalize_pmc_id(IdentifierExtractor.extract_pmc_id(root)),
            # === Unified publication fields (cross-provider consistency) ===
            "source": "pubmed",
            "doc_type": "PUBLICATION",  # PubMed primarily contains publications
            "citation_count": None,  # Not available from PubMed
            "is_oa": None,  # Not available from PubMed
            # Lookup metadata (from adapter fallback handler)
            "_lookup_method": cast("dict[str, Any]", record).get(
                "_lookup_method", "pmid"
            ),
            "_original_id": cast("dict[str, Any]", record).get("_original_id"),
            # DQ flags (default: no warnings or errors)
            "_dq_warn": False,
            "_dq_error": False,
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
            PubMedPublicationEntity class.

        """
        return cast("type[BaseEntity]", PubMedPublicationEntity)

    def _should_log_fallback_lookup(self) -> bool:
        """Enable fallback lookup logging for PubMed.

        PubMed supports title-based fallback when PMID lookup fails.
        Adapter uses TitleFallbackHandler for three-phase lookup:
        1. PMID batch fetch
        2. Title fallback for unresolved PMIDs
        3. Title-only lookup for entries without PMIDs

        Returns:
            True - log fallback lookups for observability.

        """
        return True

    def _extract_journal_data(self, article: ET.Element) -> dict[str, Any]:
        """Extract journal-related data from article XML."""
        journal = article.find(".//Journal")
        pages = get_text(article.find(".//Pagination/MedlinePgn"))
        first_page, last_page = parse_page_range(pages)

        if not journal:
            return {
                "journal": None,
                "journal_abbrev": None,
                "issn": None,
                "volume": None,
                "issue": None,
                "pages": pages,
                "first_page": first_page,
                "last_page": last_page,
            }

        journal_issue = journal.find("JournalIssue")
        return {
            "journal": get_text(journal.find("Title")),
            "journal_abbrev": get_text(journal.find("ISOAbbreviation")),
            "issn": get_text(journal.find("ISSN")),
            "volume": get_text(journal_issue.find("Volume")) if journal_issue else None,
            "issue": get_text(journal_issue.find("Issue")) if journal_issue else None,
            "pages": pages,
            "first_page": first_page,
            "last_page": last_page,
        }

    def _compute_publication_date(
        self, epub_date: str | None, pub_date: str | None, year: int | None
    ) -> str | None:
        """Compute unified publication_date (YYYY-MM-DD).

        Priority: epub_date > pub_date > year
        All outputs normalized to full YYYY-MM-DD format using end-of-period strategy.

        Args:
            epub_date: Electronic publication date (YYYY-MM-DD or partial).
            pub_date: Publication date (YYYY-MM-DD or partial).
            year: Publication year.

        Returns:
            ISO date string (YYYY-MM-DD) or None.
        """
        # Priority 1: epub_date if it's a complete date
        if epub_date and len(epub_date) >= 10:
            return epub_date[:10]

        # Priority 2: pub_date (may be partial, normalize it)
        if pub_date:
            return self._normalize_partial_date(pub_date)

        # Priority 3: Construct from year (end of year)
        if year:
            return f"{year}-12-31"

        return None

    def _normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to YYYY-MM-DD (end of period).

        Args:
            date_str: Date string (YYYY, YYYY-MM, or YYYY-MM-DD).

        Returns:
            Full YYYY-MM-DD date or None.
        """
        if not date_str:
            return None
        if len(date_str) >= 10:
            return date_str[:10]
        if len(date_str) == 7:
            # YYYY-MM → YYYY-MM-30
            return f"{date_str}-30"
        if len(date_str) == 4:
            # YYYY → YYYY-12-31
            return f"{date_str}-12-31"
        return None

    def _extract_date_data(
        self, article: ET.Element, pubmed_data: ET.Element | None
    ) -> dict[str, Any]:
        """Extract date-related data from article XML."""
        journal = article.find(".//Journal")
        journal_issue = journal.find("JournalIssue") if journal else None
        pub_date_node = journal_issue.find("PubDate") if journal_issue else None
        pub_date, raw_year = DateExtractor.extract_date(pub_date_node)
        history = pubmed_data.find("History") if pubmed_data else None

        # Validate year using PublicationYear Value Object
        year_vo = PublicationYear.from_raw(raw_year)
        validated_year = year_vo.value if year_vo else None

        epub_date = DateExtractor.extract_article_date(article, "Electronic")

        # Compute unified publication_date
        publication_date = self._compute_publication_date(
            epub_date, pub_date, validated_year
        )

        return {
            "pub_date": pub_date,
            "publication_date": publication_date,
            "year": validated_year,
            "publication_year": validated_year,
            "accepted_date": DateExtractor.extract_history_date(history, "accepted"),
            "received_date": DateExtractor.extract_history_date(history, "received"),
            "revised_date": DateExtractor.extract_history_date(history, "revised"),
            "epub_date": epub_date,
        }
