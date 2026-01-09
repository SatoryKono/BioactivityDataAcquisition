"""Comment data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.uniprot.extractors.utils import ExtractorUtils


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
        return ExtractorUtils.to_json(extracted)

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

        return ExtractorUtils.to_json(extracted)

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

        return ExtractorUtils.to_json(extracted)

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

        return ExtractorUtils.to_json(extracted)

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
