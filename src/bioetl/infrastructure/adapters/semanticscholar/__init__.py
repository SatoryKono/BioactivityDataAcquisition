# src/bioetl/infrastructure/adapters/semanticscholar/__init__.py
"""Semantic Scholar adapter package.

Provides SemanticScholarAdapter for batch DOI resolution with title fallback.
"""

from bioetl.infrastructure.adapters.semanticscholar.client import (
    SemanticScholarAdapter,
)
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)

__all__ = [
    "SEMANTICSCHOLAR_BASE_URL",
    "SemanticScholarAdapter",
]
