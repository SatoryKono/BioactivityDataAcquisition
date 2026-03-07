"""Validation constants and helper rules for activity values."""

from __future__ import annotations

from bioetl.domain.value_objects.activity_values import ActivityType

__all__ = [
    "DEFAULT_CONCENTRATION_RANGES",
    "PCHEMBL_MAX",
    "PCHEMBL_MIN",
    "PCHEMBL_TYPICAL_MAX",
    "PCHEMBL_TYPICAL_MIN",
    "is_percent_inhibition_type",
    "normalize_unit_name",
    "validate_percent_value",
]

DEFAULT_CONCENTRATION_RANGES: dict[str, tuple[float, float]] = {
    "M": (1e-15, 1e-1),
    "mM": (1e-12, 1e2),
    "µM": (1e-9, 1e5),
    "uM": (1e-9, 1e5),
    "nM": (1e-6, 1e8),
    "pM": (1e-3, 1e11),
    "fM": (1e0, 1e14),
}

PCHEMBL_MIN = 0.0
PCHEMBL_MAX = 14.0
PCHEMBL_TYPICAL_MIN = 2.0
PCHEMBL_TYPICAL_MAX = 12.0


def normalize_unit_name(unit: str) -> str:
    """Normalize unit string for lookup in concentration ranges.

    Resolves common aliases (e.g., 'uM' -> 'µM', 'nanomolar' -> 'nM').

    Args:
        unit: Raw unit string from API or user input.

    Returns:
        Canonical unit string ready for lookup in DEFAULT_CONCENTRATION_RANGES.
    """
    normalized = unit.strip()
    unit_aliases = {
        "um": "µM",
        "uM": "µM",
        "micromolar": "µM",
        "nm": "nM",
        "nanomolar": "nM",
        "pm": "pM",
        "picomolar": "pM",
        "fm": "fM",
        "femtomolar": "fM",
        "mm": "mM",
        "millimolar": "mM",
        "m": "M",
        "molar": "M",
    }
    return unit_aliases.get(normalized.lower(), normalized)


def is_percent_inhibition_type(parsed_type: ActivityType | str) -> bool:
    """Check if activity type is percent inhibition.

    Args:
        parsed_type: ActivityType enum value or raw string from API.

    Returns:
        True if the activity type is PERCENT_INHIBITION, False otherwise.
    """
    return (
        isinstance(parsed_type, ActivityType)
        and parsed_type == ActivityType.PERCENT_INHIBITION
    )


def validate_percent_value(value: float) -> tuple[bool, str | None]:
    """Validate percentage value is within 0-100 range.

    Args:
        value: Percentage value to validate (e.g., percent inhibition).

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if value < 0 or value > 100:
        return False, f"Percent inhibition must be 0-100, got {value}"
    return True, None
