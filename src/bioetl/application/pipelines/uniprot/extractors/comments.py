"""Comment data extraction for UniProt records."""

from __future__ import annotations

__all__ = ["CommentExtractor", "_extract_texts_from_dict", "_is_comment_of_type"]

from bioetl.application.pipelines.uniprot.extractors._comment_helpers import (
    _ISOFORM_SECTION_NORMALIZERS,
    _build_isoform_data,
    _extract_biophys_from_comment,
    _extract_cofactor_entry,
    _extract_location_value,
    _extract_reaction_data,
    _extract_texts_from_dict,
    _is_comment_of_type,
    _iter_alternative_product_isoforms,
)
from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict


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
