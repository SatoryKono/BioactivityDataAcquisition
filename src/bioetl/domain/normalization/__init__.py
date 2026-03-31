"""Pure domain normalization functions (no I/O)."""

from __future__ import annotations

from bioetl.domain.normalization.authors import (
    extract_first_item,
    extract_first_string,
    parse_authors_to_list,
)
from bioetl.domain.normalization.dates import format_date_parts, parse_date_field
from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
    strip_doi_prefix,
)
from bioetl.domain.normalization.pages import parse_page_range
from bioetl.domain.normalization.text import (
    normalize_string,
    normalize_to_string,
    strip_html_tags,
)

__all__ = [
    "extract_first_item",
    "extract_first_string",
    "format_date_parts",
    "normalize_doi",
    "normalize_pmc_id",
    "normalize_pmid",
    "normalize_string",
    "normalize_to_string",
    "parse_authors_to_list",
    "parse_date_field",
    "parse_page_range",
    "strip_doi_prefix",
    "strip_html_tags",
]
