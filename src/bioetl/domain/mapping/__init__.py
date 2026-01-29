"""Domain mapping utilities for cross-provider field unification."""

from bioetl.domain.mapping.publication_fields import (
    PUBLICATION_FIELD_MAPPING,
    UNIFIED_TO_PROVIDER,
    get_unified_name,
    get_provider_name,
)

__all__ = [
    "PUBLICATION_FIELD_MAPPING",
    "UNIFIED_TO_PROVIDER",
    "get_unified_name",
    "get_provider_name",
]
