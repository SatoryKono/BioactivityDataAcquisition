"""PubMed Publication Transformer.

See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html

Refactored to use BasePublicationTransformer pattern for consistency
with other publication pipelines (CrossRef, OpenAlex, SemanticScholar).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.pubmed.extractors import (
    AbstractExtractor,
    AuthorExtractor,
    ClassificationExtractor,
    DateExtractor,
    IdentifierExtractor,
    RawAuthor,
    StructuredAffiliation,
)
from bioetl.application.pipelines.pubmed.xml_parser import get_text
from bioetl.domain.entities.pubmed import PubMedPublicationEntity
from bioetl.domain.normalization import normalize_pmc_id, parse_page_range
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear, PubMedId

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
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

    # Date validation patterns for ISO date formats (YYYY, YYYY-MM, YYYY-MM-DD).
    # Used to filter out invalid dates like "2024-13-99" or "n/a" before
    # they propagate to _compute_publication_date.
    _VALID_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
        # Full date: YYYY-MM-DD (with valid month 01-12 and day 01-31)
        re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
        # Partial month: YYYY-MM (with valid month 01-12)
        re.compile(r"^\d{4}-(0[1-9]|1[0-2])$"),
        # Partial year: YYYY
        re.compile(r"^\d{4}$"),
    )

    _MONTH_MAP: ClassVar[dict[str, int]] = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def __init__(
        self,
        provider: str = "pubmed",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
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
            silver_filters: Optional filter configuration for Silver layer.
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
            silver_filters=silver_filters,
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
        """Validate raw XML and parse it, caching the root element.

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

    def _is_valid_date_format(self, date_str: str | None) -> bool:
        """Validate that date string matches YYYY, YYYY-MM, or YYYY-MM-DD format."""
        if not date_str:
            return False
        return any(pattern.match(date_str) for pattern in self._VALID_DATE_PATTERNS)

    def _extract_medline_metadata(
        self,
        medline: ET.Element | None,
        pubmed_data: ET.Element | None,
    ) -> dict[str, Any]:
        """Extract MEDLINE-specific metadata."""
        medline_info = medline.find("MedlineJournalInfo") if medline else None
        citation_subsets = (
            [get_text(cs) for cs in medline.findall("CitationSubset")]
            if medline
            else []
        )

        pub_status = self._extract_publication_status(pubmed_data)

        return {
            "nlm_unique_id": (
                get_text(medline_info.find("NlmUniqueID"))
                if medline_info is not None
                else None
            ),
            "citation_subset": (
                ",".join(cs for cs in citation_subsets if cs)
                if citation_subsets
                else None
            ),
            "publication_status": pub_status,
            "country": (
                get_text(medline.find(".//MedlineJournalInfo/Country"))
                if medline
                else None
            ),
        }

    def _extract_publication_status(self, pubmed_data: ET.Element | None) -> str | None:
        """Extract publication status from PubmedData."""
        if pubmed_data is None:
            return None
        pub_status_elem = pubmed_data.find("PublicationStatus")
        return get_text(pub_status_elem) if pub_status_elem is not None else None

    def _extract_counts(
        self,
        article: ET.Element,
        pubmed_data: ET.Element | None,
    ) -> dict[str, int]:
        """Extract grant and reference counts."""
        grant_list = article.find(".//GrantList")
        grant_count = len(grant_list.findall("Grant")) if grant_list is not None else 0

        ref_list = (
            pubmed_data.find("ReferenceList") if pubmed_data is not None else None
        )
        reference_count = (
            len(ref_list.findall(".//Reference")) if ref_list is not None else 0
        )

        return {"grant_count": grant_count, "citations_made": reference_count}

    def _extract_classification_data(
        self, article: ET.Element, medline: ET.Element | None
    ) -> dict[str, Any]:
        """Extract classification-related fields."""
        publication_types = ClassificationExtractor.parse_publication_types(article)
        subject_keywords = ClassificationExtractor.parse_keywords(medline)
        subject_mesh = ClassificationExtractor.parse_mesh_terms(medline)
        chemicals = ClassificationExtractor.parse_chemicals(medline)

        return {
            "publication_types": publication_types,
            "publication_type_list": self.serialize_json_list(publication_types),
            "subject_keywords": subject_keywords,
            "keyword_count": len(subject_keywords) if subject_keywords else 0,
            "subject_mesh": subject_mesh,
            "mesh_heading_count": len(subject_mesh) if subject_mesh else 0,
            "chemicals": chemicals,
            "chemical_count": len(chemicals) if chemicals else 0,
            "gene_symbols": ClassificationExtractor.parse_gene_symbols(medline),
            "databanks": ClassificationExtractor.parse_databanks(medline),
        }

    def _extract_author_block(
        self, article: ET.Element, raw_author_data: list[RawAuthor]
    ) -> dict[str, Any]:
        """Extract and process author-related fields from article XML.

        Uses unified normalization service for authors and affiliations.
        """
        # Normalize author names using unified service
        normalizer = self._data_normalizer
        salt = (
            self._pii_hasher.get_salt() if hasattr(self._pii_hasher, "get_salt") else None
        )

        # Extract author names for hashing
        author_names = (
            [AuthorExtractor().normalize(raw_author_data)] if raw_author_data else []
        )
        # Flatten if normalize returns list
        if author_names and isinstance(author_names[0], list):
            author_names = author_names[0]

        # Use unified normalization (parse + hash + serialize in one call)
        authors_json = normalizer.normalize_author_list(author_names, salt=salt)

        authors_with_affiliations = self._build_authors_with_affiliations(
            raw_author_data
        )

        # Extract affiliations using unified service
        affiliation_strings = normalizer.extract_affiliations_from_authors(
            raw_author_data
        )

        # Normalize affiliations using unified service (already deduplicated & sorted)
        affiliation_list_json = (
            normalizer.normalize_affiliations(affiliation_strings)
            if affiliation_strings
            else None
        )

        # Structured affiliations with identifiers (PubMed-specific)
        structured_affs = AuthorExtractor.parse_structured_affiliations(article)
        processed = self._process_structured_affiliations(structured_affs)

        # Count from parsed JSON
        import json

        author_count = len(json.loads(authors_json)) if authors_json else 0

        return {
            "authors": authors_json,
            "authors_with_affiliations": (
                self.serialize_json_list(authors_with_affiliations)
                if authors_with_affiliations
                else None
            ),
            "affiliation_list": affiliation_list_json,
            "affiliation_structured": self.serialize_json_list(processed),
            "author_count": author_count,
        }

    def _extract_identifiers(self, root: ET.Element) -> dict[str, Any]:
        """Extract and normalize all identifier fields from PubMed XML root."""
        raw_pmid = get_text(root.find(".//PMID"))
        pmid_vo = PubMedId.from_raw(raw_pmid)

        raw_doi = IdentifierExtractor.extract_doi(root)
        doi_vo = DOI.from_raw(raw_doi)

        return {
            "pmid": str(pmid_vo) if pmid_vo else None,
            "doi": str(doi_vo) if doi_vo else None,
            "pii": self._data_normalizer.normalize_to_string(
                IdentifierExtractor.extract_pii(root)
            ),
            "mid": self._data_normalizer.normalize_to_string(
                IdentifierExtractor.extract_mid(root)
            ),
            "publisher_id": self._data_normalizer.normalize_to_string(
                IdentifierExtractor.extract_publisher_id(root)
            ),
            "pmc_id": normalize_pmc_id(IdentifierExtractor.extract_pmc_id(root)),
        }

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract all business fields from PubMed XML.

        Uses the cached XML root from _pre_extract_validation.

        Args:
            record: Raw Bronze record (unused, XML already parsed).

        Returns:
            Dictionary of extracted and normalized fields.

        """
        root = self._cached_xml_root
        if root is None:
            return {"pmid": None}

        identifiers = self._extract_identifiers(root)

        article = root.find(".//Article")
        if article is None:
            return {"pmid": identifiers["pmid"]}

        medline = root.find(".//MedlineCitation")
        pubmed_data = root.find(".//PubmedData")

        raw_author_data = AuthorExtractor().extract(article) or []

        return {
            **identifiers,
            "title": get_text(article.find(".//ArticleTitle")),
            "abstract": self._data_normalizer.strip_html_tags(
                AbstractExtractor.extract_abstract(article)
            ),
            "abstract_structured": AbstractExtractor.is_abstract_structured(article),
            **self._extract_author_block(article, raw_author_data),
            **self._extract_journal_data(article),
            **self._extract_date_data(article, pubmed_data, medline),
            **self._extract_classification_data(article, medline),
            **self._extract_medline_metadata(medline, pubmed_data),
            **self._extract_counts(article, pubmed_data),
            "language": get_text(article.find(".//Language")),
            "_source": "pubmed",
            **self._build_pubmed_classification(
                ClassificationExtractor.parse_publication_types(article),
            ),
            "citations_received": None,
            "is_oa": None,
            "_lookup_method": record.get("_lookup_method", "pmid"),
            "_original_id": record.get("_original_id"),
            "_dq_warn": False,
            "_dq_error": False,
        }

    def _build_pubmed_classification(
        self, pub_types: list[str]
    ) -> dict[str, str | None]:
        """Build publication_type and classification fields for PubMed.

        Joins raw types with ``|`` for the raw ``publication_type`` field,
        then uses the unified classifier to pick the most specific match.

        Args:
            pub_types: List of raw publication type strings from XML.

        Returns:
            Dict with publication_type and the 3 classification fields.

        """
        raw_type = "|".join(pub_types) if pub_types else None
        classification = self._classify_publication_type(
            "pubmed",
            raw_types_list=pub_types,
        )
        return {"publication_type": raw_type, **classification}

    def _process_structured_affiliations(
        self, affiliations: list[StructuredAffiliation]
    ) -> list[dict[str, Any]]:
        """Process structured affiliations with PII handling for emails.

        Email addresses in affiliations are PII and must be hashed before
        storing in Silver layer (RULES.md §5.4).

        Args:
            affiliations: List of structured affiliation dicts.

        Returns:
            List of processed affiliation dicts with hashed emails.
        """
        processed = []
        for aff in affiliations:
            processed_aff: dict[str, Any] = {
                "text": aff.get("text"),
                "identifier": aff.get("identifier"),
                "identifier_source": aff.get("identifier_source"),
                "ror_id": aff.get("ror_id"),
                "grid_id": aff.get("grid_id"),
            }
            # Hash email if present (PII protection)
            email = aff.get("email")
            if email and self._pii_hasher:
                processed_aff["email_hash"] = self._pii_hasher.hash_value(email)
            else:
                processed_aff["email_hash"] = None

            processed.append(processed_aff)
        return processed

    def _build_authors_with_affiliations(
        self, raw_authors: list[RawAuthor]
    ) -> list[dict[str, Any]]:
        """Build structured author-affiliation mapping.

        Links each author to their specific affiliations with identifiers.
        Author names are hashed for PII compliance (RULES.md §5.4).

        Args:
            raw_authors: List of raw author dicts from AuthorExtractor.

        Returns:
            List of author objects with hashed names and affiliations.
        """
        result: list[dict[str, Any]] = []

        for author in raw_authors:
            # Build author name for hashing
            last_name = author.get("last_name")
            initials = author.get("initials")
            fore_name = author.get("fore_name")
            collective = author.get("collective_name")

            # Determine display name
            if last_name:
                if initials:
                    name = f"{last_name}, {initials}"
                elif fore_name:
                    name = f"{last_name}, {fore_name}"
                else:
                    name = last_name
            elif collective:
                name = collective
            else:
                continue  # Skip authors without any name

            # Hash the name for PII compliance
            name_hash = self._pii_hasher.hash_value(name) if self._pii_hasher else None

            # Process affiliations for this author (use pre-computed ror_id/grid_id)
            affiliations: list[dict[str, Any]] = []
            structured_affs = author.get("structured_affiliations") or []

            for aff in structured_affs:
                aff_entry: dict[str, Any] = {
                    "text": aff.get("text"),
                    "ror_id": aff.get("ror_id"),
                    "grid_id": aff.get("grid_id"),
                    "identifier": aff.get("identifier"),
                    "identifier_source": aff.get("identifier_source"),
                }
                affiliations.append(aff_entry)

            result.append(
                {
                    "name_hash": name_hash,
                    "initials": initials,
                    "affiliations": affiliations,
                }
            )

        return result

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
        journal_elem = article.find(".//Journal")
        pages = get_text(article.find(".//Pagination/MedlinePgn"))
        first_page, last_page = parse_page_range(pages)

        if not journal_elem:
            return {
                "journal": None,
                "journal_name_short": None,
                "journal_iso_abbrev": None,
                "journal_issn_type": None,
                "issn": None,
                "volume": None,
                "issue": None,
                "page_range": pages,
                "medline_pgn": pages,
                "page_first": first_page,
                "page_last": last_page,
            }

        journal_issue = journal_elem.find("JournalIssue")
        journal_title = get_text(journal_elem.find("Title"))
        journal_abbrev = get_text(journal_elem.find("ISOAbbreviation"))
        issn_elem = journal_elem.find("ISSN")
        issn = get_text(issn_elem)
        issn_type = issn_elem.get("IssnType") if issn_elem is not None else None

        return {
            "journal": journal_title,
            "journal_name_short": journal_abbrev,
            "journal_iso_abbrev": journal_abbrev,  # Alias for Gold schema
            "journal_issn_type": issn_type,
            "issn": issn,
            "volume": get_text(journal_issue.find("Volume")) if journal_issue else None,
            "issue": get_text(journal_issue.find("Issue")) if journal_issue else None,
            "page_range": pages,
            "medline_pgn": pages,  # Alias for Gold schema
            "page_first": first_page,
            "page_last": last_page,
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
            return self._data_normalizer.normalize_partial_date(pub_date)

        # Priority 3: Construct from year (end of year)
        if year:
            return f"{year}-12-31"

        return None

    def _parse_month_day(
        self, pub_date_node: ET.Element | None
    ) -> tuple[int | None, int | None]:
        """Extract month and day as integers from PubDate node.

        Uses DateExtractor to handle both structured (Year/Month/Day)
        and unstructured (MedlineDate) formats.
        """
        if pub_date_node is None:
            return None, None

        # Use DateExtractor logic to support MedlineDate parsing
        raw_date = DateExtractor().extract(pub_date_node)
        if not raw_date:
            return None, None

        month_text = raw_date.get("month")
        day_text = raw_date.get("day")

        pub_month = self._parse_month(month_text)
        pub_day = int(day_text) if day_text and day_text.isdigit() else None

        return pub_month, pub_day

    def _parse_month(self, month_text: str | None) -> int | None:
        """Convert month text (name or number) to integer."""
        if not month_text:
            return None

        month_lower = month_text.strip().lower()[:3]
        result = self._MONTH_MAP.get(month_lower)
        if result is None and month_text.isdigit():
            result = int(month_text)
        return result

    def _extract_date_data(
        self,
        article: ET.Element,
        pubmed_data: ET.Element | None,
        medline: ET.Element | None,
    ) -> dict[str, Any]:
        """Extract date-related data from article and MedlineCitation XML.

        Validates date formats before use to prevent invalid dates like
        "2024-13-99" or "n/a" from causing inconsistent publication_date
        computation. Invalid dates are set to None.

        Args:
            article: Article XML element.
            pubmed_data: PubmedData XML element (contains History with manuscript dates).
            medline: MedlineCitation XML element (contains DateCompleted/DateRevised).

        Returns:
            Dictionary with all date-related fields.
        """
        journal = article.find(".//Journal")
        journal_issue = journal.find("JournalIssue") if journal else None
        pub_date_node = journal_issue.find("PubDate") if journal_issue else None
        raw_pub_date, raw_year = DateExtractor.extract_date(pub_date_node)

        pub_month, pub_day = self._parse_month_day(pub_date_node)

        _validated_year = self.validate_value_object(
            PublicationYear, raw_year, as_string=False
        )
        validated_year: int | None = (
            int(_validated_year) if _validated_year is not None else None
        )

        raw_epub_date = DateExtractor.extract_article_date(article, "Electronic")

        # Validate date formats before passing to _compute_publication_date.
        # Invalid dates (e.g., "2024-13-99", "n/a") are set to None to ensure
        # _compute_publication_date falls back to the next priority source.
        pub_date = raw_pub_date if self._is_valid_date_format(raw_pub_date) else None
        epub_date = raw_epub_date if self._is_valid_date_format(raw_epub_date) else None

        publication_date = self._compute_publication_date(
            epub_date, pub_date, validated_year
        )

        # Extract MEDLINE indexing dates from MedlineCitation element
        date_completed, _ = (
            DateExtractor.extract_date(medline.find("DateCompleted"))
            if medline is not None
            else (None, None)
        )
        date_revised, _ = (
            DateExtractor.extract_date(medline.find("DateRevised"))
            if medline is not None
            else (None, None)
        )

        return {
            "pub_date": pub_date,
            "pub_month": pub_month,
            "pub_day": pub_day,
            "publication_date": publication_date,
            "publication_year": validated_year,
            # Excluded per user request: accepted_date, received_date, revised_date, epub_date
            "date_completed": date_completed,
            "date_revised": date_revised,
        }

    @staticmethod
    def entity_to_silver_record(entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord, excluding certain fields.

        Overrides base implementation to remove fields not needed for PubMed.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary without excluded fields.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        # Get base silver record
        silver_record = BaseTransformer.entity_to_silver_record(entity)

        # Remove excluded fields (API deprecated or not available)
        silver_record.pop("vernacular_title", None)
        silver_record.pop("epub_date", None)
        silver_record.pop("received_date", None)
        silver_record.pop("revised_date", None)
        silver_record.pop("accepted_date", None)
        silver_record.pop("citations_received", None)

        return silver_record
