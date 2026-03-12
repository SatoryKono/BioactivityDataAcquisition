# src/bioetl/domain/schemas/semanticscholar/__init__.py
"""Pandera schemas for Semantic Scholar entities."""

from __future__ import annotations

from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from bioetl.domain.schemas.semanticscholar.publication import (
    OA_STATUS_VALUES,
    SemanticScholarPublicationSchema,
)

__all__ = [
    "LOOKUP_METHODS",
    "OA_STATUS_VALUES",
    "SemanticScholarPublicationSchema",
]
