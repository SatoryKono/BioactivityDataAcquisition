# src/bioetl/infrastructure/adapters/semanticscholar/__init__.py
"""Semantic Scholar adapter package.

Provides SemanticScholarAdapter for batch DOI resolution with title fallback.
"""

from bioetl.infrastructure.adapters.semanticscholar.adapter import (
    SEMANTICSCHOLAR_BASE_URL,
    SemanticScholarAdapter,
)

__all__ = [
    "SEMANTICSCHOLAR_BASE_URL",
    "SemanticScholarAdapter",
]
