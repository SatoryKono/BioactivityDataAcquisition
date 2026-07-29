# mypy: disable-error-code="import-untyped"
# Host attrs/methods provided by concrete composition.
"""PubMed publication transformer."""

from __future__ import annotations

__all__ = ["PubMedPublicationTransformer"]

import re
import xml.etree.ElementTree as ET  # nosec B405
from typing import TYPE_CHECKING, Any, ClassVar, cast, override

import defusedxml.ElementTree as defused_ET

from bioetl.application.core.base_transformer import TransformerDependencyContext
from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.common.publication_blocks import ExtractionBlock
from bioetl.application.pipelines.common.publication_transformer_context import (
    publication_transformer_kwargs,
)
from bioetl.application.pipelines.pubmed._block_helpers import (
    build_authors_with_affiliations,
    compute_publication_date,
    extract_date_data,
    extract_journal_data,
    is_valid_date_format,
    process_structured_affiliations,
)
from bioetl.application.pipelines.pubmed.blocks import (
    _PubMedAuthorBlock,
    _PubMedClassificationBlock,
    _PubMedCoreBlock,
    _PubMedDateBlock,
    _PubMedIdentifierBlock,
    _PubMedJournalBlock,
    _PubMedMetricsBlock,
)
from bioetl.application.pipelines.pubmed.extractors import (
    AuthorExtractor,
    DateExtractor,
    RawAuthor,
)
from bioetl.domain.entities.pubmed import PubMedPublicationEntity
from bioetl.domain.mapping.pubmed_publication import (
    PUBMED_SILVER_EXCLUDED_FIELDS,
    build_pubmed_publication_type_fields,
)
from bioetl.domain.types import GoldRecord, JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.types import BronzeRecord


class PubMedPublicationTransformer(BasePublicationTransformer):
    """Transformer for PubMed publication records."""

    _cached_xml_root: ET.Element | None

    _VALID_DATE_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = (
        re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
        re.compile(r"^\d{4}-(0[1-9]|1[0-2])$"),
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
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        dependencies: TransformerDependencyContext | None = None,
        **legacy_collaborators: object,
    ) -> None:
        """Initialize PubMed publication transformer."""
        allowed = {
            "tracer",
            "metrics",
            "identity_service",
            "pii_hasher",
            "author_extractor",
            "date_extractor",
        }
        unexpected = sorted(k for k in legacy_collaborators if k not in allowed)
        if unexpected:
            raise TypeError(
                "PubMedPublicationTransformer() got unexpected keyword argument(s): "
                + ", ".join(unexpected)
            )
        init_locals: dict[str, object] = {
            "entity_type": entity_type,
            "silver_filters": silver_filters,
            "gold_filters": gold_filters,
            "dependencies": dependencies,
            "tracer": legacy_collaborators.get("tracer"),
            "metrics": legacy_collaborators.get("metrics"),
            "identity_service": legacy_collaborators.get("identity_service"),
            "pii_hasher": legacy_collaborators.get("pii_hasher"),
        }
        super().__init__(provider, **publication_transformer_kwargs(init_locals))
        self._cached_xml_root = None
        author_extractor = legacy_collaborators.get("author_extractor")
        date_extractor = legacy_collaborators.get("date_extractor")
        self._author_extractor = (
            author_extractor
            if isinstance(author_extractor, AuthorExtractor)
            else AuthorExtractor()
        )
        self._date_extractor = (
            date_extractor
            if isinstance(date_extractor, DateExtractor)
            else DateExtractor()
        )

    @override
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
            self._cached_xml_root = defused_ET.fromstring(raw_xml)
        except (
            ET.ParseError,
            cast(type[BaseException], getattr(defused_ET, "EntitiesForbidden", Exception)),
        ) as e:
            context.logger.warning(
                "XML_parse_error",
                error=str(e),
                pmid=record.get("pmid"),
            )
            raise ValueError(f"XML parse error: {e}") from e

    @property
    def extraction_blocks(self) -> list[ExtractionBlock]:
        """Declarative extraction blocks for PubMed XML pipeline."""

        def resolve_cached_root() -> ET.Element | None:
            return self._cached_xml_root

        return [
            _PubMedIdentifierBlock(
                data_normalizer=self._data_normalizer,
                root_resolver=resolve_cached_root,
            ),
            _PubMedCoreBlock(
                data_normalizer=self._data_normalizer,
                root_resolver=resolve_cached_root,
            ),
            _PubMedAuthorBlock(
                author_extractor=self._author_extractor,
                data_normalizer=self._data_normalizer,
                pii_hasher=self._pii_hasher,
                serialize_json_list=self.serialize_json_list,
                normalize_author_list=self._data_normalizer.normalize_author_list,
                normalize_author_keys=self._data_normalizer.normalize_author_keys,
                root_resolver=resolve_cached_root,
            ),
            _PubMedJournalBlock(
                serialize_json_list=self.serialize_json_list,
                root_resolver=resolve_cached_root,
            ),
            _PubMedDateBlock(
                extract_date_data=self._extract_date_data,
                root_resolver=resolve_cached_root,
            ),
            _PubMedClassificationBlock(
                serialize_json_list=self.serialize_json_list,
                classify_publication_types=self._build_pubmed_classification,
                root_resolver=resolve_cached_root,
            ),
            _PubMedMetricsBlock(root_resolver=resolve_cached_root),
        ]

    def _extract_author_block(
        self, article: ET.Element, raw_author_data: list[RawAuthor]
    ) -> JsonDict:  # Any: untyped PubMed XML/JSON values
        """Extract and process author-related fields from article XML."""
        author_names = self._author_extractor.normalize(raw_author_data)
        authors_with_affiliations = build_authors_with_affiliations(
            raw_author_data,
            self._pii_hasher,
        )
        affiliation_strings = self._data_normalizer.extract_affiliations_from_authors(
            cast("list[JsonDict]", raw_author_data)
        )
        structured_affiliations = process_structured_affiliations(
            self._author_extractor.parse_structured_affiliations(article),
            self._pii_hasher,
        )
        return {
            "authors": self._data_normalizer.normalize_author_list(author_names),
            "author_keys": self._data_normalizer.normalize_author_keys(author_names),
            "authors_with_affiliations": self.serialize_json_list(
                authors_with_affiliations
            )
            if authors_with_affiliations
            else None,
            "affiliation_list": self._data_normalizer.normalize_affiliations(
                affiliation_strings
            )
            if affiliation_strings
            else None,
            "affiliation_structured": self.serialize_json_list(structured_affiliations),
            "author_count": len(author_names),
        }

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

    def _validate_publication_year(self, raw: object) -> int | None:
        """Validate publication year and return integer value."""
        return self._validate_publication_year_value(raw)

    def _is_valid_date_format(self, date_str: str | None) -> bool:
        """Validate PubMed date strings against supported ISO-like formats."""
        return is_valid_date_format(date_str, self._VALID_DATE_PATTERNS)

    def _compute_publication_date(
        self,
        epub_date: str | None,
        pub_date: str | None,
        year: int | None,
    ) -> str | None:
        """Compute unified publication date using the shared helper seam."""
        return compute_publication_date(
            data_normalizer=self._data_normalizer,
            epub_date=epub_date,
            pub_date=pub_date,
            year=year,
        )

    def _extract_journal_data(
        self,
        article: ET.Element,
    ) -> dict[str, object]:
        """Extract journal-related data from article XML."""
        return extract_journal_data(article)

    def _extract_date_data(
        self,
        article: ET.Element,
        pubmed_data: ET.Element | None,
        medline: ET.Element | None,
    ) -> dict[str, object]:
        """Extract normalized date fields from article and Medline XML."""
        return extract_date_data(
            article=article,
            pubmed_data=pubmed_data,
            medline=medline,
            date_extractor=self._date_extractor,
            data_normalizer=self._data_normalizer,
            validate_publication_year=self._validate_publication_year,
            valid_date_patterns=self._VALID_DATE_PATTERNS,
            month_map=self._MONTH_MAP,
        )

    @override
    def _get_primary_id_field(self) -> str:
        """Return the PubMed primary identifier field."""
        return "pmid"

    @override
    def _get_entity_class(self) -> type[BaseEntity]:
        """Return the PubMed domain entity class."""
        return cast("type[BaseEntity]", PubMedPublicationEntity)

    @override
    def _should_log_fallback_lookup(self) -> bool:
        """Enable fallback lookup logging for PubMed."""
        return True

    @override
    def entity_to_silver_record(
        self,
        entity: Any,  # Any: generic domain entity; type varies by pipeline
    ) -> GoldRecord:  # Any: generic domain entity
        """Convert Domain Entity to SilverRecord, excluding PubMed-unsupported fields.

        Args:
            entity: Dataclass domain entity to convert to a Silver record dict.

        Returns:
            SilverRecord dictionary with PubMed-unsupported fields removed.
        """
        silver_record = super().entity_to_silver_record(entity)
        for field in PUBMED_SILVER_EXCLUDED_FIELDS:
            silver_record.pop(field, None)
        return silver_record
