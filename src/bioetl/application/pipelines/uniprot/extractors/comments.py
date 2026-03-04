"""Comment data extraction for UniProt records."""

from __future__ import annotations

__all__ = ["CommentExtractor"]


from collections.abc import Callable
from bioetl.domain.serialization import serialize_to_json
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


class CommentExtractor:
    """Extracts comment-related data from UniProt records.

    UniProt comments contain functional annotations like FUNCTION,
    SUBUNIT, CATALYTIC ACTIVITY, SUBCELLULAR LOCATION, etc.
    """

    @staticmethod
    def extract_text_values(
        comments: list[JsonDict],
        comment_type: str,
    ) -> list[str]:
        """Extract text values from comments of specific type.

        Args:
            comments: List of comment objects.
            comment_type: Comment type to filter by.

        Returns:
            List of extracted text values.
        """
        extracted: list[str] = []
        for comment in comments:
            if not _is_comment_of_type(comment, comment_type):
                continue

            texts = comment.get("texts", [])
            if isinstance(texts, list):
                for text in texts:
                    if isinstance(text, dict):
                        value = text.get("value")
                        if value:
                            extracted.append(str(value))
        return extracted

    @classmethod
    def extract_by_type(
        cls,
        comments: list[JsonDict] | None,
        comment_type: str,
    ) -> str | None:
        """Extract comments of specific type as JSON string.

        Args:
            comments: List of comment objects.
            comment_type: Comment type (FUNCTION, SUBUNIT, etc.)

        Returns:
            JSON string of comment values or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted = cls.extract_text_values(comments, comment_type)
        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_catalytic_activity(comments: list[JsonDict] | None) -> str | None:
        """Extract catalytic activity information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of catalytic activities or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[JsonDict] = []  # Any: JSON values
        for comment in comments:
            if not _is_comment_of_type(comment, "CATALYTIC ACTIVITY"):
                continue

            reaction = comment.get("reaction", {})
            if isinstance(reaction, dict):
                activity = _extract_reaction_data(reaction)
                if activity:
                    extracted.append(activity)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_subcellular_locations(comments: list[JsonDict] | None) -> str | None:
        """Extract subcellular location information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of subcellular locations or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[str] = []
        for comment in comments:
            if not _is_comment_of_type(comment, "SUBCELLULAR LOCATION"):
                continue

            locations = comment.get("subcellularLocations", [])
            if isinstance(locations, list):
                for loc in locations:
                    if isinstance(loc, dict):
                        value = _extract_location_value(loc)
                        if value:
                            extracted.append(value)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_alternative_products(comments: list[JsonDict] | None) -> str | None:
        """Extract alternative products (isoforms) information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of isoform information or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[JsonDict] = []  # Any: JSON values
        for comment in comments:
            if not _is_comment_of_type(comment, "ALTERNATIVE PRODUCTS"):
                continue

            isoforms = comment.get("isoforms", [])
            if isinstance(isoforms, list):
                for iso in isoforms:
                    if isinstance(iso, dict):
                        isoform_data = _build_isoform_data(iso)
                        if isoform_data:
                            extracted.append(isoform_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def count_isoforms(comments: list[JsonDict] | None) -> int | None:
        """Count the number of isoforms.

        Args:
            comments: List of comment objects.

        Returns:
            Number of isoforms or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        count = 0
        for comment in comments:
            if not _is_comment_of_type(comment, "ALTERNATIVE PRODUCTS"):
                continue

            isoforms = comment.get("isoforms", [])
            if isinstance(isoforms, list):
                count += len(isoforms)

        return count if count > 0 else None

    @staticmethod
    def extract_cofactors(comments: list[JsonDict] | None) -> str | None:
        """Extract cofactor information from COFACTOR comments.

        Cofactors are metal ions or organic molecules required for protein function.
        Each cofactor includes name and optional ChEBI cross-reference.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of cofactor objects with name and chebi_id, or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[JsonDict] = []  # Any: JSON values
        for comment in comments:
            if not _is_comment_of_type(comment, "COFACTOR"):
                continue

            cofactors = comment.get("cofactors", [])
            if not isinstance(cofactors, list):
                continue

            for cofactor in cofactors:
                if not isinstance(cofactor, dict):
                    continue
                cofactor_data = _extract_cofactor_entry(cofactor)
                if cofactor_data:
                    extracted.append(cofactor_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_biophysicochemical_properties(
        comments: list[JsonDict] | None,
    ) -> str | None:
        """Extract biophysicochemical properties from comments.

        Includes pH optima, temperature optima, kinetic parameters (Km, Vmax),
        and redox potential values.

        Args:
            comments: List of comment objects.

        Returns:
            JSON object with biophysicochemical properties, or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: JsonDict = {}  # Any: JSON values
        for comment in comments:
            if not _is_comment_of_type(comment, "BIOPHYSICOCHEMICAL PROPERTIES"):
                continue
            extracted.update(_extract_biophys_from_comment(comment))

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @classmethod
    def extract_induction(cls, comments: list[JsonDict] | None) -> str | None:
        """Extract induction information from INDUCTION comments.

        Describes conditions under which gene expression is induced.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of induction text values, or None.
        """
        return cls.extract_by_type(comments, "INDUCTION")

    @staticmethod
    def extract_isoform_details(
        comments: list[JsonDict] | None,
    ) -> dict[str, str | None]:
        """Extract detailed isoform information from ALTERNATIVE PRODUCTS.

        Parses isoform data to extract names, IDs, and synonyms separately.

        Args:
            comments: List of comment objects.

        Returns:
            Dict with keys:
                - isoform_names: JSON array of isoform names
                - isoform_ids: JSON array of isoform IDs (e.g., P12345-1)
                - isoform_synonyms: JSON array of synonyms
        """
        result: dict[str, str | None] = {
            section: None for section, _ in _ISOFORM_SECTION_NORMALIZERS
        }
        section_values: dict[str, list[str]] = {
            section: [] for section, _ in _ISOFORM_SECTION_NORMALIZERS
        }

        for isoform in _iter_alternative_product_isoforms(comments):
            for section, normalize in _ISOFORM_SECTION_NORMALIZERS:
                section_values[section].extend(normalize(isoform))

        for section, values in section_values.items():
            if values:
                result[section] = serialize_to_json(values, ensure_ascii=False)
        return result

    @staticmethod
    def extract_reactions(comments: list[JsonDict] | None) -> str | None:
        """Extract reaction names from CATALYTIC ACTIVITY comments.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of reaction name strings, or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        reactions: list[str] = []
        for comment in comments:
            if not _is_comment_of_type(comment, "CATALYTIC ACTIVITY"):
                continue

            reaction = comment.get("reaction", {})
            if isinstance(reaction, dict):
                name = reaction.get("name")
                if name:
                    reactions.append(str(name))

        return serialize_to_json(reactions, ensure_ascii=False) if reactions else None

    @staticmethod
    def extract_reaction_ec_numbers(comments: list[JsonDict] | None) -> str | None:
        """Extract EC numbers from CATALYTIC ACTIVITY comments.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of EC number strings, or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        ec_numbers: list[str] = []
        for comment in comments:
            if not _is_comment_of_type(comment, "CATALYTIC ACTIVITY"):
                continue

            reaction = comment.get("reaction", {})
            if isinstance(reaction, dict):
                ec_number = reaction.get("ecNumber")
                if ec_number:
                    ec_numbers.append(str(ec_number))

        return serialize_to_json(ec_numbers, ensure_ascii=False) if ec_numbers else None
