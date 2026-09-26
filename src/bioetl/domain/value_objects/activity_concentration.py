"""Concentration value objects used in bioactivity domain logic."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ConcentrationUnit(StrEnum):
    """Concentration units commonly used in bioactivity data."""

    MOLAR = "M"
    MILLIMOLAR = "mM"
    MICROMOLAR = "μM"
    NANOMOLAR = "nM"
    PICOMOLAR = "pM"
    FEMTOMOLAR = "fM"

    @property
    def molar_exponent(self) -> int:
        """Base-10 exponent of this unit relative to molar (M = 10^0)."""
        exponents = {
            ConcentrationUnit.MOLAR: 0,
            ConcentrationUnit.MILLIMOLAR: -3,
            ConcentrationUnit.MICROMOLAR: -6,
            ConcentrationUnit.NANOMOLAR: -9,
            ConcentrationUnit.PICOMOLAR: -12,
            ConcentrationUnit.FEMTOMOLAR: -15,
        }
        return exponents[self]

    @property
    def to_molar_factor(self) -> float:
        """Conversion factor to molar (M)."""
        return 10.0**self.molar_exponent

    @classmethod
    def from_string(cls, unit_str: str) -> ConcentrationUnit:
        """Parse concentration unit from string.

        Args:
            unit_str: Unit abbreviation such as 'nM', 'uM', 'μM', 'mM', 'M'.

        Returns:
            Corresponding ConcentrationUnit enum member.
        """
        normalized = unit_str.strip().lower()

        unit_map = {
            "m": cls.MOLAR,
            "mm": cls.MILLIMOLAR,
            "μm": cls.MICROMOLAR,
            "um": cls.MICROMOLAR,
            "microm": cls.MICROMOLAR,
            "nm": cls.NANOMOLAR,
            "pm": cls.PICOMOLAR,
            "fm": cls.FEMTOMOLAR,
        }

        unit = unit_map.get(normalized)
        if unit is None:
            raise ValueError(f"Unknown concentration unit: {unit_str!r}")
        return unit


@dataclass(frozen=True, slots=True)
class Concentration:
    """Concentration value with unit."""

    value: float
    unit: ConcentrationUnit

    def _require_numeric_value(self) -> None:
        if isinstance(self.value, bool):
            raise TypeError(
                f"Concentration value must be numeric, got {type(self.value).__name__}"
            )
        if isinstance(self.value, (int, float)):
            return
        raise TypeError(
            f"Concentration value must be numeric, got {type(self.value).__name__}"
        )

    def _require_finite_non_negative(self) -> None:
        import math

        if math.isnan(self.value):
            raise ValueError(f"Concentration must be finite: {self.value}")
        if math.isinf(self.value):
            raise ValueError(f"Concentration must be finite: {self.value}")
        if self.value < 0:
            raise ValueError(f"Concentration cannot be negative: {self.value}")

    def __post_init__(self) -> None:
        """Validate concentration invariants."""
        self._require_numeric_value()
        self._require_concentration_unit()
        self._require_finite_non_negative()

    def _require_concentration_unit(self) -> None:
        if isinstance(self.unit, ConcentrationUnit):
            return
        raise TypeError(
            f"Concentration unit must be ConcentrationUnit, got {type(self.unit).__name__}"
        )

    def to_unit(self, target_unit: ConcentrationUnit) -> Concentration:
        """Convert to a different unit.

        Args:
            target_unit: The desired concentration unit to convert to.

        Returns:
            New Concentration instance with value expressed in target_unit.
        """
        # Single exponent delta avoids chained mul/div floating noise.
        delta = self.unit.molar_exponent - target_unit.molar_exponent
        target_value = self.value * (10.0**delta)
        return Concentration(value=target_value, unit=target_unit)

    def to_molar(self) -> Concentration:
        """Convert to molar (M)."""
        return self.to_unit(ConcentrationUnit.MOLAR)

    def to_nanomolar(self) -> Concentration:
        """Convert to nanomolar (nM)."""
        return self.to_unit(ConcentrationUnit.NANOMOLAR)

    @property
    def molar_value(self) -> float:
        """Get concentration value in molar (M) units."""
        return self.value * self.unit.to_molar_factor

    @classmethod
    def from_string(cls, s: str) -> Concentration:
        """Parse concentration from string.

        Args:
            s: Concentration string such as '100 nM', '1.5 uM', '50 mM'.

        Returns:
            Concentration instance with parsed numeric value and unit.
        """
        match = re.fullmatch(
            r"([+-]?[\d.]+(?:e[+-]?\d+)?)\s*([a-zμ]+)", s.strip(), re.IGNORECASE
        )
        if not match:
            raise ValueError(f"Cannot parse concentration: {s!r}")

        value = float(match.group(1))
        unit = ConcentrationUnit.from_string(match.group(2))
        return cls(value=value, unit=unit)

    def __str__(self) -> str:
        """String representation with unit."""
        if self.value == int(self.value):
            return f"{int(self.value)} {self.unit.value}"
        return f"{self.value} {self.unit.value}"


__all__ = ["Concentration", "ConcentrationUnit"]
