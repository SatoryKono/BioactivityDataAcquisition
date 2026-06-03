"""Aggregate extraction helpers for UniProt comment facets."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_facets_data import (
    _COMMENT_OUTPUT_KEYS,
    _TEXT_COMMENT_FIELD_MAP,
    _UNIPROT_SEMANTIC_COMMENT_SIDECARS,
    _build_comment_index,
    _extract_text_values_from_index,
    _serialize_comment_type_payload,
)
from bioetl.application.pipelines.uniprot.extractors._comment_structured_facets import (
    _extract_alternative_products_family_raw,
    _extract_biophysicochemical_properties_raw,
    _extract_catalytic_activity_raw,
    _extract_cofactors_raw,
    _extract_reaction_parts_raw,
    _extract_subcellular_locations_raw,
)
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict


def extract_all_comments_raw(
    comments: list[JsonDict] | None,
) -> dict[str, object]:
    """Extract all UniProt comment-related fields as raw Python values."""
    raw: dict[str, object] = {key: [] for key in _COMMENT_OUTPUT_KEYS}
    raw["biophysicochemical_properties"] = {}
    raw["isoform_count"] = None

    index = _build_comment_index(comments)
    if index is None:
        return raw

    for field_name, comment_type in _TEXT_COMMENT_FIELD_MAP.items():
        raw[field_name] = _extract_text_values_from_index(index, comment_type)

    raw["subcellular_location"] = _extract_subcellular_locations_raw(index)
    raw["catalytic_activity"] = _extract_catalytic_activity_raw(index)
    raw["reactions"], raw["reaction_ec_numbers"] = _extract_reaction_parts_raw(index)

    (
        raw["alternative_products"],
        raw["isoform_count"],
        isoform_sections,
    ) = _extract_alternative_products_family_raw(index)
    raw.update(isoform_sections)

    raw["cofactors"] = _extract_cofactors_raw(index)
    raw["biophysicochemical_properties"] = _extract_biophysicochemical_properties_raw(
        index
    )

    return raw


def extract_all_comments(
    comments: list[JsonDict] | None,
) -> dict[str, str | int | None]:
    """Extract all UniProt comment-related fields in transformer output format."""
    raw = extract_all_comments_raw(comments)
    serialized: dict[str, str | int | None] = {}

    for key in _COMMENT_OUTPUT_KEYS:
        value = raw.get(key)
        if isinstance(value, list | dict):
            serialized[key] = serialize_to_json(value, ensure_ascii=False) if value else None
        else:
            serialized[key] = None

    isoform_count = raw.get("isoform_count")
    serialized["isoform_count"] = isoform_count if isinstance(isoform_count, int) else None
    index = _build_comment_index(comments)
    if index is not None:
        for (
            field_name,
            raw_sidecar_field,
            canonical_sidecar_field,
            comment_types,
        ) in _UNIPROT_SEMANTIC_COMMENT_SIDECARS:
            serialized[raw_sidecar_field] = _serialize_comment_type_payload(
                index, comment_types
            )
            serialized[canonical_sidecar_field] = serialized.get(field_name)
    else:
        for (
            _,
            raw_sidecar_field,
            canonical_sidecar_field,
            _,
        ) in _UNIPROT_SEMANTIC_COMMENT_SIDECARS:
            serialized[raw_sidecar_field] = None
            serialized[canonical_sidecar_field] = None
    return serialized


__all__ = ["extract_all_comments", "extract_all_comments_raw"]
