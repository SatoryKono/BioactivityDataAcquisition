"""Extractor helpers for UniProt comment facets."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_facets_data import (
    _build_comment_index,
    _extract_text_values_from_index,
)
from bioetl.application.pipelines.uniprot.extractors._comment_structured_facets import (
    _ISOFORM_SECTION_NORMALIZERS,
    _extract_alternative_products_family_raw,
    _extract_biophysicochemical_properties_raw,
    _extract_catalytic_activity_raw,
    _extract_cofactors_raw,
    _extract_reaction_parts_raw,
    _extract_subcellular_locations_raw,
    _serialize_isoform_sections,
)
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict


def extract_text_values(
    comments: list[JsonDict],
    comment_type: str,
) -> list[str]:
    """Extract text values from comments of specific type."""
    index = _build_comment_index(comments)
    if index is None:
        return []
    return _extract_text_values_from_index(index, comment_type)


def extract_by_type(comments: list[JsonDict] | None, comment_type: str) -> str | None:
    """Extract comments by type as serialized JSON array."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_text_values_from_index(index, comment_type)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def extract_catalytic_activity(comments: list[JsonDict] | None) -> str | None:
    """Extract catalytic activity records."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_catalytic_activity_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def extract_subcellular_locations(comments: list[JsonDict] | None) -> str | None:
    """Extract subcellular location labels."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_subcellular_locations_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def extract_alternative_products(comments: list[JsonDict] | None) -> str | None:
    """Extract alternative products (isoforms) data."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted, _, _ = _extract_alternative_products_family_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def count_isoforms(comments: list[JsonDict] | None) -> int | None:
    """Count isoforms from ALTERNATIVE PRODUCTS comments."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    _, count, _ = _extract_alternative_products_family_raw(index)
    return count


def extract_cofactors(comments: list[JsonDict] | None) -> str | None:
    """Extract cofactor entries."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_cofactors_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def extract_biophysicochemical_properties(
    comments: list[JsonDict] | None,
) -> str | None:
    """Extract biophysicochemical properties."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_biophysicochemical_properties_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def extract_isoform_details(comments: list[JsonDict] | None) -> dict[str, str | None]:
    """Extract normalized isoform names/ids/synonyms."""
    index = _build_comment_index(comments)
    section_values: dict[str, list[str]]
    if index is None:
        section_values = {section: [] for section, _ in _ISOFORM_SECTION_NORMALIZERS}
    else:
        _, _, section_values = _extract_alternative_products_family_raw(index)

    return _serialize_isoform_sections(section_values)


def extract_reactions(comments: list[JsonDict] | None) -> str | None:
    """Extract reaction names from catalytic activity comments."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    reactions, _ = _extract_reaction_parts_raw(index)
    return serialize_to_json(reactions, ensure_ascii=False) if reactions else None


def extract_reaction_ec_numbers(comments: list[JsonDict] | None) -> str | None:
    """Extract reaction EC numbers from catalytic activity comments."""
    index = _build_comment_index(comments)
    if index is None:
        return None

    _, ec_numbers = _extract_reaction_parts_raw(index)
    return serialize_to_json(ec_numbers, ensure_ascii=False) if ec_numbers else None


__all__ = [
    "count_isoforms",
    "extract_alternative_products",
    "extract_biophysicochemical_properties",
    "extract_by_type",
    "extract_catalytic_activity",
    "extract_cofactors",
    "extract_isoform_details",
    "extract_reaction_ec_numbers",
    "extract_reactions",
    "extract_subcellular_locations",
    "extract_text_values",
]
