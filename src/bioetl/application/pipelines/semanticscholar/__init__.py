# src/bioetl/application/pipelines/semanticscholar/__init__.py
"""Semantic Scholar pipeline package.

Provides transformer and extractors for Semantic Scholar publication data.
"""

from __future__ import annotations

from bioetl.application.pipelines.semanticscholar import extractors as _extractors
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)

extract_external_ids = _extractors.extract_external_ids
extract_fields_of_study = _extractors.extract_fields_of_study
extract_journal_info = _extractors.extract_journal_info
extract_open_access_info = _extractors.extract_open_access_info
extract_tldr = _extractors.extract_tldr

__all__ = ["SemanticScholarPublicationTransformer"]
__all__.extend(
    name
    for name in _extractors.__all__
    if name
    in {
        "extract_external_ids",
        "extract_fields_of_study",
        "extract_journal_info",
        "extract_open_access_info",
        "extract_tldr",
    }
)
