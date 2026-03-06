"""PubMed Publication Transformer.

See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html

Refactored to use BasePublicationTransformer pattern for consistency
with other publication pipelines (CrossRef, OpenAlex, SemanticScholar).
"""

from __future__ import annotations

__all__ = ["PubMedPublicationTransformer"]


import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.pubmed.extractors import (
    AuthorExtractor,
    DateExtractor,
    PubMedAuthorBlockExtractor,
    PubMedBusinessDataExtractor,
    RawAuthor,
)
from bioetl.application.pipelines.pubmed.transformer_authors_mixin import (
    _PubMedTransformerAuthorsMixin,
)
from bioetl.application.pipelines.pubmed.transformer_dates_mixin import (
    _PubMedTransformerDatesMixin,
)
from bioetl.domain.entities.pubmed import PubMedPublicationEntity
from bioetl.domain.mapping.pubmed_publication import (
    PUBMED_SILVER_EXCLUDED_FIELDS,
    build_pubmed_publication_type_fields,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldRecord, JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        ContractPolicyPort,
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


class PubMedPublicationTransformer(
    _PubMedTransformerAuthorsMixin,
    _PubMedTransformerDatesMixin,
    BasePublicationTransformer,
):
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
    _VALID_DATE_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = (
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
        contract_policy: ContractPolicyPort | None = None,
        author_extractor: AuthorExtractor | None = None,
        date_extractor: DateExtractor | None = None,
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
            contract_policy: Optional pipeline contract policy.
            author_extractor: Optional author extractor dependency.
                If None, defaults to AuthorExtractor().
            date_extractor: Optional date extractor dependency.
                If None, defaults to DateExtractor().

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
            contract_policy=contract_policy,
        )
        self._cached_xml_root = None
        self._author_extractor = author_extractor or AuthorExtractor()
        self._date_extractor = date_extractor or DateExtractor()

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

    def _extract_author_block(
        self, article: ET.Element, raw_author_data: list[RawAuthor]
    ) -> JsonDict:  # Any: untyped PubMed XML/JSON values
        """Extract and process author-related fields from article XML."""
        return PubMedAuthorBlockExtractor.extract(
            article=article,
            raw_author_data=raw_author_data,
            data_normalizer=self._data_normalizer,
            author_extractor=self._author_extractor,
            normalize_author_list=self._data_normalizer.normalize_author_list,
            normalize_author_keys=self._data_normalizer.normalize_author_keys,
            serialize_json_list=self.serialize_json_list,
            build_authors_with_affiliations=self._build_authors_with_affiliations,
            process_structured_affiliations=lambda affiliations: (
                self._process_structured_affiliations(
                    cast(
                        "list[JsonDict]",  # Any: structured affiliation payloads
                        affiliations,
                    )
                )
            ),
        )

    def _extract_business_data(self, record: BronzeRecord) -> GoldRecord:
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
        return PubMedBusinessDataExtractor.extract(
            record=record,
            root=root,
            data_normalizer=self._data_normalizer,
            author_extractor=self._author_extractor,
            serialize_json_list=self.serialize_json_list,
            extract_author_block=self._extract_author_block,
            extract_journal_data=self._extract_journal_data,
            extract_date_data=self._extract_date_data,
            classify_publication_types=self._build_pubmed_classification,
        )

    def _build_pubmed_classification(
        self, pub_types: list[str]
    ) -> dict[str, str | None]:
        """Build publication_type and classification fields for PubMed."""
        return build_pubmed_publication_type_fields(
            pub_types,
            classification=self._classify_publication_type(
                "pubmed",
                raw_types_list=pub_types,
            ),
        )

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

    def entity_to_silver_record(
        self,
        entity: Any,  # Any: generic domain entity; type varies by pipeline
    ) -> GoldRecord:  # Any: generic domain entity
        """Convert Domain Entity to SilverRecord, excluding PubMed-unsupported fields."""
        silver_record = super().entity_to_silver_record(entity)
        for field in PUBMED_SILVER_EXCLUDED_FIELDS:
            silver_record.pop(field, None)
        return silver_record
