"""CrossRef pipeline components.

Transformers and utilities for CrossRef data processing.
"""

from __future__ import annotations

from bioetl.application.pipelines.crossref.extractors import (
    extract_author_details,
    extract_author_orcids,
    extract_authors,
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
    extract_references,
)
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)

__all__ = [
    "CrossRefPublicationTransformer",
    "extract_author_details",
    "extract_author_orcids",
    "extract_authors",
    "extract_content_domain",
    "extract_dates",
    "extract_issn_by_type",
    "extract_journal_info",
    "extract_license_url",
    "extract_page_info",
    "extract_published_date",
    "extract_references",
]
