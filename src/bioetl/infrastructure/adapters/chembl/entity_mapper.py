"""ChEMBL entity mapping utilities.

Provides entity type to API resource mapping and primary key resolution.
Extracted from chembl/client.py for better separation of concerns.

Architecture Notes:
    Publication entity mappings (publication* → document*) are sourced from
    the centralized domain registry (domain/registry/publication.py).
    This module provides a unified API for all ChEMBL entity types.

    - **Canonical names** (publication*): Use in YAML configs and pipeline code.
    - **API resources** (document*): ChEMBL API implementation details.
      YAML configs MUST NOT use document* directly.

Requirements:
    - ADR-024: Entity naming unification
    - Single source of truth for publication mappings in domain.registry

See Also:
    - domain/registry/publication.py: Publication mapping registry
    - docs/02-architecture/decisions/ADR-024-entity-naming-unification.md
"""

from __future__ import annotations

from bioetl.domain.registry.publication import (
    get_dedup_key_fields,
    get_publication_mapping,
    has_composite_key,
    is_publication_entity,
)

# ChEMBL API base URL
# Note: ChEMBL API no longer supports .json extension - use format=json parameter instead
CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_STATUS_URL = f"{CHEMBL_API_BASE}/status"

# =============================================================================
# Non-Publication Entity Mappings
# =============================================================================
# These are entities that are NOT publication-related.
# Publication entities are managed in domain.registry.publication.

_NON_PUBLICATION_ENTITY_MAPPING: dict[str, str] = {
    "activity": "activity",
    "assay": "assay",
    "assay_parameters": "assay",
    "compound": "molecule",
    "molecule": "molecule",
    "target": "target",
    "target_component": "target_component",
    "cell_line": "cell_line",
    "tissue": "tissue",
    "compound_record": "compound_record",
    "protein_class": "protein_classification",
}

# Plural forms for API response keys (ChEMBL uses irregular plurals)
# Note: Publication plurals are provided by the registry.
_NON_PUBLICATION_ENTITY_PLURAL: dict[str, str] = {
    "activity": "activities",
    "assay": "assays",
    "molecule": "molecules",
    "target": "targets",
    "target_component": "target_components",
    "cell_line": "cell_lines",
    "tissue": "tissues",
    "compound_record": "compound_records",
    "protein_classification": "protein_classifications",
}

# Primary key field overrides by entity type
# Note: Publication PK fields are provided by the registry.
_NON_PUBLICATION_PK_FIELD_OVERRIDES: dict[str, str] = {
    "assay": "assay_chembl_id",
    "assay_parameters": "assay_param_id",
    "molecule": "molecule_chembl_id",
    "compound": "molecule_chembl_id",
    "target": "target_chembl_id",
    "target_component": "component_id",
    "cell_line": "cell_chembl_id",
    "tissue": "tissue_chembl_id",
    "compound_record": "record_id",
    "protein_class": "protein_class_id",
}


class ChemblEntityMapper:
    """Maps entity types to ChEMBL API resources and primary keys.

    This class provides a unified interface for resolving:
    - API resource URLs (e.g., 'publication' → '/document')
    - Response plural keys (e.g., 'publication' → 'documents')
    - Primary key fields (e.g., 'publication' → 'document_chembl_id')

    Publication entity mappings are sourced from the centralized domain registry
    (domain/registry/publication.py), ensuring a single source of truth.

    Note:
        - Use canonical names (publication*) in YAML configs
        - document* names are API-level details and should NOT be used directly
        - Legacy aliases (document*) are supported for backward compatibility
    """

    @staticmethod
    def get_resource_url(entity_type: str) -> str:
        """Get ChEMBL API URL for entity type.

        Args:
            entity_type: Entity type (e.g., 'activity', 'assay', 'publication').
                        Use canonical names from YAML configs.

        Returns:
            Full API URL for the entity resource (without .json extension).

        Raises:
            ValueError: If entity type is unknown.

        Note:
            ChEMBL API no longer supports .json extension.
            Use format=json query parameter instead (added by _build_params).

        Example:
            >>> ChemblEntityMapper.get_resource_url("publication")
            'https://www.ebi.ac.uk/chembl/api/data/document'
        """
        # Check publication registry first (ADR-024)
        pub_mapping = get_publication_mapping(entity_type)
        if pub_mapping is not None:
            return f"{CHEMBL_API_BASE}/{pub_mapping.api_resource}"

        # Check non-publication entities
        resource = _NON_PUBLICATION_ENTITY_MAPPING.get(entity_type)
        if resource is None:
            msg = f"Unknown entity type: {entity_type}"
            raise ValueError(msg)
        return f"{CHEMBL_API_BASE}/{resource}"

    @staticmethod
    def get_direct_record_url(entity_type: str, record_id: str) -> str:
        """Get direct URL for fetching a single record by ID.

        ChEMBL API supports two ways to fetch records:
        1. Filter endpoint: /target?target_chembl_id__in=CHEMBL123
        2. Direct endpoint: /target/CHEMBL123

        The direct endpoint uses different server-side code paths and may work
        when the filter endpoint fails with 500 errors.

        Args:
            entity_type: Entity type (e.g., 'target', 'molecule').
            record_id: The ChEMBL ID of the record (e.g., 'CHEMBL1075105').

        Returns:
            Direct API URL for the single record.

        Example:
            >>> ChemblEntityMapper.get_direct_record_url("target", "CHEMBL1075105")
            'https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL1075105'
        """
        base_url = ChemblEntityMapper.get_resource_url(entity_type)
        return f"{base_url}/{record_id}"

    @staticmethod
    def get_plural_key(entity_type: str) -> str:
        """Get the plural form key for API response parsing.

        Args:
            entity_type: Entity type (e.g., 'activity', 'publication').

        Returns:
            Plural key for extracting records from response.

        Example:
            >>> ChemblEntityMapper.get_plural_key("publication")
            'documents'
        """
        # Check publication registry first (ADR-024)
        pub_mapping = get_publication_mapping(entity_type)
        if pub_mapping is not None:
            return pub_mapping.plural_key

        # Check non-publication entities
        resource = _NON_PUBLICATION_ENTITY_MAPPING.get(entity_type, entity_type)
        return _NON_PUBLICATION_ENTITY_PLURAL.get(resource, resource + "s")

    @staticmethod
    def get_primary_key_field(entity_type: str) -> str:
        """Get the primary key field name for deduplication.

        Args:
            entity_type: Entity type (e.g., 'activity', 'publication').

        Returns:
            Primary key field name.

        Example:
            >>> ChemblEntityMapper.get_primary_key_field("publication")
            'document_chembl_id'
        """
        # Check publication registry first (ADR-024)
        pub_mapping = get_publication_mapping(entity_type)
        if pub_mapping is not None:
            return pub_mapping.primary_key_field

        # Check non-publication entities
        if entity_type in _NON_PUBLICATION_PK_FIELD_OVERRIDES:
            return _NON_PUBLICATION_PK_FIELD_OVERRIDES[entity_type]

        # Default: resource_id pattern
        resource = _NON_PUBLICATION_ENTITY_MAPPING.get(entity_type, entity_type)
        return f"{resource}_id"

    @staticmethod
    def get_dedup_key_fields(entity_type: str) -> tuple[str, ...]:
        """Get the composite key fields for deduplication.

        For entities with composite primary keys (like publication_term),
        returns all fields that together form the unique key.
        For entities with single primary key, returns a tuple with that field.

        Args:
            entity_type: Entity type (e.g., 'publication_term', 'activity').

        Returns:
            Tuple of field names for deduplication.

        Example:
            >>> ChemblEntityMapper.get_dedup_key_fields("publication_term")
            ('document_chembl_id', 'term_type', 'term')
            >>> ChemblEntityMapper.get_dedup_key_fields("activity")
            ('activity_id',)
        """
        # Check publication registry first (ADR-024) - may have composite keys
        pub_fields = get_dedup_key_fields(entity_type)
        if pub_fields is not None:
            return pub_fields

        # Non-publication entities use single primary key
        pk_field = ChemblEntityMapper.get_primary_key_field(entity_type)
        return (pk_field,)

    @staticmethod
    def has_composite_key(entity_type: str) -> bool:
        """Check if entity type has a composite primary key.

        Args:
            entity_type: Entity type to check.

        Returns:
            True if entity uses multiple fields for deduplication.

        Example:
            >>> ChemblEntityMapper.has_composite_key("publication_term")
            True
            >>> ChemblEntityMapper.has_composite_key("activity")
            False
        """
        # Check publication registry; non-publication entities always have single primary key
        return has_composite_key(entity_type)

    @staticmethod
    def get_resource_name(entity_type: str) -> str | None:
        """Get the ChEMBL resource name for entity type.

        Args:
            entity_type: Entity type (e.g., 'activity', 'publication').

        Returns:
            Resource name or None if unknown.

        Example:
            >>> ChemblEntityMapper.get_resource_name("publication")
            'document'
        """
        # Check publication registry first (ADR-024)
        pub_mapping = get_publication_mapping(entity_type)
        if pub_mapping is not None:
            return pub_mapping.api_resource

        return _NON_PUBLICATION_ENTITY_MAPPING.get(entity_type)

    @staticmethod
    def is_known_entity(entity_type: str) -> bool:
        """Check if entity type is known (publication or non-publication).

        Args:
            entity_type: Entity type to check.

        Returns:
            True if entity type is recognized.

        Example:
            >>> ChemblEntityMapper.is_known_entity("publication")
            True
            >>> ChemblEntityMapper.is_known_entity("unknown")
            False
        """
        return (
            is_publication_entity(entity_type)
            or entity_type in _NON_PUBLICATION_ENTITY_MAPPING
        )


# =============================================================================
# Backward Compatibility Alias
# =============================================================================
# Re-export for existing imports (deprecated, use domain.registry directly)

ENTITY_MAPPING: dict[str, str] = {
    **_NON_PUBLICATION_ENTITY_MAPPING,
    # Publication mappings from registry (for backward compatibility)
    "publication": "document",
    "publication_similarity": "document_similarity",
    "publication_term": "document",
    "document": "document",
    "document_similarity": "document_similarity",
    "document_term": "document",
}
