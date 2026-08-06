"""CrossRef Transformer.

Transforms Bronze records to Silver format (Publication entity inflation).
Contains orchestration logic for CrossRef data transformation per Hexagonal Architecture.

This module was refactored from infrastructure/adapters/crossref/mappers.py
to properly separate business logic from infrastructure concerns.

Terminology:
- Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
- All layers use "publication" to refer to scholarly works (articles, preprints, etc.)

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
Uses DefaultDataNormalizer for text normalization (DI pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bioetl.application.pipelines.common.base_publication_transformer import (
    BasePublicationTransformer,
)
from bioetl.application.pipelines.common.blocks import (
    _CrossRefAuthorBlock,
    _CrossRefCoreBlock,
    _CrossRefDateBlock,
    _CrossRefJournalBlock,
    _CrossRefMetadataBlock,
)
from bioetl.application.pipelines.common.publication_blocks import ExtractionBlock
from bioetl.application.pipelines.crossref._business_data_builder import (
    compute_publication_date,
    hash_author_details,
)
from bioetl.domain.entities.crossref import CrossRefPublicationEntity
from bioetl.domain.types import GoldRecord, JsonDict
from bioetl.domain.value_objects.publications import DOI

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord


__all__ = ["CrossRefPublicationTransformer"]


class CrossRefPublicationTransformer(BasePublicationTransformer):
    """Transforms CrossRef bronze records to silver.

    Implements field extraction, normalization, and type coercion
    according to the CrossRef → Publication entity mapping specification.

    Subclasses BasePublicationTransformer to provide:
    - Unified transformation flow via Template Method
    - Pre-extraction DOI validation (raises ValueError if missing)
    - Content hash computation
    - Tracing and metrics observability (O1)

    CrossRef transformer keeps fallback lookup logging enabled for title fallback
    observability in adapter fallback paths.
    """

    DEFAULT_PROVIDER = "crossref"
    DEFAULT_ENTITY_TYPE = "publication"

    @property
    def extraction_blocks(self) -> list[ExtractionBlock]:
        """Declarative blocks for CrossRef extraction pipeline."""
        return [
            _CrossRefCoreBlock(
                validate_doi=self._validate_doi,
                classify_pub_type=lambda raw_type: self._classify_publication_type(
                    "crossref", raw_type=raw_type
                ),
                serialize_json_list=self.serialize_json_list,
            ),
            _CrossRefJournalBlock(),
            _CrossRefMetadataBlock(
                serialize_json=self.serialize_json,
                serialize_json_list=self.serialize_json_list,
            ),
            _CrossRefDateBlock(
                validate_publication_year=self._validate_publication_year
            ),
            _CrossRefAuthorBlock(
                data_normalizer=self._data_normalizer,
                hash_pii_value=self.hash_pii_value,
                serialize_json=self.serialize_json,
                serialize_json_list=self.serialize_json_list,
            ),
        ]

    def _validate_doi(self, raw: object) -> str | None:
        """Validate DOI and return canonical string form."""
        value = self.validate_value_object(DOI, raw)
        return value if isinstance(value, str) else None

    def _validate_publication_year(self, raw: object) -> int | None:
        """Validate publication year and return integer value."""
        return self._validate_publication_year_value(raw)

    @override
    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for CrossRef publications.

        Returns:
            'doi' - the CrossRef-specific identifier field.

        """
        return "doi"

    @override
    def _get_entity_class(self) -> type[CrossRefPublicationEntity]:
        """Return the domain entity class for CrossRef publications.

        Returns:
            CrossRefPublicationEntity class.

        """
        return CrossRefPublicationEntity

    @override
    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate DOI exists and is well-formed before extraction.

        CrossRef publications require DOI as mandatory identifier.
        Both missing and malformed DOIs result in record rejection,
        as DOI is the primary identifier for entity_id computation.

        Raises ValueError (caught by BaseTransformer.transform).

        Args:
            context: Pipeline context (unused).
            record: Raw Bronze record from CrossRef API.
            index: Sequential index (unused).

        Raises:
            ValueError: If DOI field is missing, empty, or malformed.

        """
        raw_doi = record.get("DOI")
        if not raw_doi:
            raise ValueError("DOI is required for CrossRef Publication")

        # Cast to str for type safety (API always returns string DOIs)
        raw_doi_str = str(raw_doi)

        # Validate DOI format using Value Object
        # This catches malformed DOIs like "invalid", "10.1234", etc.
        doi_vo = DOI.from_raw(raw_doi_str)
        if doi_vo is None:
            raise ValueError(f"Invalid DOI format: {raw_doi}")

    def _hash_author_details(
        self,
        author_details: list[JsonDict],  # Any: raw CrossRef API JSON fragments
    ) -> list[JsonDict]:
        """Compatibility seam for tests and callers expecting transformer helper."""
        return hash_author_details(
            author_details,
            hash_pii_value=self.hash_pii_value,
        )

    def _compute_publication_date(
        self,
        published_print: str | None,
        published_online: str | None,
    ) -> str | None:
        """Compatibility seam for date-selection tests and legacy callers."""
        return compute_publication_date(published_print, published_online)

    @override
    def _should_log_fallback_lookup(self) -> bool:
        """Enable fallback lookup logging for CrossRef.

        CrossRef supports title-based fallback when DOI lookup fails (404).
        Adapter uses CrossRefTitleFallbackHandler for three-phase lookup:
        1. DOI batch fetch
        2. Title fallback for unresolved DOIs
        3. Title-only lookup for entries without DOIs

        Returns:
            True - log fallback lookups for observability.

        """
        return True

        # Any: generic domain entity; type varies by pipeline

    @override
    def entity_to_silver_record(
        self,
        entity: Any,  # Any: domain entity dataclass; concrete type varies by pipeline subclass
    ) -> GoldRecord:
        """Convert Domain Entity to SilverRecord, preserving base schema fields.

        Overrides base implementation to handle ISSN list conversion.
        Note: Fields like pmid, pmc_id, abstract, affiliation_list are kept
        with None values to satisfy PublicationBaseSchema inheritance requirement.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary with all base schema fields.

        """
        # Get base silver record
        silver_record = super().entity_to_silver_record(entity)

        # Note: Do NOT remove pmid, pmc_id, abstract, affiliation_list
        # These fields inherit from PublicationBaseSchema and must exist in DataFrame
        # even if set to None (Pandera requires columns to exist, not just be nullable)

        # Convert ISSN list to scalar + JSON array (unification with other providers)
        issn_raw = silver_record.get("issn")
        if isinstance(issn_raw, list):
            silver_record["issn"] = issn_raw[0] if issn_raw else None
            silver_record["issn_list"] = (
                self.serialize_json_list(issn_raw) if issn_raw else None
            )
        elif isinstance(issn_raw, str) and "," in issn_raw:
            issn_values = [
                value.strip() for value in issn_raw.split(",") if value.strip()
            ]
            silver_record["issn"] = issn_values[0] if issn_values else None
            silver_record["issn_list"] = (
                self.serialize_json_list(issn_values) if issn_values else None
            )
        else:
            silver_record.setdefault("issn_list", None)

        return silver_record

    # Constructor is inherited from BasePublicationTransformer and uses
    # DEFAULT_PROVIDER / DEFAULT_ENTITY_TYPE — no import-time __init__ mutation.
