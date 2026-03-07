"""Focused extraction facets for UniProt comment payloads."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_helpers import (
    _ISOFORM_SECTION_NORMALIZERS,
    _build_isoform_data,
    _extract_biophys_from_comment,
    _extract_cofactor_entry,
    _extract_location_value,
    _extract_reaction_data,
    _extract_texts_from_dict,
)
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict

_CATALYTIC_ACTIVITY = "CATALYTIC ACTIVITY"
_SUBCELLULAR_LOCATION = "SUBCELLULAR LOCATION"
_ALTERNATIVE_PRODUCTS = "ALTERNATIVE PRODUCTS"
_COFACTOR = "COFACTOR"
_BIOPHYSICOCHEMICAL_PROPERTIES = "BIOPHYSICOCHEMICAL PROPERTIES"
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


def extract_text_values(
    comments: list[JsonDict],
    comment_type: str,
) -> list[str]:
    """Extract text values from comments of specific type.

    Args:
        comments: List of UniProt comment dicts from the API response.
        comment_type: UniProt comment type string to filter on.

    Returns:
        List of extracted text strings for the given comment type.
    """
    index = _build_comment_index(comments)
    if index is None:
        return []
    return _extract_text_values_from_index(index, comment_type)


def _extract_text_values_from_index(
    index: dict[str, list[JsonDict]],
    comment_type: str,
) -> list[str]:
    """Extract text values for one comment type from index."""
    extracted: list[str] = []
    for comment in _iter_comments_by_type(index, comment_type):
        extracted.extend(_extract_texts_from_dict(comment))
    return extracted


def extract_by_type(
    comments: list[JsonDict] | None,
    comment_type: str,
) -> str | None:
    """Extract comments by type as serialized JSON array.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.
        comment_type: UniProt comment type string to filter on.

    Returns:
        JSON-serialized array of text values, or None if no matching comments.
    """
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_text_values_from_index(index, comment_type)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def extract_catalytic_activity(comments: list[JsonDict] | None) -> str | None:
    """Extract catalytic activity records.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        JSON-serialized list of catalytic activity dicts, or None if absent.
    """
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_catalytic_activity_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def _extract_catalytic_activity_raw(
    index: dict[str, list[JsonDict]],
) -> list[JsonDict]:
    """Extract raw catalytic activity entries from index."""
    extracted: list[JsonDict] = []  # Any: JSON values
    for comment in _iter_comments_by_type(index, _CATALYTIC_ACTIVITY):
        reaction = comment.get("reaction", {})
        if isinstance(reaction, dict):
            activity = _extract_reaction_data(reaction)
            if activity:
                extracted.append(activity)
    return extracted


def extract_subcellular_locations(comments: list[JsonDict] | None) -> str | None:
    """Extract subcellular location labels.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        JSON-serialized list of subcellular location strings, or None if absent.
    """
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_subcellular_locations_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def _extract_subcellular_locations_raw(
    index: dict[str, list[JsonDict]],
) -> list[str]:
    """Extract raw subcellular location values from index."""
    extracted: list[str] = []
    for comment in _iter_comments_by_type(index, _SUBCELLULAR_LOCATION):
        locations = comment.get("subcellularLocations", [])
        if not isinstance(locations, list):
            continue
        for loc in locations:
            if not isinstance(loc, dict):
                continue
            value = _extract_location_value(loc)
            if value:
                extracted.append(value)
    return extracted


def extract_alternative_products(comments: list[JsonDict] | None) -> str | None:
    """Extract alternative products (isoforms) data.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        JSON-serialized list of isoform dicts, or None if no alternative products.
    """
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted, _, _ = _extract_alternative_products_family_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def _extract_alternative_products_family_raw(
    index: dict[str, list[JsonDict]],
) -> tuple[list[JsonDict], int | None, dict[str, list[str]]]:
    """Extract alternative products, isoform count, and detailed sections."""
    alternative_products: list[JsonDict] = []  # Any: JSON values
    count = 0
    sections: dict[str, list[str]] = {
        section: [] for section, _ in _ISOFORM_SECTION_NORMALIZERS
    }

    for comment in _iter_comments_by_type(index, _ALTERNATIVE_PRODUCTS):
        isoforms = comment.get("isoforms", [])
        if not isinstance(isoforms, list):
            continue
        count += len(isoforms)
        for isoform in isoforms:
            if not isinstance(isoform, dict):
                continue
            isoform_data = _build_isoform_data(isoform)
            if isoform_data:
                alternative_products.append(isoform_data)
            for section, normalize in _ISOFORM_SECTION_NORMALIZERS:
                sections[section].extend(normalize(isoform))

    return alternative_products, count if count > 0 else None, sections


def count_isoforms(comments: list[JsonDict] | None) -> int | None:
    """Count isoforms from ALTERNATIVE PRODUCTS comments.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        Total isoform count, or None if no alternative products are present.
    """
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


def _extract_cofactors_raw(index: dict[str, list[JsonDict]]) -> list[JsonDict]:
    """Extract raw cofactor entries from index."""
    extracted: list[JsonDict] = []  # Any: JSON values
    for comment in _iter_comments_by_type(index, _COFACTOR):
        cofactors = comment.get("cofactors", [])
        if not isinstance(cofactors, list):
            continue
        for cofactor in cofactors:
            if not isinstance(cofactor, dict):
                continue
            cofactor_data = _extract_cofactor_entry(cofactor)
            if cofactor_data:
                extracted.append(cofactor_data)
    return extracted


def extract_biophysicochemical_properties(
    comments: list[JsonDict] | None,
) -> str | None:
    """Extract biophysicochemical properties.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        JSON-serialized dict of biophysicochemical property values, or None if absent.
    """
    index = _build_comment_index(comments)
    if index is None:
        return None

    extracted = _extract_biophysicochemical_properties_raw(index)
    return serialize_to_json(extracted, ensure_ascii=False) if extracted else None


def _extract_biophysicochemical_properties_raw(
    index: dict[str, list[JsonDict]],
) -> JsonDict:
    """Extract raw biophysicochemical properties from index."""
    extracted: JsonDict = {}  # Any: JSON values
    for comment in _iter_comments_by_type(index, _BIOPHYSICOCHEMICAL_PROPERTIES):
        extracted.update(_extract_biophys_from_comment(comment))
    return extracted


def extract_isoform_details(
    comments: list[JsonDict] | None,
) -> dict[str, str | None]:
    """Extract normalized isoform names/ids/synonyms.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        Dict mapping section names (isoform_names, isoform_ids, isoform_synonyms)
        to JSON-serialized string values, or None if the section is empty.
    """
    index = _build_comment_index(comments)
    section_values: dict[str, list[str]]
    if index is None:
        section_values = {section: [] for section, _ in _ISOFORM_SECTION_NORMALIZERS}
    else:
        _, _, section_values = _extract_alternative_products_family_raw(index)

    return _serialize_isoform_sections(section_values)


def extract_reactions(comments: list[JsonDict] | None) -> str | None:
    """Extract reaction names from catalytic activity comments.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        JSON-serialized list of reaction name strings, or None if absent.
    """
    index = _build_comment_index(comments)
    if index is None:
        return None

    reactions, _ = _extract_reaction_parts_raw(index)
    return serialize_to_json(reactions, ensure_ascii=False) if reactions else None


def extract_reaction_ec_numbers(comments: list[JsonDict] | None) -> str | None:
    """Extract reaction EC numbers from catalytic activity comments.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        JSON-serialized list of EC number strings, or None if absent.
    """
    index = _build_comment_index(comments)
    if index is None:
        return None

    _, ec_numbers = _extract_reaction_parts_raw(index)
    return serialize_to_json(ec_numbers, ensure_ascii=False) if ec_numbers else None


def _extract_reaction_parts_raw(
    index: dict[str, list[JsonDict]],
) -> tuple[list[str], list[str]]:
    """Extract reaction names and EC numbers from catalytic comments."""
    reactions: list[str] = []
    ec_numbers: list[str] = []
    for comment in _iter_comments_by_type(index, _CATALYTIC_ACTIVITY):
        reaction = comment.get("reaction", {})
        if not isinstance(reaction, dict):
            continue
        name = reaction.get("name")
        ec_number = reaction.get("ecNumber")
        if name:
            reactions.append(str(name))
        if ec_number:
            ec_numbers.append(str(ec_number))
    return reactions, ec_numbers


def extract_all_comments_raw(
    comments: list[JsonDict] | None,
) -> dict[str, object]:
    """Extract all UniProt comment-related fields as raw Python values.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        Dict mapping output field names to raw Python values (lists, dicts, int, or None).
        Includes all comment output keys plus isoform_count.
    """
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


def _serialize_isoform_sections(
    section_values: dict[str, list[str]],
) -> dict[str, str | None]:
    """Serialize isoform section arrays into output values."""
    result: dict[str, str | None] = {
        section: None for section, _ in _ISOFORM_SECTION_NORMALIZERS
    }
    for section, values in section_values.items():
        if values:
            result[section] = serialize_to_json(values, ensure_ascii=False)
    return result


def extract_all_comments(
    comments: list[JsonDict] | None,
) -> dict[str, str | int | None]:
    """Extract all UniProt comment-related fields in transformer output format.

    Args:
        comments: List of UniProt comment dicts from the API response, or None.

    Returns:
        Dict mapping output field names to JSON-serialized strings, integers, or None.
        All list/dict values are serialized to JSON strings; isoform_count is int or None.
    """
    raw = extract_all_comments_raw(comments)
    serialized: dict[str, str | int | None] = {}

    for key in _COMMENT_OUTPUT_KEYS:
        value = raw.get(key)
        if isinstance(value, list | dict):
            serialized[key] = (
                serialize_to_json(value, ensure_ascii=False) if value else None
            )
        else:
            serialized[key] = None

    isoform_count = raw.get("isoform_count")
    serialized["isoform_count"] = (
        isoform_count if isinstance(isoform_count, int) else None
    )
    return serialized
