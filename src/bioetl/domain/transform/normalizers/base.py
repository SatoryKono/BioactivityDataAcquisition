"""Base utilities and regex patterns for normalizers."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# --- Regex Patterns ---

DOI_REGEX = re.compile(r"^10\.\d{4,9}/\S+$", flags=re.IGNORECASE)
CHEMBL_ID_REGEX = re.compile(r"^CHEMBL\d+$", flags=re.IGNORECASE)
PUBMED_ID_REGEX = re.compile(r"^\d{1,10}$")
PUBCHEM_CID_REGEX = re.compile(r"^\d{1,10}$")
BAO_ID_REGEX = re.compile(r"^BAO_\d+$", flags=re.IGNORECASE)

# UniProt patterns
_UNIPROT_PATTERN_SHORT = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9]"
_UNIPROT_PATTERN_PQ = r"[OPQ][0-9][A-Z0-9]{3}[0-9]"
_UNIPROT_PATTERN_LONG = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9][A-Z0-9]{3}[0-9]"

UNIPROT_ID_REGEX = re.compile(
    f"^(?:{_UNIPROT_PATTERN_PQ}|{_UNIPROT_PATTERN_SHORT}|" f"{_UNIPROT_PATTERN_LONG})$",
    flags=re.IGNORECASE,
)


def is_missing(value: Any) -> bool:
    """Check if value is None or pandas NA."""
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (ValueError, TypeError):
        return False


__all__ = [
    "DOI_REGEX",
    "CHEMBL_ID_REGEX",
    "PUBMED_ID_REGEX",
    "PUBCHEM_CID_REGEX",
    "BAO_ID_REGEX",
    "UNIPROT_ID_REGEX",
    "is_missing",
]
