"""Domain mapping utilities for cross-provider field unification."""

from bioetl.domain.mapping.publication_fields import (
    PUBLICATION_FIELD_MAPPING,
    UNIFIED_TO_PROVIDER,
    apply_field_mapping,
    get_provider_name,
    get_unified_name,
)

__all__ = [
    "PUBLICATION_FIELD_MAPPING",
    "UNIFIED_TO_PROVIDER",
    "apply_field_mapping",
    "get_provider_name",
    "get_unified_name",
]
