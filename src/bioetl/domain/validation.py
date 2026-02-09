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
from typing import TYPE_CHECKING, Any

from .transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.config import ValidationConfig

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
# covers historical scientific journals from XVII century
#
# These constants use DEFAULT_VALIDATION_CONFIG for the authoritative values.
# For custom ranges, use ValidationConfig directly or PublicationYear Value Object.


def _get_default_config() -> ValidationConfig:
    """Get default validation config (lazy import to avoid circular deps)."""
    from bioetl.domain.config import DEFAULT_VALIDATION_CONFIG

    return DEFAULT_VALIDATION_CONFIG


# Backward-compatible constants that reference DEFAULT_VALIDATION_CONFIG
MIN_PUBLICATION_YEAR: int = 1500
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
    min_year: int = MIN_PUBLICATION_YEAR,
    max_year: int = MAX_PUBLICATION_YEAR,
) -> bool:
    """Validate year is within a reasonable range.

    Default range [1950, CURRENT_YEAR+1] covers scientific publications.

    Args:
        year: Year to validate.
        min_year: Minimum valid year (inclusive). Default 1950.
        max_year: Maximum valid year (inclusive). Default CURRENT_YEAR + 1.

    Returns:
        True if year is within range.

    Example:
        >>> validate_year_range(2024)
        True
        >>> validate_year_range(1949)
        False
        >>> validate_year_range(None)
        False

    """
    if year is None:
        return False
    return min_year <= year <= max_year


def validate_publication_year(
    year: int | None,
    config: ValidationConfig | None = None,
) -> tuple[int | None, bool]:
    """Validate publication year and flag if out of range.

    Uses validation range from config or DEFAULT_VALIDATION_CONFIG.
    Values outside this range are preserved but flagged for DQ warnings.

    Args:
        year: Publication year to validate.
        config: Optional ValidationConfig for custom ranges.
            If None, uses DEFAULT_VALIDATION_CONFIG.

    Returns:
        Tuple of (year, is_warning) where:
        - year: Original value (preserved even if out of range)
        - is_warning: True if year is outside valid range (requires DQ warning)

    Example:
        >>> validate_publication_year(2020)
        (2020, False)
        >>> validate_publication_year(1950)
        (1950, False)
        >>> validate_publication_year(1949)
        (1949, True)
        >>> validate_publication_year(None)
        (None, False)
        >>> # With custom config
        >>> from bioetl.domain.config import ValidationConfig
        >>> ss_config = ValidationConfig(min_publication_year=1500)
        >>> validate_publication_year(1600, config=ss_config)
        (1600, False)

    """
    if year is None:
        return None, False
    resolved_config = config or _get_default_config()
    min_year = resolved_config.min_publication_year
    max_year = resolved_config.max_publication_year
    if min_year <= year <= max_year:
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
# Molecular Weight Validation
# =============================================================================

# Molecular weight valid range:
# - Min: > 10.0 Da (DEFAULT_VALIDATION_CONFIG)
# - Max: < 10000.0 Da (DEFAULT_VALIDATION_CONFIG)
# Reference: PubChem compound MW typically ranges from ~10 to ~5000 Da
#
# For backward compatibility, these constants use broader ranges than
# DEFAULT_VALIDATION_CONFIG. Use MolecularWeight Value Object for strict validation.
MIN_MOLECULAR_WEIGHT: float = 0.0  # Legacy: 0.0 (exclusive bound)
MAX_MOLECULAR_WEIGHT: float = 100000.0  # Legacy: 100000.0 (exclusive bound)


def validate_molecular_weight(
    value: Any,
    config: ValidationConfig | None = None,
) -> float | None:
    """Validate and convert molecular weight to float.

    Handles string-to-float conversion (PubChem API may return strings)
    and validates the range. Precision from config (default 10 decimals)
    per RULES.md §2.8.1.

    When config is provided, uses config.min_molecular_weight and
    config.max_molecular_weight (exclusive bounds).

    When config is None, uses legacy bounds (0, 100000) for backward
    compatibility. For stricter validation, use MolecularWeight Value Object.

    Args:
        value: Raw molecular weight value (string, int, float, or None).
        config: Optional ValidationConfig for custom ranges and precision.

    Returns:
        Valid float rounded to precision, or None if invalid/out of range.

    Example:
        >>> validate_molecular_weight(180.156)
        180.156
        >>> validate_molecular_weight("342.30")  # String from API
        342.3
        >>> validate_molecular_weight(0)  # Zero is invalid
        None
        >>> validate_molecular_weight(-1.0)  # Negative is invalid
        None
        >>> validate_molecular_weight(100001)  # Too large (legacy bounds)
        None
        >>> validate_molecular_weight(None)
        None
        >>> validate_molecular_weight("invalid")
        None

    """
    if value is None:
        return None
    try:
        mw = float(value)
        # Use config bounds if provided, otherwise legacy bounds
        if config is not None:
            min_mw = config.min_molecular_weight
            max_mw = config.max_molecular_weight
            precision = config.molecular_weight_precision
        else:
            min_mw = MIN_MOLECULAR_WEIGHT
            max_mw = MAX_MOLECULAR_WEIGHT
            precision = 10
        if min_mw < mw < max_mw:
            return round(mw, precision)
        return None
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
#   - suffix is the identifier (minimum 1 non-whitespace character)
# Aligned with DOI Value Object: \S+ forbids whitespace in DOI suffix.
DOI_REGEX_PATTERN: str = r"^10\.\d{4,}/\S+$"
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
