"""Domain mapping utilities for cross-provider field unification."""

from __future__ import annotations

from bioetl.domain.mapping.activity_fields import ACTIVITY_FIELD_MAPPING
from bioetl.domain.mapping.classification_data import ClassificationData
from bioetl.domain.mapping.molecule_fields import MOLECULE_FIELD_MAPPING
from bioetl.domain.mapping.organism_classification import (
    OrganismClassificationResult,
    classify_organism,
    normalize_organism_name,
)
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTargetTypeResult,
    ProteinClassTopLevelMappingEntry,
    derive_major_families,
    derive_protein_class_target_type,
    initialize_protein_class_target_type_mapping,
)
from bioetl.domain.mapping.publication_fields import (
    PUBLICATION_FIELD_MAPPING,
    UNIFIED_TO_PROVIDER,
    apply_field_mapping,
    get_provider_name,
    get_unified_name,
)
from bioetl.domain.mapping.publication_type_classification import (
    PublicationTypeEntry,
    classify_publication_type,
    initialize_classification,
)
from bioetl.domain.mapping.publication_type_mapping import (
    PUBLICATION_TYPE_MAPPING,
    normalize_publication_type,
)
from bioetl.domain.mapping.pubmed_publication import (
    PUBMED_SILVER_EXCLUDED_FIELDS,
    build_pubmed_publication_type_fields,
)

__all__ = [
    "ACTIVITY_FIELD_MAPPING",
    "MOLECULE_FIELD_MAPPING",
    "PUBLICATION_FIELD_MAPPING",
    "PUBLICATION_TYPE_MAPPING",
    "PUBMED_SILVER_EXCLUDED_FIELDS",
    "UNIFIED_TO_PROVIDER",
    "ClassificationData",
    "OrganismClassificationResult",
    "ProteinClassTargetTypeMappingData",
    "ProteinClassTargetTypeResult",
    "ProteinClassTopLevelMappingEntry",
    "PublicationTypeEntry",
    "apply_field_mapping",
    "build_pubmed_publication_type_fields",
    "classify_organism",
    "classify_publication_type",
    "derive_major_families",
    "derive_protein_class_target_type",
    "get_provider_name",
    "get_unified_name",
    "initialize_classification",
    "initialize_protein_class_target_type_mapping",
    "normalize_organism_name",
    "normalize_publication_type",
]
