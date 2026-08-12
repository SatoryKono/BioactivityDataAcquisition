"""Value validator service for bioactivity measurements (pure domain logic)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.behavior.value_validator_rules import (
    DEFAULT_CONCENTRATION_RANGES,
    PCHEMBL_MAX,
    PCHEMBL_MIN,
    PCHEMBL_TYPICAL_MAX,
    PCHEMBL_TYPICAL_MIN,
    is_percent_inhibition_type,
    normalize_unit_name,
    validate_percent_value,
)
from bioetl.domain.value_objects import ActivityType

if TYPE_CHECKING:
    from bioetl.domain.behavior.normalization_config import NormalizationConfig

__all__ = [
    "PCHEMBL_MAX",
    "PCHEMBL_MIN",
    "PCHEMBL_TYPICAL_MAX",
    "PCHEMBL_TYPICAL_MIN",
    "ValueValidator",
]


@dataclass(slots=True)
class ValueValidator:
    """Validate bioactivity measurements against configured domain ranges."""

    config: NormalizationConfig | None = None
    strict: bool = False
    _concentration_ranges: dict[str, tuple[float, float]] = field(
        default_factory=lambda: DEFAULT_CONCENTRATION_RANGES.copy()
    )

    def _apply_molar_window(
        self, unit: str, min_m: float, max_m: float, scale: float
    ) -> None:
        if unit not in self._concentration_ranges:
            return
        self._concentration_ranges[unit] = (min_m * scale, max_m * scale)

    def _micromolar_key(self) -> str | None:
        if "µM" in self._concentration_ranges:
            return "µM"
        if "uM" in self._concentration_ranges:
            return "uM"
        return None

    def __post_init__(self) -> None:
        """Apply configured absolute molar bounds when config is provided."""
        if self.config is None:
            return
        # Keep unit keys from defaults; scale absolute molar window via nM bounds
        # when only a single molar range is configured.
        min_m = self.config.concentration_range.min_molar
        max_m = self.config.concentration_range.max_molar
        self._apply_molar_window("nM", min_m, max_m, 1e9)
        um_key = self._micromolar_key()
        if um_key is not None:
            self._apply_molar_window(um_key, min_m, max_m, 1e6)
        self._apply_molar_window("mM", min_m, max_m, 1e3)
        self._apply_molar_window("M", min_m, max_m, 1.0)

    def validate_concentration(
        self,
        value: float,
        unit: str,
    ) -> tuple[bool, str | None]:
        """Validate a concentration value and unit."""
        # Check basic value constraints
        basic_error = self._check_basic_concentration(value)
        if basic_error:
            return False, basic_error

        # Check unit and range
        return self._check_concentration_range(value, unit)

    def _check_basic_concentration(self, value: float) -> str | None:
        """Check basic concentration constraints (non-negative, non-zero)."""
        if not math.isfinite(value):
            return f"Concentration must be finite: {value}"
        if value < 0:
            return f"Concentration cannot be negative: {value}"
        if value == 0:
            return "Concentration cannot be zero"
        return None

    def _check_concentration_range(
        self,
        value: float,
        unit: str,
    ) -> tuple[bool, str | None]:
        """Check if concentration is within valid range for unit."""
        normalized_unit = normalize_unit_name(unit)
        if normalized_unit not in self._concentration_ranges:
            return False, f"Unknown concentration unit: {unit}"

        min_val, max_val = self._concentration_ranges[normalized_unit]
        return self._check_value_in_range(value, min_val, max_val, unit)

    def _check_value_in_range(
        self,
        value: float,
        min_val: float,
        max_val: float,
        unit: str,
    ) -> tuple[bool, str | None]:
        """Check if value is within min/max range."""
        if value < min_val:
            return False, (
                f"Concentration {value} {unit} below minimum ({min_val} {unit})"
            )
        if value > max_val:
            return False, (
                f"Concentration {value} {unit} exceeds maximum ({max_val} {unit})"
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
        # Check absolute range
        if not math.isfinite(value):
            return False, f"pChEMBL value must be finite: {value}"
        range_error = self._check_pchembl_absolute_range(value)
        if range_error:
            return False, range_error

        # Check strict mode typical range
        if self.strict:
            return self._check_pchembl_typical_range(value)

        return True, None

    def _check_pchembl_absolute_range(self, value: float) -> str | None:
        """Check pChEMBL value against absolute physical limits."""
        if value < PCHEMBL_MIN:
            return f"pChEMBL value cannot be negative: {value:.2f}"
        if value > PCHEMBL_MAX:
            return f"pChEMBL value {value:.2f} exceeds maximum {PCHEMBL_MAX:.2f}"
        return None

    def _check_pchembl_typical_range(
        self,
        value: float,
    ) -> tuple[bool, str | None]:
        """Check pChEMBL value against typical drug-like range."""
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
        parsed_type = self._parse_activity_type(activity_type)

        # Basic numeric validation
        if not math.isfinite(value):
            return False, f"Activity value must be finite: {value}"
        if value < 0:
            return False, f"Activity value cannot be negative: {value}"

        if is_percent_inhibition_type(parsed_type):
            return self._validate_by_activity_type(value, parsed_type)
        if unit:
            return self.validate_concentration(value, unit)

        # Type-specific validation
        return self._validate_by_activity_type(value, parsed_type)

    def _parse_activity_type(
        self,
        activity_type: ActivityType | str,
    ) -> ActivityType | str:
        """Parse activity type string to enum if possible."""
        if isinstance(activity_type, ActivityType):
            return activity_type
        try:
            return ActivityType.from_string(activity_type)
        except ValueError:
            return activity_type

    def _validate_by_activity_type(
        self,
        value: float,
        parsed_type: ActivityType | str,
    ) -> tuple[bool, str | None]:
        """Validate value based on specific activity type."""
        # For percentage values (e.g., % Inhibition)
        if is_percent_inhibition_type(parsed_type):
            return validate_percent_value(value)
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

    def set_concentration_range(
        self,
        unit: str,
        min_value: float,
        max_value: float,
    ) -> None:
        """Set finite, increasing validation bounds for a concentration unit."""
        if not math.isfinite(min_value) or not math.isfinite(max_value):
            raise ValueError(
                f"concentration bounds must be finite, got min={min_value}, max={max_value}"
            )
        if min_value >= max_value:
            raise ValueError("min_value must be less than max_value")

        normalized_unit = normalize_unit_name(unit)
        self._concentration_ranges[normalized_unit] = (min_value, max_value)
