"""ChEMBL Publication Transformer.

Transforms Bronze records to Silver format (ChemblPublication entity inflation).
Uses declarative field_specs DSL for mapping.

.. versionchanged:: 2.0.0
    Uses ChemblPublication (canonical) instead of Document (deprecated).

.. versionchanged:: 2.1.0
    Uses DataNormalizationService for text normalization (DI pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.field_specs import (
    PMID,
    FieldGroup,
    FieldSpec,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import ChemblPublication
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


# Declarative field groups for ChemblPublication entity
_PUBLICATION_IDS = FieldGroup(
    name="publication_ids",
    fields=(
        # Rename pubmed_id -> pmid for cross-provider consistency (PMID standardization)
        FieldSpec("pubmed_id", target="pmid", converter=PMID),
        *simple_fields("doi"),
        # Note: patent_id excluded - not needed for unified publication schema
    ),
)

_CORE_METADATA = FieldGroup(
    name="core_metadata",
    fields=simple_fields("title", "authors", "abstract"),
)

_PUBLICATION_TYPE = FieldGroup(
    name="publication_type",
    fields=(
        # Unified field: doc_type → publication_type
        FieldSpec("doc_type", target="publication_type"),
    ),
)

_JOURNAL_INFO = FieldGroup(
    name="journal_info",
    fields=(
        *simple_fields(
            "journal",
            "volume",
            "issue",
        ),
        # Unified pagination fields
        FieldSpec("first_page", target="page_first"),
        FieldSpec("last_page", target="page_last"),
        # Unified temporal field
        FieldSpec("year", target="publication_year", converter=int),
    ),
)

_SOURCE_INFO = FieldGroup(
    name="source_info",
    fields=int_fields("src_id"),
)

# All field groups for ChemblPublication entity
_PUBLICATION_GROUPS: tuple[FieldGroup, ...] = (
    _PUBLICATION_IDS,
    _CORE_METADATA,
    _PUBLICATION_TYPE,
    _JOURNAL_INFO,
    _SOURCE_INFO,
)


class PublicationTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze publication records to silver.

    Uses ChemblPublication entity (canonical name).
    Uses DataNormalizationService for text normalization (DI pattern).

    .. versionchanged:: 2.0.0
        Renamed from DocumentTransformer to PublicationTransformer (ADR-024).
    """

    entity_class = ChemblPublication
    primary_id_field = "document_chembl_id"

    def __init__(
        self,
        provider: str = "chembl",
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: GoldFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize ChEMBL Publication transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.
            entity_type: Entity type for metrics labels. If None, derived from
                entity_class name.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            silver_filters: Optional filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Optional data normalization service for text normalization.

        """
        super().__init__(
            provider=provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract ChemblPublication business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated document_chembl_id value.

        Returns:
            Dictionary of ChemblPublication business fields.

        """
        # Extract base fields using declarative DSL
        data = {
            "document_chembl_id": str(primary_id),
            **map_field_groups(record, _PUBLICATION_GROUPS),
        }

        # Strip HTML from abstract field using DataNormalizationService
        normalizer = self._data_normalizer
        data["abstract"] = normalizer.strip_html_tags(data.get("abstract"))

        # Validate DOI using Value Object (returns None for invalid/empty)
        doi = DOI.from_raw(data.get("doi"))
        data["doi"] = str(doi) if doi else None

        # Validate year using PublicationYear Value Object
        # Note: field_specs already maps year → publication_year
        data["publication_year"] = self.validate_value_object(
            PublicationYear, data.get("publication_year"), as_string=False
        )

        # Hash PII field (RULES.md §5.4)
        # ChEMBL authors is a concatenated string - parse to list, hash, serialize to JSON
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = data.get("authors")
        if raw_authors:
            author_list = normalizer.parse_authors_to_list(raw_authors)
            hashed_authors = self.hash_pii_list(author_list) or []
            data["authors"] = self.serialize_json_list(hashed_authors)
        else:
            data["authors"] = None

        # Lookup metadata (direct extraction, no enrichment)
        data["_lookup_method"] = "direct"
        data["_original_id"] = str(primary_id)

        # ChEMBL release metadata (nested object from API)
        release_info = record.get("chembl_release")
        if release_info and isinstance(release_info, dict):
            data["chembl_release"] = release_info.get("chembl_release")
            data["creation_date"] = release_info.get("creation_date")
        else:
            data["chembl_release"] = None
            data["creation_date"] = None

        # System field: data source identifier
        data["_source"] = "chembl"

        # Унифицированные поля публикации (в ChEMBL есть только citation_count)
        citation_count = record.get("citation_count")
        if citation_count is not None:
            try:
                data["citations_received"] = int(str(citation_count))
            except (TypeError, ValueError):
                data["citations_received"] = None
        else:
            data["citations_received"] = None
        data["citations_made"] = None

        # Fields from PublicationBaseSchema that ChEMBL API doesn't provide
        data["pmc_id"] = None
        data["affiliation_list"] = None
        data["author_orcids"] = None
        data["publication_date"] = None
        data["language"] = None
        data["is_oa"] = None
        data["oa_status"] = None

        # DQ flags (default: no warnings or errors)
        data["_dq_warn"] = False
        data["_dq_error"] = False

        return data

    @staticmethod
    def entity_to_silver_record(entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord.

        ChEMBL-specific fields are set to None in _extract_business_data() for
        fields not available from ChEMBL API (pmc_id, affiliation_list, etc.).
        These None values satisfy the PublicationBaseSchema inheritance requirement.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord with all PublicationBaseSchema fields (ChEMBL-unavailable
            fields are None).

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        # Get base silver record (includes all fields with None values)
        silver_record = BaseTransformer.entity_to_silver_record(entity)

        # Remove fields not in unified publication schema (ChEMBL-specific exclusions)
        silver_record.pop("issn", None)
        silver_record.pop("publisher", None)
        silver_record.pop("oa_status", None)

        # Note: pmc_id, affiliation_list, author_orcids, publication_date, language,
        # and is_oa are kept (with None values) to satisfy PublicationBaseSchema

        return silver_record
