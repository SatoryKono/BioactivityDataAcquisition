"""Pure domain validation functions (no I/O).

Implements business validation rules as pure functions.
All functions are deterministic and side-effect free.

Requirements:
- REQ-ARCH-003: No I/O in domain layer
- REFACTOR-004: Domain logic separation from use-case layer

See also:
- docs/RULES.md §1.1 (Domain — pure functions)
- docs/RULES.md §8.1 (Pandera-schemas for structural validation)
"""

from __future__ import annotations

import re
from typing import Any

from .transformations import safe_int

# =============================================================================
# SMILES Validation (Chemical Structure)
# =============================================================================

# SMILES validation regex (basic syntax check)
# Allowed: letters, digits, brackets, dots, signs, hashes, percentages, @, +, -, =, #
_SMILES_PATTERN = re.compile(r"^[A-Za-z0-9@+\-=#$()\[\]\\/%.*]+$")


def validate_smiles(smiles: str | None) -> bool:
    """Validate SMILES string format.

    Performs basic syntactic validation without full molecule parsing.
    For complete validation use RDKit or other chemical libraries.

    Args:
        smiles: SMILES string to validate.

    Returns:
        True if string matches basic SMILES syntax.

    Example:
        >>> validate_smiles("CCO")  # Ethanol
        True
        >>> validate_smiles("C1=CC=CC=C1")  # Benzene
        True
        >>> validate_smiles("")
        False
        >>> validate_smiles(None)
        False
        >>> validate_smiles("invalid smiles with spaces")
        False

    """
    if not smiles or not isinstance(smiles, str):
        return False

    stripped = smiles.strip()
    if not stripped:
        return False

    return bool(_SMILES_PATTERN.match(stripped))


# =============================================================================
# Publication Year Constants
# =============================================================================

# Standard publication year range for scientific publications.
# First scientific journals appeared in XVII century, but systematic
# publications began in XIX century.
MIN_PUBLICATION_YEAR: int = 1800
MAX_PUBLICATION_YEAR: int = 2100


# =============================================================================
# Numeric Validation
# =============================================================================


def validate_positive_int(value: Any) -> int | None:
    """Validate integer is positive (>= 1) or return None.

    Used for validating IDs, counts, and other positive integer fields.

    Args:
        value: Raw value to validate (string, int, or other convertible type).

    Returns:
        Valid int (>= 1) or None if invalid/non-positive.

    Example:
        >>> validate_positive_int(42)
        42
        >>> validate_positive_int("123")
        123
        >>> validate_positive_int(0)
        None
        >>> validate_positive_int(-1)
        None
        >>> validate_positive_int("invalid")
        None

    """
    int_value = safe_int(value)
    if int_value is not None and int_value < 1:
        return None
    return int_value


def validate_year_range(
    year: int | None,
    min_year: int = 1800,
    max_year: int = 2100,
) -> bool:
    """Validate year is within a reasonable range.

    Default range [1800, 2100] covers scientific publications.

    Args:
        year: Year to validate.
        min_year: Minimum valid year (inclusive). Default 1800.
        max_year: Maximum valid year (inclusive). Default 2100.

    Returns:
        True if year is within range.

    Example:
        >>> validate_year_range(2024)
        True
        >>> validate_year_range(1799)
        False
        >>> validate_year_range(2101)
        False
        >>> validate_year_range(None)
        False

    """
    if year is None:
        return False
    return min_year <= year <= max_year


def validate_publication_year(year: int | None) -> tuple[int | None, bool]:
    """Validate publication year and flag if out of range.

    Uses standard publication year range [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR].
    Values outside this range are preserved but flagged for DQ warnings.

    Args:
        year: Publication year to validate.

    Returns:
        Tuple of (year, is_warning) where:
        - year: Original value (preserved even if out of range)
        - is_warning: True if year is outside valid range (requires DQ warning)

    Example:
        >>> validate_publication_year(2020)
        (2020, False)
        >>> validate_publication_year(1800)
        (1800, False)
        >>> validate_publication_year(2100)
        (2100, False)
        >>> validate_publication_year(1799)
        (1799, True)
        >>> validate_publication_year(2101)
        (2101, True)
        >>> validate_publication_year(1500)
        (1500, True)
        >>> validate_publication_year(None)
        (None, False)

    """
    if year is None:
        return None, False
    if MIN_PUBLICATION_YEAR <= year <= MAX_PUBLICATION_YEAR:
        return year, False
    return year, True  # Keep value but flag as warning


def validate_non_negative(value: Any) -> float | None:
    """Validate numeric value is non-negative (>= 0) or return None.

    Used for validating concentrations, counts, and other non-negative fields.

    Args:
        value: Raw value to validate.

    Returns:
        Valid float (>= 0) or None if invalid/negative.

    Example:
        >>> validate_non_negative(0.0)
        0.0
        >>> validate_non_negative(42.5)
        42.5
        >>> validate_non_negative(-1.0)
        None
        >>> validate_non_negative("invalid")
        None

    """
    if value is None:
        return None
    try:
        float_value = float(value)
        if float_value < 0:
            return None
        return float_value
    except (ValueError, TypeError):
        return None


# =============================================================================
# String Validation
# =============================================================================


def validate_non_empty_string(value: str | None) -> str | None:
    """Validate string is non-empty after stripping whitespace.

    Args:
        value: String to validate.

    Returns:
        Stripped string if non-empty, None otherwise.

    Example:
        >>> validate_non_empty_string("  hello  ")
        'hello'
        >>> validate_non_empty_string("   ")
        None
        >>> validate_non_empty_string(None)
        None

    """
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped if stripped else None


# =============================================================================
# DOI Validation
# =============================================================================

# DOI regex pattern per DOI Handbook (https://www.doi.org/doi_handbook/2_Numbering.html)
# Format: 10.XXXX/suffix where:
#   - 10. is the fixed prefix
#   - XXXX is registrant code (minimum 4 digits)
#   - suffix is the identifier (minimum 1 character)
DOI_REGEX_PATTERN: str = r"^10\.\d{4,}/.+$"
_DOI_PATTERN = re.compile(DOI_REGEX_PATTERN)


def validate_doi(doi: str | None) -> bool:
    """Validate DOI format.

    Checks if DOI matches the standard format: 10.XXXX/...

    Args:
        doi: DOI string to validate.

    Returns:
        True if DOI format is valid.

    Example:
        >>> validate_doi("10.1038/nature12373")
        True
        >>> validate_doi("10.1000/xyz123")
        True
        >>> validate_doi("invalid")
        False
        >>> validate_doi(None)
        False

    """
    if not doi or not isinstance(doi, str):
        return False
    return bool(_DOI_PATTERN.match(doi.strip().lower()))


# =============================================================================
# InChI Key Validation
# =============================================================================

# InChI Key format: XXXXXXXXXXXXXX-YYYYYYYYYY-Z
# - First block: 14 uppercase letters (connectivity layer)
# - Second block: 10 uppercase letters (stereochemistry + isotopes)
# - Third block: 1 uppercase letter (protonation)
# Total: 27 characters (14 + 1 + 10 + 1 + 1 = 27)
# Reference: IUPAC InChI specification https://www.inchi-trust.org/
INCHI_KEY_REGEX_PATTERN: str = r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"
_INCHI_KEY_PATTERN = re.compile(INCHI_KEY_REGEX_PATTERN)


def validate_inchi_key(key: str | None) -> bool:
    """Validate InChI Key format.

    InChI Key is a 27-character string in format: XXXXXXXXXXXXXX-YYYYYYYYYY-Z
    where each block contains only uppercase letters A-Z.

    Args:
        key: InChI Key string to validate.

    Returns:
        True if InChI Key format is valid.

    Example:
        >>> validate_inchi_key("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")  # Aspirin
        True
        >>> validate_inchi_key("RYYVLZVUVIJVGH-UHFFFAOYSA-N")  # Caffeine
        True
        >>> validate_inchi_key("bsynrymutxbxsq-uhfffaoysa-n")  # Lowercase
        False
        >>> validate_inchi_key("invalid")
        False
        >>> validate_inchi_key(None)
        False

    """
    if not key or not isinstance(key, str):
        return False
    return bool(_INCHI_KEY_PATTERN.match(key.strip()))
