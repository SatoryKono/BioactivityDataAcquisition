"""OpenAlex pipeline package.

Contains transformer and extractors for OpenAlex Works API data.
"""

from __future__ import annotations

from bioetl.application.pipelines.openalex.extractors import (
    extract_authors,
    extract_doi,
    extract_journal_info,
    reconstruct_abstract,
)
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)

__all__ = [
    "OpenAlexPublicationTransformer",
    "extract_authors",
    "extract_doi",
    "extract_journal_info",
    "reconstruct_abstract",
]
