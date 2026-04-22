"""ChEMBL Publication Transformer.

Transforms Bronze records to Silver format (ChemblPublication entity inflation).
Uses declarative field_specs DSL for mapping.

.. versionchanged:: 2.0.0
    Uses ChemblPublication (canonical) instead of Document (deprecated).

.. versionchanged:: 2.1.0
    Uses DataNormalizationService for text normalization (DI pattern).
"""

from __future__ import annotations

__all__ = ["PublicationTransformer"]


from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    TransformationError,
    TransformerDependencyContext,
)
from bioetl.application.core.field_specs import (
    INT,
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
from bioetl.domain.mapping.publication_type_classification import (
    build_publication_type_classification_payload,
)
from bioetl.domain.types import BronzeRecord, GoldRecord
from bioetl.domain.value_objects import DOI, PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import PrimaryId


# Declarative field groups for ChemblPublication entity
_PUBLICATION_IDS = FieldGroup(
    name="publication_ids",
    fields=(
        # Rename pubmed_id -> pmid for cross-provider consistency (PMID standardization)
        FieldSpec("pubmed_id", target="publication_pmid", converter=PMID),
        FieldSpec("doi", target="publication_doi"),
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
        FieldSpec("year", target="publication_year", converter=INT),
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
    primary_id_field = "publication_id"

    def __init__(
        self,
        provider: str = "chembl",
        entity_type: str | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize ChEMBL Publication transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.
            entity_type: Entity type for metrics labels. If None, derived from
                entity_class name.
            silver_filters: Optional filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            dependencies: Explicit collaborator bundle.

        """
        super().__init__(
            provider=provider,
            entity_type=entity_type,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            dependencies=dependencies,
        )

    def _resolve_primary_id(self, record: BronzeRecord) -> PrimaryId:
        """Handle legacy and unified publication ID fields."""
        primary_id = record.get(self.primary_id_field) or record.get(
            "document_chembl_id"
        )
        if not primary_id:
            raise TransformationError(
                "Missing required field: publication_id or document_chembl_id",
                field=self.primary_id_field,
            )
        return cast("PrimaryId", primary_id)

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> GoldRecord:
        """Extract ChemblPublication business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated publication_id value.

        Returns:
            Dictionary of ChemblPublication business fields.

        """
        # Extract base fields using declarative DSL
        data = {
            "publication_id": str(primary_id),
            **map_field_groups(record, _PUBLICATION_GROUPS),
        }
        self._normalize_publication_identity(data, record)
        self._normalize_publication_text(data)
        self._normalize_publication_authors(data)
        self._apply_release_metadata(data, record)
        self._apply_publication_defaults(data, primary_id, record)
        return data

        # Any: generic domain entity; type varies by pipeline

    def _normalize_publication_identity(
        self,
        data: GoldRecord,
        record: BronzeRecord,
    ) -> None:
        """Normalize publication identifiers and value-object backed fields."""
        raw_publication_type = data.get("publication_type")
        data.update(
            build_publication_type_classification_payload(
                "chembl",
                raw_type=str(raw_publication_type)
                if raw_publication_type is not None
                else None,
                raw_field_name="publication_type",
            )
        )
        data["publication_pmid"] = data.get("publication_pmid") or PMID(
            record.get("pmid")
        )
        doi = DOI.from_raw(data.get("publication_doi"))
        data["publication_doi"] = str(doi) if doi else None
        data["doi"] = data["publication_doi"]
        data["publication_year"] = self.validate_value_object(
            PublicationYear, data.get("publication_year"), as_string=False
        )
        data["pmid"] = data.get("publication_pmid")

    def _normalize_publication_text(self, data: GoldRecord) -> None:
        """Apply Level-A text normalization for title and abstract fields."""
        normalizer = self._data_normalizer
        data["title"] = normalizer.normalize_title(data.get("title"))
        data["abstract"] = normalizer.normalize_abstract(data.get("abstract"))

    def _normalize_publication_authors(self, data: GoldRecord) -> None:
        """Normalize ChEMBL author strings into unified list/key representations."""
        raw_authors = data.get("authors")
        normalizer = self._data_normalizer
        data["authors"] = normalizer.normalize_author_list(raw_authors)
        data["author_keys"] = normalizer.normalize_author_keys(raw_authors)

    def _apply_release_metadata(
        self,
        data: GoldRecord,
        record: BronzeRecord,
    ) -> None:
        """Copy nested ChEMBL release metadata into the business payload."""
        release_info = record.get("chembl_release")
        if release_info and isinstance(release_info, dict):
            data["chembl_release"] = release_info.get("chembl_release")
            data["creation_date"] = release_info.get("creation_date")
            return
        data["chembl_release"] = None
        data["creation_date"] = None

    def _apply_publication_defaults(
        self,
        data: GoldRecord,
        primary_id: PrimaryId,
        record: BronzeRecord,
    ) -> None:
        """Populate default metadata, citations, and missing publication fields."""
        data["_lookup_method"] = "direct"
        data["_original_id"] = str(primary_id)
        data["_source"] = "chembl"
        data["citations_received"] = self._parse_citation_count(
            record.get("citation_count")
        )
        data["citations_made"] = None
        data["pmc_id"] = None
        data["affiliation_list"] = None
        data["author_orcids"] = None
        data["publication_date"] = None
        data["language"] = None
        data["is_oa"] = None
        data["oa_status"] = None
        data["_dq_warn"] = False
        data["_dq_error"] = False

    @staticmethod
    def _parse_citation_count(value: object) -> int | None:
        """Parse the optional citation count into an integer when possible."""
        if value is None:
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    def entity_to_silver_record(
        self,
        entity: Any,  # Any: generic domain entity; type varies by pipeline
    ) -> GoldRecord:  # Any: generic domain entity
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
        # Get base silver record (includes all fields with None values)
        silver_record = super().entity_to_silver_record(entity)

        # Remove fields not in unified publication schema (ChEMBL-specific exclusions)
        silver_record.pop("issn", None)
        silver_record.pop("publisher", None)
        silver_record.pop("oa_status", None)

        # Note: pmc_id, affiliation_list, author_orcids, publication_date, language,
        # and is_oa are kept (with None values) to satisfy PublicationBaseSchema

        return silver_record
