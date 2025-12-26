"""ChEMBL entity mapping utilities.

Provides entity type to API resource mapping and primary key resolution.
Extracted from chembl/client.py for better separation of concerns.
"""

from __future__ import annotations

# ChEMBL API base URL
CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_STATUS_URL = f"{CHEMBL_API_BASE}/status.json"

# Entity type to ChEMBL resource mapping
ENTITY_MAPPING: dict[str, str] = {
    "activity": "activity",
    "assay": "assay",
    "compound": "molecule",
    "molecule": "molecule",
    "target": "target",
    "target_component": "target_component",
    "document": "document",
    "cell_line": "cell_line",
    "tissue": "tissue",
}

# Plural forms for API response keys (ChEMBL uses irregular plurals)
ENTITY_PLURAL: dict[str, str] = {
    "activity": "activities",
    "assay": "assays",
    "molecule": "molecules",
    "target": "targets",
    "target_component": "target_components",
    "document": "documents",
    "cell_line": "cell_lines",
    "tissue": "tissues",
}

# Primary key field overrides by entity type
PK_FIELD_OVERRIDES: dict[str, str] = {
    "assay": "assay_chembl_id",
    "molecule": "molecule_chembl_id",
    "compound": "molecule_chembl_id",
    "document": "document_chembl_id",
    "target": "target_chembl_id",
    "target_component": "component_id",
    "cell_line": "cell_chembl_id",
    "tissue": "tissue_chembl_id",
}


class ChemblEntityMapper:
    """Maps entity types to ChEMBL API resources and primary keys."""

    @staticmethod
    def get_resource_url(entity_type: str) -> str:
        """Get ChEMBL API URL for entity type.

        Args:
            entity_type: Entity type (e.g., 'activity', 'assay', 'compound')

        Returns:
            Full API URL for the entity resource

        Raises:
            ValueError: If entity type is unknown
        """
        resource = ENTITY_MAPPING.get(entity_type)
        if resource is None:
            msg = f"Unknown entity type: {entity_type}"
            raise ValueError(msg)
        return f"{CHEMBL_API_BASE}/{resource}.json"

    @staticmethod
    def get_plural_key(entity_type: str) -> str:
        """Get the plural form key for API response parsing.

        Args:
            entity_type: Entity type

        Returns:
            Plural key for extracting records from response
        """
        resource = ENTITY_MAPPING.get(entity_type, entity_type)
        return ENTITY_PLURAL.get(resource, resource + "s")

    @staticmethod
    def get_primary_key_field(entity_type: str) -> str:
        """Get the primary key field name for deduplication.

        Args:
            entity_type: Entity type

        Returns:
            Primary key field name
        """
        if entity_type in PK_FIELD_OVERRIDES:
            return PK_FIELD_OVERRIDES[entity_type]
        # Default: resource_id pattern
        resource = ENTITY_MAPPING.get(entity_type, entity_type)
        return f"{resource}_id"

    @staticmethod
    def get_resource_name(entity_type: str) -> str | None:
        """Get the ChEMBL resource name for entity type.

        Args:
            entity_type: Entity type

        Returns:
            Resource name or None if unknown
        """
        return ENTITY_MAPPING.get(entity_type)
