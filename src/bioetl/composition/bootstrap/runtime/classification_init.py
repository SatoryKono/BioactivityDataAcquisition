"""Compatibility exports for classification initialization at composition root."""

from __future__ import annotations

from bioetl.composition.runtime_builders.config_access import (
    initialize_protein_class_target_type_mapping,
    initialize_publication_type_classification,
)

__all__ = [
    "initialize_protein_class_target_type_mapping",
    "initialize_publication_type_classification",
]
