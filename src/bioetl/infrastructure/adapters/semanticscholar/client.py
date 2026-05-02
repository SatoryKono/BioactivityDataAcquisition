"""Deprecated compatibility shim for Semantic Scholar client-path imports.

Canonical provider adapter surface:
    - ``bioetl.infrastructure.adapters.semanticscholar``
    - ``bioetl.infrastructure.adapters.semanticscholar.adapter``
"""

from __future__ import annotations

import warnings

from bioetl.infrastructure.adapters.semanticscholar.adapter import (
    DEFAULT_FIELDS,
    SEMANTICSCHOLAR_HEALTH_ERRORS,
    SemanticScholarAdapter,
)

warnings.warn(
    "bioetl.infrastructure.adapters.semanticscholar.client is deprecated; "
    "import SemanticScholarAdapter from "
    "bioetl.infrastructure.adapters.semanticscholar or "
    "bioetl.infrastructure.adapters.semanticscholar.adapter instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "DEFAULT_FIELDS",
    "SEMANTICSCHOLAR_HEALTH_ERRORS",
    "SemanticScholarAdapter",
]
