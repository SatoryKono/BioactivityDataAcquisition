"""Domain mapping utilities for cross-provider field unification."""

from bioetl.domain.mapping.activity_fields import ACTIVITY_FIELD_MAPPING
from bioetl.domain.mapping.molecule_fields import MOLECULE_FIELD_MAPPING
from bioetl.domain.mapping.organism_classification import (
    OrganismClass,
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
)
from bioetl.domain.mapping.publication_type_mapping import (
    PUBLICATION_TYPE_MAPPING,
    normalize_publication_type,
)

__all__ = [
    "ACTIVITY_FIELD_MAPPING",
    "MOLECULE_FIELD_MAPPING",
    "PUBLICATION_FIELD_MAPPING",
    "PUBLICATION_TYPE_MAPPING",
    "UNIFIED_TO_PROVIDER",
    "OrganismClass",
    "OrganismClassificationResult",
    "PublicationTypeEntry",
    "apply_field_mapping",
    "classify_organism",
    "classify_publication_type",
    "get_provider_name",
    "get_unified_name",
    "normalize_organism_name",
    "normalize_publication_type",
]
