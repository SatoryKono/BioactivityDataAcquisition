"""Shared profile rules for derived publication classification fields."""

from __future__ import annotations

from bioetl.domain.mapping.publication_type_classification import (
    normalize_publication_classification_field,
)

__all__ = ["publication_classification_rules"]


def publication_classification_rules() -> dict[str, tuple[object, str]]:
    """Return strict taxonomy-backed rules for derived publication fields."""
    return {
        field_name: (
            lambda value, record=None, field_name=field_name: (
                normalize_publication_classification_field(field_name, value)
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
