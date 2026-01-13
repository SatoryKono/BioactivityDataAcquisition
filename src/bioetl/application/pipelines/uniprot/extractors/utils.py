"""Utility functions for UniProt data extraction."""

from __future__ import annotations

from typing import Any, ClassVar

import orjson


class ExtractorUtils:
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
    def serialize_list(value: Any) -> str | None:
        """Serialize a list to JSON string.

        Args:
            value: List to serialize, or None/non-list.

        Returns:
            JSON string or None if empty/None/not a list.
        """
        if not value or not isinstance(value, list):
            return None
        return orjson.dumps(value).decode("utf-8")

    @staticmethod
    def count_list(value: Any) -> int | None:
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
    def is_reviewed(entry_type: Any) -> bool:
        """Check if entry is Swiss-Prot (reviewed).

        Args:
            entry_type: Entry type string from record.

        Returns:
            True if reviewed (Swiss-Prot), False otherwise.
        """
        return "Swiss-Prot" in str(entry_type or "")

    @classmethod
    def extract_protein_existence(cls, existence: Any) -> str | None:
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
    def extract_short_names(recommended_name: dict[str, Any] | None) -> str | None:
        """Extract short names from recommended name.

        Args:
            recommended_name: proteinDescription.recommendedName dict.

        Returns:
            JSON array of short names or None.
        """
        if not recommended_name:
            return None
        short_names = recommended_name.get("shortNames", [])
        if not isinstance(short_names, list):
            return None
        values = [sn.get("value") for sn in short_names if isinstance(sn, dict)]
        values = [v for v in values if v]
        return orjson.dumps(values).decode("utf-8") if values else None

    @staticmethod
    def extract_alternative_names(protein_desc: Any) -> str | None:
        """Extract alternative protein names.

        Args:
            protein_desc: proteinDescription dict.

        Returns:
            JSON array of alternative names or None.
        """
        if not protein_desc or not isinstance(protein_desc, dict):
            return None
        alt_names = protein_desc.get("alternativeNames", [])
        if not isinstance(alt_names, list):
            return None

        values = []
        for alt in alt_names:
            if not isinstance(alt, dict):
                continue
            full_name = alt.get("fullName", {})
            if isinstance(full_name, dict):
                name = full_name.get("value")
                if name:
                    values.append(name)
        return orjson.dumps(values).decode("utf-8") if values else None

    @staticmethod
    def extract_ec_numbers(recommended_name: dict[str, Any] | None) -> str | None:
        """Extract EC numbers from recommended name.

        Args:
            recommended_name: proteinDescription.recommendedName dict.

        Returns:
            JSON array of EC numbers or None.
        """
        if not recommended_name:
            return None
        ec_numbers = recommended_name.get("ecNumbers", [])
        if not isinstance(ec_numbers, list):
            return None
        values = [ec.get("value") for ec in ec_numbers if isinstance(ec, dict)]
        values = [v for v in values if v]
        return orjson.dumps(values).decode("utf-8") if values else None
