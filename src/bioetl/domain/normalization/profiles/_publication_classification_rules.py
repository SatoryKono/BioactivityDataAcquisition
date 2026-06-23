"""Shared profile rules for derived publication classification fields.

These rules apply only to the derived harmonized taxonomy fields:
``publication_type_unified``, ``publication_subclass``, and
``publication_class``.

Raw provider-native fields such as ``publication_type``, ``type_crossref``,
and provider-specific type arrays remain raw sidecars and must not be treated
as strict enums merely because current fixtures have low cardinality.
"""

from __future__ import annotations

from bioetl.domain.normalization.profiles._profile_publication_normalizers import (
    normalize_profile_chembl_publication_classification_field,
)

__all__ = ["publication_classification_rules"]


def publication_classification_rules() -> dict[str, tuple[object, str]]:
    """Return strict taxonomy-backed rules for derived publication fields only."""
    return {
        field_name: (
            lambda value, field_name=field_name, record=None: (
                normalize_profile_chembl_publication_classification_field(
                    value,
                    field_name=field_name,
                    record=record,
                )
            ),
            (
                f"Normalize derived {field_name} against the unified "
                "publication type classification taxonomy using the raw "
                "provider publication type as the authoritative input seam."
            ),
        )
        for field_name in (
            "publication_type_unified",
            "publication_subclass",
            "publication_class",
        )
    }
