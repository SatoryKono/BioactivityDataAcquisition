"""Utility functions for UniProt data extraction."""

from __future__ import annotations

__all__ = ["ExtractorHelper"]


from datetime import date
from typing import ClassVar

import orjson

from bioetl.domain.types import JsonDict


class ExtractorHelper:
    """Common utility methods for UniProt data extraction."""

    # Mapping of UniProt protein existence values
    EXISTENCE_MAP: ClassVar[dict[str, str]] = {
        "1: Evidence at protein level": "Evidence at protein level",
        "2: Evidence at transcript level": "Evidence at transcript level",
        "3: Inferred from homology": "Inferred from homology",
        "4: Predicted": "Predicted",
        "5: Uncertain": "Uncertain",
    }

    @staticmethod
    def serialize_list(value: object) -> str | None:
        """Serialize a list to JSON string.

        Args:
            value: List to serialize, or None/non-list.

        Returns:
            JSON string or None if empty/None/not a list.
        """
        if not value or not isinstance(value, list):
            return None
        result: str = orjson.dumps(value).decode("utf-8")
        return result

    @staticmethod
    def count_list(value: object) -> int | None:
        """Count items in a list.

        Args:
            value: List to count, or None/non-list.

        Returns:
            Count or None if not a list.
        """
        if value is None:
            return None
        if isinstance(value, list):
            return len(value)
        return None

    @staticmethod
    def is_reviewed(entry_type: object) -> bool:
        """Check if entry is Swiss-Prot (reviewed).

        Args:
            entry_type: Entry type string from record.

        Returns:
            True if reviewed (Swiss-Prot), False otherwise.
        """
        return "Swiss-Prot" in str(entry_type or "")

    @classmethod
    def extract_protein_existence(
        cls,
        existence: object,
    ) -> str | None:
        """Extract and normalize protein existence level.

        Args:
            existence: Raw protein existence value from API.

        Returns:
            Normalized protein existence level or None.
        """
        if not existence:
            return None
        existence_str = str(existence)
        return cls.EXISTENCE_MAP.get(existence_str, existence_str)

    @staticmethod
    def _extract_values_from_list(
        data: list[JsonDict],  # Any: untyped API JSON record
        key: str = "value",  # Any: record vals vary
    ) -> list[str]:
        """Extract values from a list of dictionaries.

        Args:
            data: List of dictionaries.
            key: Key to extract from each dictionary.

        Returns:
            List of extracted values.
        """
        values = [item.get(key) for item in data if isinstance(item, dict)]
        return [v for v in values if v]

    @staticmethod
    # Any: JSON vals
    def extract_short_names(
        recommended_name: JsonDict | None,  # Any: untyped API JSON record
    ) -> str | None:  # Any: untyped API JSON record
        """Extract short names from recommended name.

        Args:
            recommended_name: proteinDescription.recommendedName dict.

        Returns:
            JSON array of short names or None.
        """
        if not recommended_name:
            return None
        short_names = recommended_name.get("shortNames")
        if not isinstance(short_names, list):
            return None
        values = ExtractorHelper._extract_values_from_list(short_names)
        return orjson.dumps(values).decode("utf-8") if values else None

    @staticmethod
    def extract_alternative_names(protein_desc: object) -> str | None:
        """Extract alternative protein names.

        Args:
            protein_desc: proteinDescription dict.

        Returns:
            JSON array of alternative names or None.
        """
        if not protein_desc or not isinstance(protein_desc, dict):
            return None
        alt_names = protein_desc.get("alternativeNames")
        if not isinstance(alt_names, list):
            return None

        values = []
        for alt in alt_names:
            if not isinstance(alt, dict):
                continue
            full_name = alt.get("fullName")
            if isinstance(full_name, dict):
                name = full_name.get("value")
                if name:
                    values.append(name)
        return orjson.dumps(values).decode("utf-8") if values else None

    @staticmethod
    # Any: JSON vals
    def extract_ec_numbers(
        recommended_name: JsonDict | None,  # Any: untyped API JSON record
    ) -> str | None:  # Any: untyped API JSON record
        """Extract EC numbers from recommended name.

        Args:
            recommended_name: proteinDescription.recommendedName dict.

        Returns:
            JSON array of EC numbers or None.
        """
        if not recommended_name:
            return None
        ec_numbers = recommended_name.get("ecNumbers")
        if not isinstance(ec_numbers, list):
            return None
        values = ExtractorHelper._extract_values_from_list(ec_numbers)
        return orjson.dumps(values).decode("utf-8") if values else None

    @staticmethod
    def parse_uniprot_date(date_str: object) -> date | None:
        """Parse UniProt date string to datetime.date.

        UniProt API returns dates in ISO 8601 format (YYYY-MM-DD).

        Args:
            date_str: Date string from UniProt API (e.g., "2000-12-01").

        Returns:
            Parsed date object or None if invalid/empty.
        """
        if not date_str or not isinstance(date_str, str):
            return None
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            return None
