"""Shared helper functions for UniProt comment extraction."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.types import JsonDict


def _is_comment_of_type(comment: object, comment_type: str) -> bool:
    """Check if comment matches the specified type.

    Args:
        comment: Comment object to check.
        comment_type: Expected comment type.

    Returns:
        True if comment is a dict with matching commentType.
    """
    return isinstance(comment, dict) and comment.get("commentType") == comment_type


def _extract_reaction_data(
    reaction: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> JsonDict:  # Any: untyped JSON fragment from UniProt API
    """Extract reaction data from catalytic activity.

    Args:
        reaction: Reaction dict from comment.

    Returns:
        Activity dict with reaction and ec_number fields.
    """
    activity: JsonDict = {}  # Any: JSON values
    if reaction.get("name"):
        activity["reaction"] = reaction.get("name")
    if reaction.get("ecNumber"):
        activity["ec_number"] = reaction.get("ecNumber")
    return activity


def _extract_location_value(loc: JsonDict) -> str | None:  # Any: JSON values
    """Extract location value from subcellular location entry.

    Args:
        loc: Location entry dict.

    Returns:
        Location value string or None.
    """
    location = loc.get("location", {})
    if isinstance(location, dict):
        value = location.get("value")
        if value:
            return str(value)
    return None


def _build_isoform_data(iso: JsonDict) -> JsonDict:  # Any: JSON values
    """Build isoform data from isoform entry.

    Args:
        iso: Isoform entry dict.

    Returns:
        Isoform data dict with ids and name.
    """
    isoform_data: JsonDict = {}  # Any: JSON values
    isoform_ids = iso.get("isoformIds", [])
    if isoform_ids:
        isoform_data["ids"] = isoform_ids
    name = iso.get("name", {})
    if isinstance(name, dict) and name.get("value"):
        isoform_data["name"] = name.get("value")
    return isoform_data


def _extract_isoform_id_values(
    isoform: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> list[str]:
    """Extract normalized isoform IDs."""
    raw_ids = isoform.get("isoformIds", [])
    if not isinstance(raw_ids, list):
        return []
    return [str(iso_id) for iso_id in raw_ids if iso_id]


def _extract_isoform_name_values(
    isoform: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> list[str]:
    """Extract normalized isoform primary name."""
    name = isoform.get("name", {})
    if isinstance(name, dict) and name.get("value"):
        return [str(name["value"])]
    return []


def _extract_isoform_synonym_values(
    isoform: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> list[str]:
    """Extract normalized isoform synonyms."""
    raw_synonyms = isoform.get("synonyms", [])
    if not isinstance(raw_synonyms, list):
        return []
    return [
        str(item["value"])
        for item in raw_synonyms
        if isinstance(item, dict) and item.get("value")
    ]


def _iter_alternative_product_isoforms(
    comments: list[JsonDict] | None,
) -> list[JsonDict]:
    """Collect ALTERNATIVE PRODUCTS isoform dicts."""
    if not comments or not isinstance(comments, list):
        return []

    isoforms: list[JsonDict] = []  # Any: untyped UniProt API JSON objects
    for comment in comments:
        if not _is_comment_of_type(comment, "ALTERNATIVE PRODUCTS"):
            continue
        comment_isoforms = comment.get("isoforms", [])
        if not isinstance(comment_isoforms, list):
            continue
        isoforms.extend(item for item in comment_isoforms if isinstance(item, dict))
    return isoforms


_IsoformPayload = JsonDict  # Any: untyped UniProt API JSON objects
_IsoformExtractor = Callable[[_IsoformPayload], list[str]]
_ISOFORM_SECTION_NORMALIZERS: tuple[tuple[str, _IsoformExtractor], ...] = (
    ("isoform_names", _extract_isoform_name_values),
    ("isoform_ids", _extract_isoform_id_values),
    ("isoform_synonyms", _extract_isoform_synonym_values),
)


def _extract_texts_from_dict(
    data: JsonDict | None,  # Any: untyped JSON fragment from UniProt API
) -> list[str]:
    """Extract text values from a dict with 'texts' key.

    Args:
        data: Dict containing 'texts' list.

    Returns:
        List of extracted text values.
    """
    if not isinstance(data, dict):
        return []
    texts = data.get("texts", [])
    if not isinstance(texts, list):
        return []
    return [
        str(t.get("value")) for t in texts if isinstance(t, dict) and t.get("value")
    ]


def _extract_cofactor_entry(
    cofactor: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> JsonDict:  # Any: untyped JSON fragment from UniProt API
    """Extract data from a single cofactor entry.

    Args:
        cofactor: Cofactor dict from comment.

    Returns:
        Cofactor data dict with name, chebi_id, and optional note.
    """
    cofactor_data: JsonDict = {}  # Any: JSON values

    name = cofactor.get("name")
    if name:
        cofactor_data["name"] = str(name)

    xref = cofactor.get("cofactorCrossReference")
    if isinstance(xref, dict):
        chebi_id = xref.get("id")
        if chebi_id:
            cofactor_data["chebi_id"] = str(chebi_id)

    note = cofactor.get("note")
    notes = _extract_texts_from_dict(note)
    if notes:
        cofactor_data["note"] = notes[0] if len(notes) == 1 else notes

    return cofactor_data


def _extract_km_entry(km: JsonDict) -> JsonDict:  # Any: JSON values
    """Extract Michaelis constant entry."""
    km_entry: JsonDict = {}  # Any: JSON values
    if km.get("constant"):
        km_entry["value"] = km["constant"]
    if km.get("unit"):
        km_entry["unit"] = km["unit"]
    if km.get("substrate"):
        km_entry["substrate"] = km["substrate"]
    return km_entry


def _extract_vmax_entry(vmax: JsonDict) -> JsonDict:  # Any: JSON values
    """Extract maximum velocity entry."""
    vmax_entry: JsonDict = {}  # Any: JSON values
    if vmax.get("velocity"):
        vmax_entry["value"] = vmax["velocity"]
    if vmax.get("unit"):
        vmax_entry["unit"] = vmax["unit"]
    if vmax.get("enzyme"):
        vmax_entry["enzyme"] = vmax["enzyme"]
    return vmax_entry


def _extract_list_entries(
    data_list: list[JsonDict] | None,
    extractor: Callable[[JsonDict], JsonDict],
) -> list[JsonDict]:
    """Extract entries from a list using the provided extractor function."""
    if not isinstance(data_list, list) or not data_list:
        return []
    return [
        e
        for e in (extractor(item) for item in data_list if isinstance(item, dict))
        if e
    ]


def _extract_kinetic_parameters(
    kinetics: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> JsonDict:  # Any: untyped JSON fragment from UniProt API
    """Extract kinetic parameters (Km, Vmax) from kineticParameters dict."""
    kinetic_data: JsonDict = {}  # Any: JSON values

    km_values = _extract_list_entries(
        kinetics.get("michaelisConstants"), _extract_km_entry
    )
    if km_values:
        kinetic_data["km"] = km_values

    vmax_values = _extract_list_entries(
        kinetics.get("maximumVelocities"), _extract_vmax_entry
    )
    if vmax_values:
        kinetic_data["vmax"] = vmax_values

    notes = _extract_texts_from_dict(kinetics.get("note"))
    if notes:
        kinetic_data["note"] = notes

    return kinetic_data


def _extract_absorption_data(
    absorption: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> JsonDict:  # Any: untyped JSON fragment from UniProt API
    """Extract absorption (spectroscopic) data."""
    abs_data: JsonDict = {}  # Any: JSON values
    if absorption.get("max"):
        abs_data["max"] = absorption["max"]
    notes = _extract_texts_from_dict(absorption.get("note"))
    if notes:
        abs_data["note"] = notes
    return abs_data


def _extract_biophys_from_comment(
    comment: JsonDict,  # Any: untyped JSON fragment from UniProt API
) -> JsonDict:  # Any: untyped JSON fragment from UniProt API
    """Extract biophysicochemical data from a single comment.

    Args:
        comment: BIOPHYSICOCHEMICAL PROPERTIES comment dict.

    Returns:
        Dict with extracted properties.
    """
    result: JsonDict = {}  # Any: JSON values

    # Simple text extractions
    ph_values = _extract_texts_from_dict(comment.get("phDependence"))
    if ph_values:
        result["ph_dependence"] = ph_values

    temp_values = _extract_texts_from_dict(comment.get("temperatureDependence"))
    if temp_values:
        result["temperature_dependence"] = temp_values

    redox_values = _extract_texts_from_dict(comment.get("redoxPotential"))
    if redox_values:
        result["redox_potential"] = redox_values

    # Complex extractions
    kinetics = comment.get("kineticParameters")
    if isinstance(kinetics, dict):
        kinetic_data = _extract_kinetic_parameters(kinetics)
        if kinetic_data:
            result["kinetic_parameters"] = kinetic_data

    absorption = comment.get("absorption")
    if isinstance(absorption, dict):
        abs_data = _extract_absorption_data(absorption)
        if abs_data:
            result["absorption"] = abs_data

    return result
