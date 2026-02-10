"""Domain mapping utilities for cross-provider field unification."""

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

__all__ = [
    "PUBLICATION_FIELD_MAPPING",
    "PublicationTypeEntry",
    "UNIFIED_TO_PROVIDER",
    "apply_field_mapping",
    "classify_publication_type",
    "get_provider_name",
    "get_unified_name",
]
