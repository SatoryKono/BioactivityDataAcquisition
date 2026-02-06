"""Utility functions for UniProt extractors to reduce code duplication and complexity.

This module contains the ExtractorUtils class which provides static methods
for common text processing and data extraction tasks used across multiple
UniProt extractor classes.
"""

from typing import Any

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
