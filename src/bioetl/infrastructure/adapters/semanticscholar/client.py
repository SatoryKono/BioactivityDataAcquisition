"""Canonical Semantic Scholar adapter entrypoint.

Keeps backward compatibility while steering new imports away from
``adapter``.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.semanticscholar.adapter import (
    DEFAULT_FIELDS,
    SEMANTICSCHOLAR_HEALTH_ERRORS,
    SemanticScholarAdapter,
)

__all__ = [
    "DEFAULT_FIELDS",
    "SEMANTICSCHOLAR_HEALTH_ERRORS",
    "SemanticScholarAdapter",
]
