# src/bioetl/application/pipelines/semanticscholar/__init__.py
"""Semantic Scholar pipeline package.

Provides transformer and extractors for Semantic Scholar publication data.
"""

from __future__ import annotations

from bioetl.application.pipelines.semanticscholar.extractors import (
    extract_external_ids,
    extract_fields_of_study,
    extract_journal_info,
    extract_open_access_info,
    extract_tldr,
)
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)

__all__ = [
    "SemanticScholarPublicationTransformer",
    # extract_authors excluded per user request
    "extract_external_ids",
    "extract_fields_of_study",
    "extract_journal_info",
    "extract_open_access_info",
    "extract_tldr",
]
