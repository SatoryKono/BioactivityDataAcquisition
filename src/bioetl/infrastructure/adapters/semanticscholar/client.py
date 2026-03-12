"""Retained Semantic Scholar adapter entrypoint.

This module is the stable canonical import path for first-party code. It
remains intentionally retained in the current cycle while the implementation
continues to live in ``adapter``.
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
