"""Deprecated compatibility shim for PubMed adapter client-path imports.

Canonical provider adapter surface:
    - ``bioetl.infrastructure.adapters.pubmed``
    - ``bioetl.infrastructure.adapters.pubmed.adapter``
"""

from __future__ import annotations

import warnings

from bioetl.infrastructure.adapters.pubmed.adapter import (
    ENTREZ_API_BASE,
    PubMedAdapter,
)
from bioetl.infrastructure.adapters.pubmed.adapter import (
    _create_pubmed_adapter as create_pubmed_adapter,
)

warnings.warn(
    "bioetl.infrastructure.adapters.pubmed.client is deprecated; "
    "import PubMedAdapter from bioetl.infrastructure.adapters.pubmed or "
    "bioetl.infrastructure.adapters.pubmed.adapter instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ENTREZ_API_BASE", "PubMedAdapter", "create_pubmed_adapter"]
