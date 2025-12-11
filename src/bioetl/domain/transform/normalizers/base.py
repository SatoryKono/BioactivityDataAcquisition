"""Base utilities and regex patterns for normalizers."""

from __future__ import annotations

import re
from typing import Any

from bioetl.domain.schemas.field_specs import UNIPROT_ID_PATTERN

# --- Regex Patterns ---

DOI_REGEX = re.compile(r"^10\.\d{4,9}/\S+$", flags=re.IGNORECASE)
CHEMBL_ID_REGEX = re.compile(r"^CHEMBL\d+$", flags=re.IGNORECASE)
PUBMED_ID_REGEX = re.compile(r"^\d{1,10}$")
PUBCHEM_CID_REGEX = re.compile(r"^\d{1,10}$")
BAO_ID_REGEX = re.compile(r"^BAO_\d+$", flags=re.IGNORECASE)

UNIPROT_ID_REGEX = re.compile(
    UNIPROT_ID_PATTERN,
    flags=re.IGNORECASE,
)


def is_missing(value: Any) -> bool:
    """Check if value is None or pandas NA."""
    if value is None:
        return True
    try:
        return bool(value != value)
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
