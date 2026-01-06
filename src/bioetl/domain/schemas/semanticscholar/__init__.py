# src/bioetl/domain/schemas/semanticscholar/__init__.py
"""Pandera schemas for Semantic Scholar entities."""

from bioetl.domain.schemas.semanticscholar.publication import (
    LOOKUP_METHODS,
    OA_STATUS_VALUES,
    SemanticScholarPublicationSchema,
)

__all__ = [
    "LOOKUP_METHODS",
    "OA_STATUS_VALUES",
    "SemanticScholarPublicationSchema",
]
