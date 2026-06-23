"""Shared regex patterns for domain schema validation."""

from __future__ import annotations

CHEMBL_ID_PATTERN = r"^CHEMBL\d+$"

BAO_ID_PATTERN = r"^BAO[_:]\d+$"
UO_ID_PATTERN = r"^UO[_:]\d+$"
CLO_ID_PATTERN = r"^CLO[_:]\d+$"
EFO_ID_PATTERN = r"^EFO[_:]\d+$"
BTO_ID_PATTERN = r"^BTO[_:]\d+$"
UBERON_ID_PATTERN = r"^UBERON[_:]\d+$"
CALOHA_ID_PATTERN = r"^TS-\d{4}$"

CELLOSAURUS_ID_PATTERN = r"^CVCL_[A-Z0-9]+$"

ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

ISSN_PATTERN = r"^\d{4}-\d{3}[\dX]$"
ORCID_PATTERN = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"

__all__ = [
    "BAO_ID_PATTERN",
    "BTO_ID_PATTERN",
    "CALOHA_ID_PATTERN",
    "CELLOSAURUS_ID_PATTERN",
    "CHEMBL_ID_PATTERN",
    "CLO_ID_PATTERN",
    "EFO_ID_PATTERN",
    "ISO_DATE_PATTERN",
    "ISSN_PATTERN",
    "ORCID_PATTERN",
    "UBERON_ID_PATTERN",
    "UO_ID_PATTERN",
]
