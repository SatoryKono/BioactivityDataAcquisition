"""Facade for CrossRef batch and pagination collaborators."""

from __future__ import annotations

__all__ = [
    "CROSSREF_FALLBACK_ERRORS",
    "CROSSREF_RUNTIME_ERRORS",
    "BaseMetrics",
    "DoiBatchProcessor",
    "HttpTransport",
    "SearchPaginator",
]
from bioetl.infrastructure.adapters.crossref._batch_support import (
    CROSSREF_FALLBACK_ERRORS,
    CROSSREF_RUNTIME_ERRORS,
    BaseMetrics,
    HttpTransport,
)
from bioetl.infrastructure.adapters.crossref._doi_batch_processor import (
    DoiBatchProcessor,
)
from bioetl.infrastructure.adapters.crossref._search_paginator import (
    SearchPaginator,
)
