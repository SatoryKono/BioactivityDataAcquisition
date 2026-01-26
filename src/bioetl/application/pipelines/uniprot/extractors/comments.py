"""Comment data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json


def _is_comment_of_type(comment: Any, comment_type: str) -> bool:
    """Check if comment matches the specified type.

    Args:
        comment: Comment object to check.
        comment_type: Expected comment type.

    Returns:
        True if comment is a dict with matching commentType.
    """
    return isinstance(comment, dict) and comment.get("commentType") == comment_type


def _extract_reaction_data(reaction: dict[str, Any]) -> dict[str, Any]:
    """Extract reaction data from catalytic activity.

    Args:
        reaction: Reaction dict from comment.

    Returns:
        Activity dict with reaction and ec_number fields.
    """
    activity: dict[str, Any] = {}
    if reaction.get("name"):
        activity["reaction"] = reaction.get("name")
    if reaction.get("ecNumber"):
        activity["ec_number"] = reaction.get("ecNumber")
    return activity


def _extract_location_value(loc: dict[str, Any]) -> str | None:
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


def _build_isoform_data(iso: dict[str, Any]) -> dict[str, Any]:
    """Build isoform data from isoform entry.

    Args:
        iso: Isoform entry dict.

    Returns:
        Isoform data dict with ids and name.
    """
    isoform_data: dict[str, Any] = {}
    isoform_ids = iso.get("isoformIds", [])
    if isoform_ids:
        isoform_data["ids"] = isoform_ids
    name = iso.get("name", {})
    if isinstance(name, dict) and name.get("value"):
        isoform_data["name"] = name.get("value")
    return isoform_data


class CommentExtractor:
    """Extracts comment-related data from UniProt records.

    UniProt comments contain functional annotations like FUNCTION,
    SUBUNIT, CATALYTIC ACTIVITY, SUBCELLULAR LOCATION, etc.
    """

    @staticmethod
    def extract_text_values(comments: list[Any], comment_type: str) -> list[str]:
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
    def extract_by_type(cls, comments: Any, comment_type: str) -> str | None:
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
    def extract_catalytic_activity(comments: Any) -> str | None:
        """Extract catalytic activity information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of catalytic activities or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []
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
    def extract_subcellular_locations(comments: Any) -> str | None:
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
    def extract_alternative_products(comments: Any) -> str | None:
        """Extract alternative products (isoforms) information.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of isoform information or None.
        """
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []
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
    def count_isoforms(comments: Any) -> int | None:
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
    def extract_cofactors(comments: Any) -> str | None:
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

        extracted: list[dict[str, Any]] = []
        for comment in comments:
            if not _is_comment_of_type(comment, "COFACTOR"):
                continue

            cofactors = comment.get("cofactors", [])
            if not isinstance(cofactors, list):
                continue

            for cofactor in cofactors:
                if not isinstance(cofactor, dict):
                    continue

                cofactor_data: dict[str, Any] = {}

                # Extract cofactor name
                name = cofactor.get("name")
                if name:
                    cofactor_data["name"] = str(name)

                # Extract ChEBI cross-reference if available
                xref = cofactor.get("cofactorCrossReference")
                if isinstance(xref, dict):
                    chebi_id = xref.get("id")
                    if chebi_id:
                        cofactor_data["chebi_id"] = str(chebi_id)

                # Extract note if available
                note = cofactor.get("note")
                if isinstance(note, dict):
                    note_texts = note.get("texts", [])
                    if isinstance(note_texts, list) and note_texts:
                        notes = [
                            str(t.get("value"))
                            for t in note_texts
                            if isinstance(t, dict) and t.get("value")
                        ]
                        if notes:
                            cofactor_data["note"] = notes[0] if len(notes) == 1 else notes

                if cofactor_data:
                    extracted.append(cofactor_data)

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @staticmethod
    def extract_biophysicochemical_properties(comments: Any) -> str | None:
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

        extracted: dict[str, Any] = {}
        for comment in comments:
            if not _is_comment_of_type(comment, "BIOPHYSICOCHEMICAL PROPERTIES"):
                continue

            # Extract pH dependence
            ph_dep = comment.get("phDependence")
            if isinstance(ph_dep, dict):
                texts = ph_dep.get("texts", [])
                if isinstance(texts, list):
                    ph_values = [
                        str(t.get("value"))
                        for t in texts
                        if isinstance(t, dict) and t.get("value")
                    ]
                    if ph_values:
                        extracted["ph_dependence"] = ph_values

            # Extract temperature dependence
            temp_dep = comment.get("temperatureDependence")
            if isinstance(temp_dep, dict):
                texts = temp_dep.get("texts", [])
                if isinstance(texts, list):
                    temp_values = [
                        str(t.get("value"))
                        for t in texts
                        if isinstance(t, dict) and t.get("value")
                    ]
                    if temp_values:
                        extracted["temperature_dependence"] = temp_values

            # Extract kinetic parameters
            kinetics = comment.get("kineticParameters")
            if isinstance(kinetics, dict):
                kinetic_data: dict[str, Any] = {}

                # Michaelis constants (Km)
                km_list = kinetics.get("michaelisConstants", [])
                if isinstance(km_list, list) and km_list:
                    km_values = []
                    for km in km_list:
                        if isinstance(km, dict):
                            km_entry: dict[str, Any] = {}
                            if km.get("constant"):
                                km_entry["value"] = km["constant"]
                            if km.get("unit"):
                                km_entry["unit"] = km["unit"]
                            if km.get("substrate"):
                                km_entry["substrate"] = km["substrate"]
                            if km_entry:
                                km_values.append(km_entry)
                    if km_values:
                        kinetic_data["km"] = km_values

                # Maximum velocities (Vmax)
                vmax_list = kinetics.get("maximumVelocities", [])
                if isinstance(vmax_list, list) and vmax_list:
                    vmax_values = []
                    for vmax in vmax_list:
                        if isinstance(vmax, dict):
                            vmax_entry: dict[str, Any] = {}
                            if vmax.get("velocity"):
                                vmax_entry["value"] = vmax["velocity"]
                            if vmax.get("unit"):
                                vmax_entry["unit"] = vmax["unit"]
                            if vmax.get("enzyme"):
                                vmax_entry["enzyme"] = vmax["enzyme"]
                            if vmax_entry:
                                vmax_values.append(vmax_entry)
                    if vmax_values:
                        kinetic_data["vmax"] = vmax_values

                # Note/text
                note = kinetics.get("note")
                if isinstance(note, dict):
                    note_texts = note.get("texts", [])
                    if isinstance(note_texts, list):
                        notes = [
                            str(t.get("value"))
                            for t in note_texts
                            if isinstance(t, dict) and t.get("value")
                        ]
                        if notes:
                            kinetic_data["note"] = notes

                if kinetic_data:
                    extracted["kinetic_parameters"] = kinetic_data

            # Extract redox potential
            redox = comment.get("redoxPotential")
            if isinstance(redox, dict):
                texts = redox.get("texts", [])
                if isinstance(texts, list):
                    redox_values = [
                        str(t.get("value"))
                        for t in texts
                        if isinstance(t, dict) and t.get("value")
                    ]
                    if redox_values:
                        extracted["redox_potential"] = redox_values

            # Extract absorption (spectroscopic data)
            absorption = comment.get("absorption")
            if isinstance(absorption, dict):
                abs_data: dict[str, Any] = {}
                if absorption.get("max"):
                    abs_data["max"] = absorption["max"]
                note = absorption.get("note")
                if isinstance(note, dict):
                    note_texts = note.get("texts", [])
                    if isinstance(note_texts, list):
                        notes = [
                            str(t.get("value"))
                            for t in note_texts
                            if isinstance(t, dict) and t.get("value")
                        ]
                        if notes:
                            abs_data["note"] = notes
                if abs_data:
                    extracted["absorption"] = abs_data

        return serialize_to_json(extracted, ensure_ascii=False) if extracted else None

    @classmethod
    def extract_induction(cls, comments: Any) -> str | None:
        """Extract induction information from INDUCTION comments.

        Describes conditions under which gene expression is induced.

        Args:
            comments: List of comment objects.

        Returns:
            JSON array of induction text values, or None.
        """
        return cls.extract_by_type(comments, "INDUCTION")
