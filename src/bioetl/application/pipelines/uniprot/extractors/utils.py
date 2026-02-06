from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.types import IsoformNote


def clean_text(text: str) -> str:
    """Removes trailing periods and excessive whitespace from text."""
    if not text:
        return ""
    text = text.strip()
    if text.endswith("."):
        text = text[:-1]
    return text.strip()


def split_semicolon(text: str) -> list[str]:
    """Splits a semicolon-separated string into a list of strings."""
    if not text:
        return []
    return [t.strip() for t in text.split(";") if t.strip()]


def process_single_isoform_note(
    note_text: str, isoform_ids: list[str], result: dict[str, list[IsoformNote]]
) -> None:
    """Processes a single isoform note and updates the result dictionary."""
    if not note_text:
        return

    # Extract all RefSeq IDs from the note text using regex
    # Pattern looks for RefSeq IDs like NP_001234.1 or NM_001234.2
    refseq_pattern = r"(N[M|P]_\d+\.\d+)"
    refseq_ids = list(set(re.findall(refseq_pattern, note_text)))

    if not refseq_ids:
        return

    # Create IsoformNote object
    isoform_note: IsoformNote = {"note": note_text, "refseq_ids": refseq_ids}

    # Associate this note with each isoform ID found in the evidence
    for isoform_id in isoform_ids:
        if isoform_id not in result:
            result[isoform_id] = []
        # Avoid duplicate notes for the same isoform
        exists = False
        for existing in result[isoform_id]:
            if (
                existing["note"] == isoform_note["note"]
                and set(existing["refseq_ids"]) == set(isoform_note["refseq_ids"])
            ):
                exists = True
                break
        if not exists:
            result[isoform_id].append(isoform_note)
