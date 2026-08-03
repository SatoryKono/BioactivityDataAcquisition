# basedpyright residual burn-down (shrink-only product surface).
"""Molecular weight Value Object.

Contains MolecularWeight — a chemical property with configurable
range validation and precision rounding per RULES.md §2.8.1.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.base import ValueObject

if TYPE_CHECKING:
    from bioetl.domain.config import ValidationConfig

__all__ = [
    "MolecularWeight",
]


class MolecularWeight(ValueObject[float]):
    """Molecular weight value object with validation.

    Validates molecular weight against configurable range and rounds
    to specified precision per RULES.md §2.8.1.

    Default validation range: (10.0, 10000.0) Da - covers small molecules
    to large peptides. Range is exclusive (open interval).

    Attributes:
        _config: ValidationConfig for range and precision.

    Invariants:
        - Must be between config.min_molecular_weight and max_molecular_weight
        - Rounded to config.molecular_weight_precision decimals
        - Cannot be NaN or Inf

    Example:
        >>> mw = MolecularWeight(180.156)
        >>> mw.value
        180.156
        >>> # Rounding to precision
        >>> mw = MolecularWeight(180.15600000001)
        >>> mw.value
        180.156

    """

    __slots__ = ("_config",)
    _value: float
    _config: ValidationConfig

    def __init__(  # pyright: ignore[reportMissingSuperCall]
        self,
        value: float | int | str,
        *,
        config: ValidationConfig | None = None,
    ) -> None:
        """Create MolecularWeight with validated value.

        Args:
            value: Raw molecular weight value.
            config: Optional ValidationConfig for custom ranges.
                If None, uses DEFAULT_VALIDATION_CONFIG.

        Raises:
            ValueError: If MW is outside valid range or invalid.

        """
        # Import here to avoid circular dependency
        from bioetl.domain.config import DEFAULT_VALIDATION_CONFIG

        resolved_config = config or DEFAULT_VALIDATION_CONFIG
        object.__setattr__(self, "_config", resolved_config)
        validated = self._validate(value)
        object.__setattr__(self, "_value", validated)

    def _validate(self, value: float | int | str) -> float:
        """Validate and normalize molecular weight.

        Args:
            value: Raw molecular weight value.

        Returns:
            Validated and rounded float.

        Raises:
            ValueError: If MW is invalid or outside range.
        """
        # Convert to float
        try:
            float_value = float(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid molecular weight: {value!r}") from e

        # Check for NaN/Inf
        if math.isnan(float_value) or math.isinf(float_value):
            raise ValueError(f"Invalid molecular weight: {value} (NaN or Inf)")

        # Validate range (exclusive bounds)
        min_mw = self._config.min_molecular_weight
        max_mw = self._config.max_molecular_weight
        if not min_mw < float_value < max_mw:
            raise ValueError(
                f"Molecular weight {float_value} outside range ({min_mw}, {max_mw})"
            )

        # Round to precision
        precision = self._config.molecular_weight_precision
        return round(float_value, precision)

    @property
    def min_weight(self) -> float:
        """Get the minimum valid molecular weight from config."""
        return self._config.min_molecular_weight

    @property
    def max_weight(self) -> float:
        """Get the maximum valid molecular weight from config."""
        return self._config.max_molecular_weight

    @classmethod
    def from_raw(
        cls,
        raw: float | int | str | None,
        *,
        config: ValidationConfig | None = None,
    ) -> MolecularWeight | None:
        """Create MolecularWeight from raw value with normalization.

        Args:
            raw: Raw molecular weight value or None.
            config: Optional ValidationConfig for custom ranges.

        Returns:
            MolecularWeight if valid, None if input is None or invalid.

        Example:
            >>> MolecularWeight.from_raw(180.156)
            MolecularWeight(180.156)
            >>> MolecularWeight.from_raw("342.30")  # String from API
            MolecularWeight(342.3)
            >>> MolecularWeight.from_raw(None)
            None

        """
        if raw is None:
            return None
        if isinstance(raw, str) and not raw.strip():
            return None
        try:
            return cls(raw, config=config)
        except ValueError:
            return None

    def __eq__(self, other: object) -> bool:
        """Compare by value only (ignoring config)."""
        if not isinstance(other, MolecularWeight):
            return NotImplemented
        return bool(self._value == other._value)

    def __hash__(self) -> int:
        """Hash based on class and value only (ignoring config)."""
        return hash((self.__class__.__name__, self._value))
