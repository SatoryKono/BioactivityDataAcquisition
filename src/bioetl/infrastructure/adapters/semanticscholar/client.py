"""Semantic Scholar adapter entrypoint.

Stable canonical import path — use this module (or the package
``bioetl.infrastructure.adapters.semanticscholar``) for all imports.
Implementation lives in ``adapter``.
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
