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

from bioetl.application.core.base_transformer import TransformationError
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
from bioetl.domain.mapping.publication_type_mapping import normalize_publication_type
from bioetl.domain.services import IdentityService
from bioetl.domain.types import BronzeRecord, GoldRecord
from bioetl.domain.value_objects import DOI, PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        ContractPolicyPort,
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import PrimaryId, SilverRecord


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
    primary_id_field = "publication_id"

    def __init__(
        self,
        provider: str = "chembl",
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: ContractPolicyPort | None = None,
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
            contract_policy: Optional pipeline contract policy.

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
            contract_policy=contract_policy,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Handle legacy and unified publication ID fields."""
        primary_id = record.get(self.primary_id_field) or record.get(
            "document_chembl_id"
        )
        if not primary_id:
            raise TransformationError(
                "Missing required field: publication_id or document_chembl_id",
                field=self.primary_id_field,
            )

        # 2. Generate entity ID using IdentityService
        entity_id = self.compute_entity_id(
            source_id=str(primary_id),
            record={self.primary_id_field: str(primary_id)},
        )

        # 3. Extract business data (delegated to subclass)
        business_data = self._extract_business_data(record, primary_id)

        # 4. Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 5. Create domain entity
        entity = self._create_entity(
            self.entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 6. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

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

        # Normalize publication_type to canonical kebab-case
        data["publication_type"] = normalize_publication_type(
            data.get("publication_type")
        )

        # Normalize text fields using DataNormalizationService
        # Level A: Bronze → Silver basic normalization
        # - HTML cleanup, whitespace, unicode NFC, trim
        normalizer = self._data_normalizer
        data["title"] = normalizer.normalize_title(data.get("title"))
        data["abstract"] = normalizer.normalize_abstract(data.get("abstract"))

        # Validate DOI using Value Object (returns None for invalid/empty)
        data["publication_pmid"] = data.get("publication_pmid") or PMID(
            record.get("pmid")
        )
        doi = DOI.from_raw(data.get("publication_doi"))
        data["publication_doi"] = str(doi) if doi else None
        data["doi"] = data["publication_doi"]

        # Validate year using PublicationYear Value Object
        # Note: field_specs already maps year → publication_year
        data["publication_year"] = self.validate_value_object(
            PublicationYear, data.get("publication_year"), as_string=False
        )
        data["pmid"] = data.get("publication_pmid")

        # Normalize authors using unified service (RULES.md §5.4)
        # ChEMBL authors is a concatenated string - parse, hash, serialize to JSON
        # Uses normalize_author_list() for unified cross-provider handling
        raw_authors = data.get("authors")
        data["authors"] = normalizer.normalize_author_list(raw_authors)
        data["author_keys"] = normalizer.normalize_author_keys(raw_authors)

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

        # Unified publication fields (ChEMBL only provides citation_count)
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

        # Any: generic domain entity; type varies by pipeline

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
