"""Chemical structure validation functions (no I/O).

Implements validation rules for chemical identifiers:
- SMILES strings
- InChI Keys
- Molecular weights

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
    "INCHI_KEY_REGEX_PATTERN",
    "MAX_MOLECULAR_WEIGHT",
    "MIN_MOLECULAR_WEIGHT",
    "validate_inchi_key",
    "validate_molecular_weight",
    "validate_smiles",
]

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
    value: object,
    config: ValidationConfig | None = None,
) -> float | None:
    """Convert molecular weight to float and enforce configured bounds.

    Args:
        value: Raw molecular weight value to validate; may be any type
            convertible to float via str().
        config: Optional ValidationConfig providing custom min/max bounds and
            precision; defaults to None, which applies legacy broad bounds.

    Returns:
        Validated molecular weight as float, or None if value is invalid or
        outside configured bounds.
    """
    if value is None or isinstance(value, bool):
        return None

    try:
        mw = float(str(value).strip())
    except (ValueError, TypeError):
        return None

    min_mw, max_mw, precision = _molecular_weight_bounds(config)
    rounded = round(mw, precision)
    if not (min_mw < rounded < max_mw):
        return None
    return rounded


def _molecular_weight_bounds(
    config: ValidationConfig | None,
) -> tuple[float, float, int]:
    """Resolve molecular-weight validation bounds and precision."""
    if config is None:
        return MIN_MOLECULAR_WEIGHT, MAX_MOLECULAR_WEIGHT, 10
    return (
        config.min_molecular_weight,
        config.max_molecular_weight,
        config.molecular_weight_precision,
    )


# =============================================================================
# InChI Key Validation
# =============================================================================

# InChI Key format: AAAAAAAAAAAAAA-BBBBBBBBBB-Z
# - First block: 14 uppercase letters (connectivity layer)
# - Second block: 10 uppercase letters (stereochemistry + isotopes)
# - Third block: 1 uppercase letter (protonation)
# Total: 27 characters (14 + 1 + 10 + 1 + 1 = 27)
# Reference: IUPAC InChI specification https://www.inchi-trust.org/
INCHI_KEY_REGEX_PATTERN: str = r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"
_INCHI_KEY_PATTERN = re.compile(INCHI_KEY_REGEX_PATTERN)


def validate_inchi_key(key: str | None) -> bool:
    """Validate InChI Key format.

    InChI Key is a 27-character string in format: AAAAAAAAAAAAAA-BBBBBBBBBB-Z
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
