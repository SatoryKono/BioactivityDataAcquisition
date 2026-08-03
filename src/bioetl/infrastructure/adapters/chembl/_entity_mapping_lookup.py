"""Internal lookup helpers for ChEMBL entity mapping."""

from __future__ import annotations

from bioetl.domain.registry.publication import (
    get_dedup_key_fields,
    get_publication_mapping,
    has_composite_key,
    is_publication_entity,
)

__all__ = [
    "build_legacy_entity_mapping",
    "has_entity_composite_key",
    "is_known_entity_type",
    "resolve_dedup_key_fields",
    "resolve_plural_key",
    "resolve_primary_key_field",
    "resolve_resource_name",
]


_NON_PUBLICATION_ENTITY_MAPPING: dict[str, str] = {
    "activity": "activity",
    "assay": "assay",
    "assay_parameters": "assay",
    "compound": "molecule",
    "molecule": "molecule",
    "target": "target",
    "target_component": "target_component",
    "cell_line": "cell_line",
    "subcellular_fraction": "assay",
    "tissue": "tissue",
    "compound_record": "compound_record",
    "protein_class": "protein_classification",
}

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

_NON_PUBLICATION_PK_FIELD_OVERRIDES: dict[str, str] = {
    "assay": "assay_id",
    "assay_parameters": "assay_param_id",
    "molecule": "molecule_id",
    "compound": "molecule_id",
    "target": "target_id",
    "target_component": "component_id",
    "cell_line": "cell_id",
    "subcellular_fraction": "assay_id",
    "tissue": "tissue_id",
    "compound_record": "record_id",
    "protein_class": "protein_class_id",
}


def resolve_resource_name(entity_type: str) -> str | None:
    """Resolve ChEMBL API resource name for an entity type."""
    pub_mapping = get_publication_mapping(entity_type)
    if pub_mapping is not None:
        return str(pub_mapping.api_resource)
    return _NON_PUBLICATION_ENTITY_MAPPING.get(entity_type)


def resolve_plural_key(entity_type: str) -> str:
    """Resolve API response plural key for an entity type."""
    pub_mapping = get_publication_mapping(entity_type)
    if pub_mapping is not None:
        return str(pub_mapping.plural_key)
    resource = _NON_PUBLICATION_ENTITY_MAPPING.get(entity_type, entity_type)
    return _NON_PUBLICATION_ENTITY_PLURAL.get(resource, resource + "s")


def resolve_primary_key_field(entity_type: str) -> str:
    """Resolve primary key field name for an entity type."""
    pub_mapping = get_publication_mapping(entity_type)
    if pub_mapping is not None:
        return str(pub_mapping.primary_key_field)

    if entity_type in _NON_PUBLICATION_PK_FIELD_OVERRIDES:
        return _NON_PUBLICATION_PK_FIELD_OVERRIDES[entity_type]

    resource = _NON_PUBLICATION_ENTITY_MAPPING.get(entity_type, entity_type)
    return f"{resource}_id"


def resolve_dedup_key_fields(entity_type: str) -> tuple[str, ...]:
    """Resolve deduplication key fields for an entity type."""
    pub_fields = get_dedup_key_fields(entity_type)
    if pub_fields is not None:
        return tuple(str(field) for field in pub_fields)
    return (resolve_primary_key_field(entity_type),)


def has_entity_composite_key(entity_type: str) -> bool:
    """Return True when entity uses a composite deduplication key."""
    return bool(has_composite_key(entity_type))


def is_known_entity_type(entity_type: str) -> bool:
    """Return True when entity is known via publication or non-publication lookup."""
    return (
        is_publication_entity(entity_type)
        or entity_type in _NON_PUBLICATION_ENTITY_MAPPING
    )


def build_legacy_entity_mapping() -> dict[str, str]:
    """Build backward-compatible entity mapping export."""
    return {
        **_NON_PUBLICATION_ENTITY_MAPPING,
        "publication": "document",
        "publication_similarity": "document_similarity",
        "publication_term": "document",
        "document": "document",
        "document_similarity": "document_similarity",
        "document_term": "document",
    }
