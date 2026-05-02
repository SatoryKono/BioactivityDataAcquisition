"""Shared profile rules for derived publication classification fields.

These rules apply only to the derived harmonized taxonomy fields:
``publication_type_unified``, ``publication_subclass``, and
``publication_class``.

Raw provider-native fields such as ``publication_type``, ``type_crossref``,
and provider-specific type arrays remain raw sidecars and must not be treated
as strict enums merely because current fixtures have low cardinality.
"""

from __future__ import annotations

from bioetl.domain.mapping.publication_type_classification import (
    normalize_publication_classification_field,
)

__all__ = ["publication_classification_rules"]


def publication_classification_rules() -> dict[str, tuple[object, str]]:
    """Return strict taxonomy-backed rules for derived publication fields only."""
    return {
        field_name: (
            lambda value, field_name=field_name: (
                normalize_publication_classification_field(
                    field_name,
                    value,
                )
            ),
            (
                f"Normalize derived {field_name} against the unified "
                "publication type classification taxonomy."
            ),
        )
        for field_name in (
            "publication_type_unified",
            "publication_subclass",
            "publication_class",
        )
    }
