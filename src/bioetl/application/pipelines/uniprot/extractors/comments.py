"""Comment data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json


def _is_comment_of_type(comment: Any, comment_type: str) -> bool:  # Any: JSON
    """Check if comment matches the specified type.

    Args:
        comment: Comment object to check.
        comment_type: Expected comment type.

    Returns:
        True if comment is a dict with matching commentType.
    """
    return isinstance(comment, dict) and comment.get("commentType") == comment_type


def _extract_reaction_data(
    reaction: dict[str, Any],  # Any: untyped JSON fragment from UniProt API
) -> dict[str, Any]:  # Any: untyped JSON fragment from UniProt API
    """Extract reaction data from catalytic activity.

    Args:
        reaction: Reaction dict from comment.

    Returns:
        Activity dict with reaction and ec_number fields.
    """
    activity: dict[str, Any] = {}  # Any: JSON values
    if reaction.get("name"):
        activity["reaction"] = reaction.get("name")
    if reaction.get("ecNumber"):
        activity["ec_number"] = reaction.get("ecNumber")
    return activity


def _extract_location_value(loc: dict[str, Any]) -> str | None:  # Any: JSON values
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


def _build_isoform_data(iso: dict[str, Any]) -> dict[str, Any]:  # Any: JSON values
    """Build isoform data from isoform entry.

    Args:
        iso: Isoform entry dict.

    Returns:
        Isoform data dict with ids and name.
    """
    isoform_data: dict[str, Any] = {}  # Any: JSON values
    isoform_ids = iso.get("isoformIds", [])
    if isoform_ids:
        isoform_data["ids"] = isoform_ids
    name = iso.get("name", {})
    if isinstance(name, dict) and name.get("value"):
        isoform_data["name"] = name.get("value")
    return isoform_data


def _extract_texts_from_dict(
    data: dict[str, Any] | None,  # Any: untyped JSON fragment from UniProt API
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
    cofactor: dict[str, Any],  # Any: untyped JSON fragment from UniProt API
) -> dict[str, Any]:  # Any: untyped JSON fragment from UniProt API
    """Extract data from a single cofactor entry.

    Args:
        cofactor: Cofactor dict from comment.

    Returns:
        Cofactor data dict with name, chebi_id, and optional note.
    """
    cofactor_data: dict[str, Any] = {}  # Any: JSON values

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


def _extract_km_entry(km: dict[str, Any]) -> dict[str, Any]:  # Any: JSON values
    """Extract Michaelis constant entry."""
    km_entry: dict[str, Any] = {}  # Any: JSON values
    if km.get("constant"):
        km_entry["value"] = km["constant"]
    if km.get("unit"):
        km_entry["unit"] = km["unit"]
    if km.get("substrate"):
        km_entry["substrate"] = km["substrate"]
    return km_entry


def _extract_vmax_entry(vmax: dict[str, Any]) -> dict[str, Any]:  # Any: JSON values
    """Extract maximum velocity entry."""
    vmax_entry: dict[str, Any] = {}  # Any: JSON values
    if vmax.get("velocity"):
        vmax_entry["value"] = vmax["velocity"]
    if vmax.get("unit"):
        vmax_entry["unit"] = vmax["unit"]
    if vmax.get("enzyme"):
        vmax_entry["enzyme"] = vmax["enzyme"]
    return vmax_entry


def _extract_list_entries(
    data_list: Any,  # Any: untyped UniProt JSON list
    extractor: Any,  # Any: dynamic extractor callable
) -> list[dict[str, Any]]:  # Any: JSON
    """Extract entries from a list using the provided extractor function."""
    if not isinstance(data_list, list) or not data_list:
        return []
    return [
        e
        for e in (extractor(item) for item in data_list if isinstance(item, dict))
        if e
    ]


def _extract_kinetic_parameters(
    kinetics: dict[str, Any],  # Any: untyped JSON fragment from UniProt API
) -> dict[str, Any]:  # Any: untyped JSON fragment from UniProt API
    """Extract kinetic parameters (Km, Vmax) from kineticParameters dict."""
    kinetic_data: dict[str, Any] = {}  # Any: JSON values

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
    absorption: dict[str, Any],  # Any: untyped JSON fragment from UniProt API
) -> dict[str, Any]:  # Any: untyped JSON fragment from UniProt API
    """Extract absorption (spectroscopic) data."""
    abs_data: dict[str, Any] = {}  # Any: JSON values
    if absorption.get("max"):
        abs_data["max"] = absorption["max"]
    notes = _extract_texts_from_dict(absorption.get("note"))
    if notes:
        abs_data["note"] = notes
    return abs_data


def _extract_biophys_from_comment(
    comment: dict[str, Any],  # Any: untyped JSON fragment from UniProt API
) -> dict[str, Any]:  # Any: untyped JSON fragment from UniProt API
    """Extract biophysicochemical data from a single comment.

    Args:
        comment: BIOPHYSICOCHEMICAL PROPERTIES comment dict.

    Returns:
        Dict with extracted properties.
    """
    result: dict[str, Any] = {}  # Any: JSON values

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
        comments: list[Any],  # Any: untyped JSON fragment from UniProt API
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
        comments: Any,  # Any: untyped API JSON
        comment_type: str,  # Any: untyped UniProt API JSON
    ) -> str | None:  # Any: untyped UniProt JSON
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
    def extract_catalytic_activity(comments: Any) -> str | None:  # Any: untyped JSON
        """Extract catalytic activity information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of catalytic activities or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []  # Any: JSON values
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
    def extract_subcellular_locations(comments: Any) -> str | None:  # Any: untyped JSON
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
    def extract_alternative_products(comments: Any) -> str | None:  # Any: untyped JSON
        """Extract alternative products (isoforms) information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of isoform information or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []  # Any: JSON values
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
    def count_isoforms(comments: Any) -> int | None:  # Any: untyped API JSON
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
    def extract_cofactors(comments: Any) -> str | None:  # Any: untyped API JSON
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

        extracted: list[dict[str, Any]] = []  # Any: JSON values
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
        comments: Any,  # Any: untyped UniProt API JSON
    ) -> str | None:  # Any: untyped UniProt JSON
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

        extracted: dict[str, Any] = {}  # Any: JSON values
        for comment in comments:
            if not _is_comment_of_type(comment, "BIOPHYSICOCHEMICAL PROPERTIES"):
                continue
            extracted.update(_extract_biophys_from_comment(comment))

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @classmethod
    def extract_induction(cls, comments: Any) -> str | None:  # Any: untyped API JSON
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
        comments: Any,  # Any: untyped UniProt API JSON
    ) -> dict[str, str | None]:  # Any: untyped UniProt JSON
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
            "isoform_names": None,
            "isoform_ids": None,
            "isoform_synonyms": None,
        }

        if not comments or not isinstance(comments, list):
            return result

        names: list[str] = []
        ids: list[str] = []
        synonyms: list[str] = []

        for comment in comments:
            if not _is_comment_of_type(comment, "ALTERNATIVE PRODUCTS"):
                continue

            isoforms = comment.get("isoforms", [])
            if not isinstance(isoforms, list):
                continue

            for iso in isoforms:
                if not isinstance(iso, dict):
                    continue

                # Extract isoform IDs
                isoform_ids = iso.get("isoformIds", [])
                if isinstance(isoform_ids, list):
                    for iso_id in isoform_ids:
                        if iso_id:
                            ids.append(str(iso_id))

                # Extract isoform name
                name = iso.get("name", {})
                if isinstance(name, dict) and name.get("value"):
                    names.append(str(name["value"]))

                # Extract synonyms
                iso_synonyms = iso.get("synonyms", [])
                if isinstance(iso_synonyms, list):
                    for syn in iso_synonyms:
                        if isinstance(syn, dict) and syn.get("value"):
                            synonyms.append(str(syn["value"]))

        if names:
            result["isoform_names"] = serialize_to_json(names, ensure_ascii=False)
        if ids:
            result["isoform_ids"] = serialize_to_json(ids, ensure_ascii=False)
        if synonyms:
            result["isoform_synonyms"] = serialize_to_json(synonyms, ensure_ascii=False)

        return result

    @staticmethod
    def extract_reactions(comments: Any) -> str | None:  # Any: untyped API JSON
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
    def extract_reaction_ec_numbers(comments: Any) -> str | None:  # Any: untyped JSON
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
