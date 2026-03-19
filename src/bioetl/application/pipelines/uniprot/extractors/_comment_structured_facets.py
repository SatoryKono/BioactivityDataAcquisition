"""Structured extraction helpers for UniProt comment facets."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_helpers import (
    _ISOFORM_SECTION_NORMALIZERS,
    _build_isoform_data,
    _extract_biophys_from_comment,
    _extract_cofactor_entry,
    _extract_location_value,
    _extract_reaction_data,
)
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict

_CATALYTIC_ACTIVITY = "CATALYTIC ACTIVITY"
_SUBCELLULAR_LOCATION = "SUBCELLULAR LOCATION"
_ALTERNATIVE_PRODUCTS = "ALTERNATIVE PRODUCTS"
_COFACTOR = "COFACTOR"
_BIOPHYSICOCHEMICAL_PROPERTIES = "BIOPHYSICOCHEMICAL PROPERTIES"


def _extract_catalytic_activity_raw(
    index: dict[str, list[JsonDict]],
) -> list[JsonDict]:
    """Extract raw catalytic activity entries from index."""
    extracted: list[JsonDict] = []  # Any: JSON values
    for comment in index.get(_CATALYTIC_ACTIVITY, []):
        reaction = comment.get("reaction", {})
        if isinstance(reaction, dict):
            activity = _extract_reaction_data(reaction)
            if activity:
                extracted.append(activity)
    return extracted


def _extract_subcellular_locations_raw(
    index: dict[str, list[JsonDict]],
) -> list[str]:
    """Extract raw subcellular location values from index."""
    extracted: list[str] = []
    for comment in index.get(_SUBCELLULAR_LOCATION, []):
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


def _extract_alternative_products_family_raw(
    index: dict[str, list[JsonDict]],
) -> tuple[list[JsonDict], int | None, dict[str, list[str]]]:
    """Extract alternative products, isoform count, and detailed sections."""
    alternative_products: list[JsonDict] = []  # Any: JSON values
    count = 0
    sections: dict[str, list[str]] = {
        section: [] for section, _ in _ISOFORM_SECTION_NORMALIZERS
    }

    for comment in index.get(_ALTERNATIVE_PRODUCTS, []):
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


def _extract_cofactors_raw(index: dict[str, list[JsonDict]]) -> list[JsonDict]:
    """Extract raw cofactor entries from index."""
    extracted: list[JsonDict] = []  # Any: JSON values
    for comment in index.get(_COFACTOR, []):
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


def _extract_biophysicochemical_properties_raw(
    index: dict[str, list[JsonDict]],
) -> JsonDict:
    """Extract raw biophysicochemical properties from index."""
    extracted: JsonDict = {}  # Any: JSON values
    for comment in index.get(_BIOPHYSICOCHEMICAL_PROPERTIES, []):
        extracted.update(_extract_biophys_from_comment(comment))
    return extracted


def _extract_reaction_parts_raw(
    index: dict[str, list[JsonDict]],
) -> tuple[list[str], list[str]]:
    """Extract reaction names and EC numbers from catalytic comments."""
    reactions: list[str] = []
    ec_numbers: list[str] = []
    for comment in index.get(_CATALYTIC_ACTIVITY, []):
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
