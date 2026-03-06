"""Domain mapping utilities for cross-provider field unification."""

from bioetl.domain.mapping.activity_fields import ACTIVITY_FIELD_MAPPING
from bioetl.domain.mapping.classification_data import ClassificationData
from bioetl.domain.mapping.molecule_fields import MOLECULE_FIELD_MAPPING
from bioetl.domain.mapping.organism_classification import (
    OrganismClassificationResult,
    classify_organism,
    normalize_organism_name,
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

__all__ = [
    "ACTIVITY_FIELD_MAPPING",
    "ClassificationData",
    "MOLECULE_FIELD_MAPPING",
    "PUBLICATION_FIELD_MAPPING",
    "PUBLICATION_TYPE_MAPPING",
    "UNIFIED_TO_PROVIDER",
    "OrganismClassificationResult",
    "PublicationTypeEntry",
    "apply_field_mapping",
    "classify_organism",
    "classify_publication_type",
    "get_provider_name",
    "get_unified_name",
    "initialize_classification",
    "normalize_organism_name",
    "normalize_publication_type",
]
