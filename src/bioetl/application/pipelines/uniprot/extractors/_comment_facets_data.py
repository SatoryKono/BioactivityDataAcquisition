"""Shared constants and index helpers for UniProt comment facets."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_helpers import (
    _extract_texts_from_dict,
)
from bioetl.application.pipelines.uniprot.extractors._comment_structured_facets import (
    _ISOFORM_SECTION_NORMALIZERS,
)
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict

_TEXT_COMMENT_FIELD_MAP: dict[str, str] = {
    "function_comment": "FUNCTION",
    "activity_regulation": "ACTIVITY REGULATION",
    "subunit": "SUBUNIT",
    "pathway": "PATHWAY",
    "tissue_specificity": "TISSUE SPECIFICITY",
    "disease_involvement": "DISEASE",
    "similarity_comment": "SIMILARITY",
    "caution": "CAUTION",
    "induction": "INDUCTION",
}

_UNIPROT_SEMANTIC_COMMENT_SIDECARS: tuple[
    tuple[str, str, str, tuple[str, ...]],
    ...,
] = (
    (
        "alternative_products",
        "alternative_products_raw_json",
        "alternative_products_canonical_json",
        ("ALTERNATIVE PRODUCTS",),
    ),
    (
        "biophysicochemical_properties",
        "biophysicochemical_properties_raw_json",
        "biophysicochemical_properties_canonical_json",
        ("BIOPHYSICOCHEMICAL PROPERTIES",),
    ),
    (
        "cofactors",
        "cofactors_raw_json",
        "cofactors_canonical_json",
        ("COFACTOR",),
    ),
    (
        "reactions",
        "reactions_raw_json",
        "reactions_canonical_json",
        ("CATALYTIC ACTIVITY",),
    ),
)

_COMMENT_OUTPUT_KEYS: tuple[str, ...] = (
    "function_comment",
    "catalytic_activity",
    "activity_regulation",
    "subunit",
    "pathway",
    "subcellular_location",
    "tissue_specificity",
    "alternative_products",
    "disease_involvement",
    "similarity_comment",
    "caution",
    "cofactors",
    "biophysicochemical_properties",
    "induction",
    "isoform_names",
    "isoform_ids",
    "isoform_synonyms",
    "reactions",
    "reaction_ec_numbers",
)

_COMMENT_ANNOTATION_OUTPUT_KEYS: tuple[str, ...] = (
    "function_comment",
    "catalytic_activity",
    "activity_regulation",
    "subunit",
    "pathway",
    "subcellular_location",
    "tissue_specificity",
    "alternative_products",
    "alternative_products_raw_json",
    "alternative_products_canonical_json",
    "disease_involvement",
    "similarity_comment",
    "caution",
    "cofactors",
    "cofactors_raw_json",
    "cofactors_canonical_json",
    "biophysicochemical_properties",
    "biophysicochemical_properties_raw_json",
    "biophysicochemical_properties_canonical_json",
    "induction",
    "isoform_names",
    "isoform_ids",
    "isoform_synonyms",
    "reactions",
    "reactions_raw_json",
    "reactions_canonical_json",
    "reaction_ec_numbers",
)


def _normalize_comments(comments: list[JsonDict] | None) -> list[JsonDict] | None:
    """Validate and normalize comments input."""
    if not comments or not isinstance(comments, list):
        return None
    return comments


def _build_comment_index(
    comments: list[JsonDict] | None,
) -> dict[str, list[JsonDict]] | None:
    """Build index grouped by commentType in a single pass."""
    normalized = _normalize_comments(comments)
    if normalized is None:
        return None

    index: dict[str, list[JsonDict]] = {}
    for comment in normalized:
        if not isinstance(comment, dict):
            continue
        comment_type = comment.get("commentType")
        if not isinstance(comment_type, str) or not comment_type:
            continue
        index.setdefault(comment_type, []).append(comment)
    return index


def _iter_comments_by_type(
    index: dict[str, list[JsonDict]],
    comment_type: str,
) -> list[JsonDict]:
    """Get comments for a type from prebuilt index."""
    return index.get(comment_type, [])


def _extract_text_values_from_index(
    index: dict[str, list[JsonDict]],
    comment_type: str,
) -> list[str]:
    """Extract text values for one comment type from index."""
    extracted: list[str] = []
    for comment in _iter_comments_by_type(index, comment_type):
        extracted.extend(_extract_texts_from_dict(comment))
    return extracted


def _serialize_comment_type_payload(
    index: dict[str, list[JsonDict]],
    comment_types: tuple[str, ...],
) -> str | None:
    """Serialize raw provider comment envelopes for the requested types."""
    payload: list[JsonDict] = []
    for comment_type in comment_types:
        payload.extend(_iter_comments_by_type(index, comment_type))
    return serialize_to_json(payload, ensure_ascii=False) if payload else None


__all__ = [
    "_COMMENT_ANNOTATION_OUTPUT_KEYS",
    "_COMMENT_OUTPUT_KEYS",
    "_ISOFORM_SECTION_NORMALIZERS",
    "_TEXT_COMMENT_FIELD_MAP",
    "_UNIPROT_SEMANTIC_COMMENT_SIDECARS",
    "_build_comment_index",
    "_extract_text_values_from_index",
    "_iter_comments_by_type",
    "_normalize_comments",
    "_serialize_comment_type_payload",
]
