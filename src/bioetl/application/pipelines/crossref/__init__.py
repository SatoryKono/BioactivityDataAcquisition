"""CrossRef pipeline components.

Transformers and utilities for CrossRef data processing.
"""

from bioetl.application.pipelines.crossref.extractors import (
    extract_authors,
    extract_dates,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_year,
)
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)

__all__ = [
    "CrossRefPublicationTransformer",
    "extract_authors",
    "extract_dates",
    "extract_journal_info",
    "extract_license_url",
    "extract_page_info",
    "extract_year",
]
