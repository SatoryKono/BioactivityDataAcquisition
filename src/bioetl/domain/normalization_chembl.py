"""Legacy wrapper for ChEMBL normalization helpers.

Deprecated: import from ``bioetl.domain.normalization.chembl`` instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from bioetl.domain.normalization.chembl import (
    normalize_bao_identifier,
    normalize_bao_label,
    normalize_chembl_organism_name,
    normalize_qudt_unit,
    normalize_standard_unit,
    normalize_uo_identifier,
)

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.chembl"
SUNSET_DATE = "2026-06-30"

__all__ = [
    "normalize_bao_identifier",
    "normalize_bao_label",
    "normalize_chembl_organism_name",
    "normalize_qudt_unit",
    "normalize_standard_unit",
    "normalize_uo_identifier",
]
