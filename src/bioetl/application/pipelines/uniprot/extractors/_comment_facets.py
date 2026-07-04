"""Focused extraction facets for UniProt comment payloads."""

# ruff: noqa: F401, I001
from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_facets_all import (
    extract_all_comments,
    extract_all_comments_raw,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    __all__ as _COMMENT_EXTRACTOR_EXPORTS,
    count_isoforms,
    extract_alternative_products,
    extract_biophysicochemical_properties,
    extract_by_type,
    extract_catalytic_activity,
    extract_cofactors,
    extract_isoform_details,
    extract_reaction_ec_numbers,
    extract_reactions,
    extract_subcellular_locations,
    extract_text_values,
)

__all__ = [
    "extract_all_comments",
    "extract_all_comments_raw",
    *_COMMENT_EXTRACTOR_EXPORTS,
]
