"""Publication validation functions (no I/O).

Implements validation rules for publication identifiers and metadata:
- DOI (Digital Object Identifier)
- Publication year
- Year range

Requirements:
- REQ-ARCH-003: No I/O in domain layer
- REFACTOR-004: Domain logic separation from use-case layer

See also:
- docs/RULES.md §1.1 (Domain — pure functions)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.config import ValidationConfig

__all__ = [
    "DOI_REGEX_PATTERN",
    "MAX_PUBLICATION_YEAR",
    "MIN_PUBLICATION_YEAR",
    "validate_doi",
    "validate_publication_year",
    "validate_year_range",
]

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
MIN_PUBLICATION_YEAR: int = 1950
MAX_PUBLICATION_YEAR: int = 2050


# =============================================================================
# Publication Year Validation
# =============================================================================


def validate_publication_year(
    year: int | None,
    config: ValidationConfig | None = None,
) -> tuple[int | None, bool]:
    """Validate publication year and return (year, is_warning).

    Preserves the original value; flags as warning when outside valid range.
    Uses ValidationConfig range (default min_publication_year=1500,
    max_publication_year=2100 from DEFAULT_VALIDATION_CONFIG).

    Args:
        year: Year to validate.
        config: Optional ValidationConfig. Uses DEFAULT_VALIDATION_CONFIG if None.

    Returns:
        Tuple of (year, is_warning). Year is preserved; is_warning is True
        when year is outside [min_publication_year, max_publication_year].

    Example:
        >>> validate_publication_year(2020)
        (2020, False)
        >>> validate_publication_year(1499)
        (1499, True)
        >>> validate_publication_year(None)
        (None, False)
    """
    if year is None:
        return (None, False)
    cfg = config if config is not None else _get_default_config()
    in_range = cfg.min_publication_year <= year <= cfg.max_publication_year
    return (year, not in_range)


def validate_year_range(
    year: int | None,
    min_year: int = MIN_PUBLICATION_YEAR,
    max_year: int = MAX_PUBLICATION_YEAR,
) -> bool:
    """Validate year is within a reasonable range.

    Default range [1950, 2050] covers scientific publications.
    Bounds come from MIN_PUBLICATION_YEAR and MAX_PUBLICATION_YEAR constants.

    Args:
        year: Year to validate.
        min_year: Minimum valid year (inclusive). Default MIN_PUBLICATION_YEAR (1950).
        max_year: Maximum valid year (inclusive). Default MAX_PUBLICATION_YEAR (2050).

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


# =============================================================================
# DOI Validation
# =============================================================================

# DOI regex pattern per DOI Handbook (https://www.doi.org/doi_handbook/2_Numbering.html)
# Format: 10.NNNN/suffix where:
#   - 10. is the fixed prefix
#   - NNNN is registrant code (minimum 4 digits)
#   - suffix is the identifier (minimum 1 non-whitespace character)
# Aligned with DOI Value Object: \S+ forbids whitespace in DOI suffix.
DOI_REGEX_PATTERN: str = r"^10\.\d{4,}/\S+$"
_DOI_PATTERN = re.compile(DOI_REGEX_PATTERN)


def validate_doi(doi: str | None) -> bool:
    """Validate DOI format.

    Checks if DOI matches the standard format: 10.NNNN/...

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
