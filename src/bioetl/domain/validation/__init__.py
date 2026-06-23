"""Pure domain validation functions (no I/O).

Implements business validation rules as pure functions.
All functions are deterministic and side-effect free.

This package is split into sub-modules by responsibility:
- ``chemical``: SMILES, InChI Key, molecular weight
- ``publication``: DOI, publication year, year range
- ``primitives``: non-empty strings, non-negative values, positive integers

Requirements:
- REQ-ARCH-003: No I/O in domain layer
- REFACTOR-004: Domain logic separation from use-case layer

See also:
- docs/RULES.md §1.1 (Domain — pure functions)
- docs/RULES.md §8.1 (Pandera-schemas for structural validation)
"""

from __future__ import annotations

from bioetl.domain.validation.chemical import (
    INCHI_KEY_REGEX_PATTERN,
    MAX_MOLECULAR_WEIGHT,
    MIN_MOLECULAR_WEIGHT,
    validate_inchi_key,
    validate_molecular_weight,
    validate_smiles,
)
from bioetl.domain.validation.primitives import (
    validate_non_empty_string,
    validate_non_negative,
    validate_positive_int,
)
from bioetl.domain.validation.publication import (
    DOI_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
    validate_doi,
    validate_publication_year,
    validate_year_range,
)

__all__ = [
    "DOI_REGEX_PATTERN",
    "INCHI_KEY_REGEX_PATTERN",
    "MAX_MOLECULAR_WEIGHT",
    "MAX_PUBLICATION_YEAR",
    "MIN_MOLECULAR_WEIGHT",
    "MIN_PUBLICATION_YEAR",
    "validate_doi",
    "validate_inchi_key",
    "validate_molecular_weight",
    "validate_non_empty_string",
    "validate_non_negative",
    "validate_positive_int",
    "validate_publication_year",
    "validate_smiles",
    "validate_year_range",
]
