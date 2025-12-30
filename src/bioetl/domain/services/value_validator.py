"""Value validator service for bioactivity measurements.

Validates that bioactivity values fall within acceptable ranges
based on measurement type and physical constraints.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.activity_values import ActivityType

if TYPE_CHECKING:
    from bioetl.domain.services.normalization_config import NormalizationConfig


# Default validation ranges for bioactivity values
# Values outside these ranges are considered invalid/suspicious
DEFAULT_CONCENTRATION_RANGES: dict[str, tuple[float, float]] = {
    # Unit: (min_value, max_value)
    "M": (1e-15, 1e-1),  # femtomolar to 100 mM
    "mM": (1e-12, 1e2),  # picomolar equivalent to 100 mM
    "µM": (1e-9, 1e5),  # sub-picomolar to 100 mM
    "uM": (1e-9, 1e5),  # alias
    "nM": (1e-6, 1e8),  # sub-femtomolar to 100 mM
    "pM": (1e-3, 1e11),  # range in picomolar
    "fM": (1e0, 1e14),  # range in femtomolar
}

# pChEMBL value range (physical limits)
PCHEMBL_MIN = 0.0  # 1 M concentration
PCHEMBL_MAX = 14.0  # 0.1 fM concentration (theoretical limit)
PCHEMBL_TYPICAL_MIN = 2.0  # 10 mM - weak binding
PCHEMBL_TYPICAL_MAX = 12.0  # 1 pM - very strong binding


@dataclass(slots=True)
class ValueValidator:
    """Service for validating bioactivity measurement values.

    Validates concentrations and pChEMBL values against configurable
    ranges based on measurement type.

    Attributes:
        config: Optional configuration for custom validation ranges.
        strict: If True, use stricter validation (typical ranges).

    Example:
        >>> validator = ValueValidator()
        >>> valid, error = validator.validate_concentration(100.0, "nM")
        >>> print(valid)
        True

        >>> valid, error = validator.validate_pchembl(20.0)
        >>> print(valid, error)
        False pChEMBL value 20.00 exceeds maximum 14.00
    """

    config: NormalizationConfig | None = None
    strict: bool = False
    _concentration_ranges: dict[str, tuple[float, float]] = field(
        default_factory=lambda: DEFAULT_CONCENTRATION_RANGES.copy()
    )

    def validate_concentration(
        self,
        value: float,
        unit: str,
    ) -> tuple[bool, str | None]:
        """Validate concentration value is within acceptable range.

        Args:
            value: Concentration value.
            unit: Unit string (e.g., "nM", "µM").

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.

        Example:
            >>> validator = ValueValidator()
            >>> validator.validate_concentration(100.0, "nM")
            (True, None)
            >>> validator.validate_concentration(-1.0, "nM")
            (False, 'Concentration cannot be negative: -1.0')
        """
        # Negative values are always invalid
        if value < 0:
            return False, f"Concentration cannot be negative: {value}"

        # Zero is technically valid but suspicious
        if value == 0:
            return False, "Concentration cannot be zero"

        # Normalize unit for lookup
        normalized_unit = self._normalize_unit(unit)
        if normalized_unit not in self._concentration_ranges:
            return False, f"Unknown concentration unit: {unit}"

        min_val, max_val = self._concentration_ranges[normalized_unit]

        if value < min_val:
            return False, (
                f"Concentration {value} {unit} below minimum "
                f"({min_val} {unit})"
            )

        if value > max_val:
            return False, (
                f"Concentration {value} {unit} exceeds maximum "
                f"({max_val} {unit})"
            )

        return True, None

    def validate_pchembl(
        self,
        value: float,
    ) -> tuple[bool, str | None]:
        """Validate pChEMBL value is within acceptable range.

        pChEMBL values typically range from 2 to 14, with most
        drug-like compounds in the 5-9 range.

        Args:
            value: pChEMBL value.

        Returns:
            Tuple of (is_valid, error_message).

        Example:
            >>> validator = ValueValidator()
            >>> validator.validate_pchembl(7.5)
            (True, None)
            >>> validator.validate_pchembl(-1.0)
            (False, 'pChEMBL value cannot be negative: -1.00')
        """
        if value < PCHEMBL_MIN:
            return False, f"pChEMBL value cannot be negative: {value:.2f}"

        if value > PCHEMBL_MAX:
            return False, (
                f"pChEMBL value {value:.2f} exceeds maximum {PCHEMBL_MAX:.2f}"
            )

        # In strict mode, check typical range
        if self.strict:
            if value < PCHEMBL_TYPICAL_MIN:
                return False, (
                    f"pChEMBL value {value:.2f} below typical minimum "
                    f"{PCHEMBL_TYPICAL_MIN:.2f} (very weak activity)"
                )
            if value > PCHEMBL_TYPICAL_MAX:
                return False, (
                    f"pChEMBL value {value:.2f} exceeds typical maximum "
                    f"{PCHEMBL_TYPICAL_MAX:.2f} (unusually potent)"
                )

        return True, None

    def validate_activity_value(
        self,
        value: float,
        activity_type: ActivityType | str,
        unit: str | None = None,
    ) -> tuple[bool, str | None]:
        """Validate activity value based on measurement type.

        Different activity types may have different valid ranges.

        Args:
            value: Activity measurement value.
            activity_type: Type of measurement (IC50, EC50, Ki, etc.).
            unit: Optional unit for context-aware validation.

        Returns:
            Tuple of (is_valid, error_message).

        Example:
            >>> validator = ValueValidator()
            >>> validator.validate_activity_value(100.0, "IC50", "nM")
            (True, None)
        """
        # Parse activity type if string
        parsed_type: ActivityType | str = activity_type
        if isinstance(activity_type, str):
            try:
                parsed_type = ActivityType.from_string(activity_type)
            except ValueError:
                # Unknown activity type - allow with basic validation
                parsed_type = activity_type

        # Basic numeric validation
        if value < 0:
            return False, f"Activity value cannot be negative: {value}"

        # If unit provided, validate as concentration
        if unit:
            return self.validate_concentration(value, unit)

        # For percentage values (e.g., % Inhibition)
        if (
            isinstance(parsed_type, ActivityType)
            and parsed_type == ActivityType.PERCENT_INHIBITION
            and (value < 0 or value > 100)
        ):
            return False, f"Percent inhibition must be 0-100, got {value}"

        return True, None

    def is_potent(
        self,
        pchembl_value: float,
        threshold: float = 5.0,
    ) -> bool:
        """Check if pChEMBL value indicates potent activity.

        Args:
            pchembl_value: pChEMBL value to check.
            threshold: Potency threshold (default 5.0 = 10 µM).

        Returns:
            True if pChEMBL >= threshold.
        """
        return pchembl_value >= threshold

    def is_highly_potent(
        self,
        pchembl_value: float,
        threshold: float = 7.0,
    ) -> bool:
        """Check if pChEMBL value indicates highly potent activity.

        Args:
            pchembl_value: pChEMBL value to check.
            threshold: High potency threshold (default 7.0 = 100 nM).

        Returns:
            True if pChEMBL >= threshold.
        """
        return pchembl_value >= threshold

    def _normalize_unit(self, unit: str) -> str:
        """Normalize unit string for lookup.

        Args:
            unit: Raw unit string.

        Returns:
            Normalized unit string.
        """
        normalized = unit.strip()

        # Handle common aliases
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

    def set_concentration_range(
        self,
        unit: str,
        min_value: float,
        max_value: float,
    ) -> None:
        """Set custom validation range for a concentration unit.

        Args:
            unit: Unit string.
            min_value: Minimum valid value.
            max_value: Maximum valid value.

        Raises:
            ValueError: If min_value >= max_value.
        """
        if min_value >= max_value:
            raise ValueError("min_value must be less than max_value")

        normalized_unit = self._normalize_unit(unit)
        self._concentration_ranges[normalized_unit] = (min_value, max_value)
