"""Utility functions for UniProt extractors to reduce code duplication and complexity.

This module contains the ExtractorUtils class which provides static methods
for common text processing and data extraction tasks used across multiple
UniProt extractor classes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import IsoformNote


class ExtractorUtils:
    """Shared utility methods for UniProt extractors."""

    @staticmethod
    def clean_text(text: str | None) -> str | None:
        """Clean text by stripping whitespace and removing trailing periods."""
        if not text:
            return None
        text = text.strip()
        if text.endswith("."):
            text = text[:-1]
        return text.strip() or None

    @staticmethod
    def split_semicolon(text: str | None) -> list[str]:
        """Split text by semicolon and clean each part."""
        if not text:
            return []
        return [cleaned for part in text.split(";") if (cleaned := ExtractorUtils.clean_text(part))]

    @staticmethod
    def process_single_isoform_note(
        iso_id: str, note_text: str, isoform_notes: list[IsoformNote]
    ) -> None:
        """Process a single isoform note text and append to the list."""
        if not note_text:
            return

        # Clean up the note text
        note_text = note_text.strip()
        if not note_text:
            return

        # Check if note already exists for this isoform
        for existing in isoform_notes:
            if existing.isoform_id == iso_id and existing.note == note_text:
                return

        isoform_notes.append(IsoformNote(isoform_id=iso_id, note=note_text))

    @staticmethod
    def extract_evidence(element: dict[str, Any]) -> list[str]:
        """Extract evidence codes from an element."""
        evidence = element.get("@evidence", "")
        if not evidence:
            return []
        return [e.strip() for e in evidence.split(" ") if e.strip()]

    @staticmethod
    def serialize_list(data: Any) -> str | None:
        """Serialize a list to JSON string, or return None if empty.

        Args:
            data: List or item to serialize.

        Returns:
            JSON string or None.
        """
        if not data:
            return None
        if isinstance(data, list) and not data:
            return None
        return serialize_to_json(data, ensure_ascii=False)

    @staticmethod
    def extract_short_names(recommended_name: Any) -> str | None:
        """Extract short names from recommendedName.

        Args:
            recommended_name: dict or list of recommended names.

        Returns:
            JSON array of short names or None.
        """
        if not recommended_name or not isinstance(recommended_name, dict):
            return None

        short_names = recommended_name.get("shortName", [])
        if not short_names:
            return None

        if isinstance(short_names, dict):
            short_names = [short_names]

        names = []
        for sn in short_names:
            if isinstance(sn, dict) and (val := sn.get("value")):
                names.append(val)
            elif isinstance(sn, str):
                names.append(sn)

        return serialize_to_json(names, ensure_ascii=False) if names else None

    @staticmethod
    def extract_alternative_names(protein_desc: Any) -> str | None:
        """Extract alternative names.

        Args:
            protein_desc: proteinDescription dictionary.

        Returns:
            JSON array of alternative names or None.
        """
        if not protein_desc or not isinstance(protein_desc, dict):
            return None

        alt_names_data = protein_desc.get("alternativeName", [])
        if not alt_names_data:
            return None

        if isinstance(alt_names_data, dict):
            alt_names_data = [alt_names_data]

        names = []
        for alt in alt_names_data:
            if not isinstance(alt, dict):
                continue

            # Full names
            if full := alt.get("fullName"):
                if isinstance(full, dict) and (val := full.get("value")):
                    names.append(val)
                elif isinstance(full, str):
                    names.append(full)

            # Short names
            if short := alt.get("shortName"):
                if isinstance(short, list):
                    for s in short:
                        if isinstance(s, dict) and (val := s.get("value")):
                            names.append(val)
                elif isinstance(short, dict) and (val := short.get("value")):
                    names.append(val)

        return serialize_to_json(names, ensure_ascii=False) if names else None

    @staticmethod
    def extract_ec_numbers(recommended_name: Any) -> str | None:
        """Extract EC numbers from recommendedName.

        Args:
            recommended_name: recommendedName dictionary.

        Returns:
            JSON array of EC numbers or None.
        """
        if not recommended_name or not isinstance(recommended_name, dict):
            return None

        ec_numbers = recommended_name.get("ecNumber", [])
        if not ec_numbers:
            return None

        if isinstance(ec_numbers, dict):
            ec_numbers = [ec_numbers]

        ecs = []
        for ec in ec_numbers:
            if isinstance(ec, dict) and (val := ec.get("value")):
                ecs.append(val)
            elif isinstance(ec, str):
                ecs.append(ec)

        return serialize_to_json(ecs, ensure_ascii=False) if ecs else None

    @staticmethod
    def extract_protein_existence(protein_existence: Any) -> str | None:
        """Extract protein existence level.

        Args:
            protein_existence: proteinExistence dictionary.

        Returns:
            Existence type string or None.
        """
        if not protein_existence or not isinstance(protein_existence, dict):
            return None
        val = protein_existence.get("@type")
        return str(val) if val else None

    @staticmethod
    def is_reviewed(entry_type: Any) -> bool:
        """Check if entry is reviewed (Swiss-Prot).

        Args:
            entry_type: entryType string ("Swiss-Prot" or "TrEMBL").

        Returns:
            True if reviewed, False otherwise.
        """
        return str(entry_type) == "Swiss-Prot"

    @staticmethod
    def parse_uniprot_date(date_str: str | None) -> date | None:
        """Parse UniProt date string (YYYY-MM-DD).

        Args:
            date_str: Date string.

        Returns:
            date object or None.
        """
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def count_list(data: Any) -> int:
        """Count items in a list or single item.

        Args:
            data: List, dict (single item), or None.

        Returns:
            Count of items.
        """
        if not data:
            return 0
        if isinstance(data, list):
            return len(data)
        return 1
