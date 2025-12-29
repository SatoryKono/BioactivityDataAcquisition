"""Measurement Value Objects for BioETL domain.

Contains Value Objects for scientific measurements:
- Concentration: Value with concentration units (nM, μM, mM, etc.)
- ActivityType: Type of bioactivity measurement (IC50, EC50, Ki, etc.)
- PChemblValue: pChEMBL value (-log10 of molar activity)

These Value Objects encapsulate validation and unit conversion logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ConcentrationUnit(str, Enum):
    """Concentration units commonly used in bioactivity data.

    Ordered from largest to smallest for easy comparison.
    """

    MOLAR = "M"
    MILLIMOLAR = "mM"
    MICROMOLAR = "μM"
    NANOMOLAR = "nM"
    PICOMOLAR = "pM"
    FEMTOMOLAR = "fM"

    @property
    def to_molar_factor(self) -> float:
        """Conversion factor to molar (M)."""
        factors = {
            ConcentrationUnit.MOLAR: 1.0,
            ConcentrationUnit.MILLIMOLAR: 1e-3,
            ConcentrationUnit.MICROMOLAR: 1e-6,
            ConcentrationUnit.NANOMOLAR: 1e-9,
            ConcentrationUnit.PICOMOLAR: 1e-12,
            ConcentrationUnit.FEMTOMOLAR: 1e-15,
        }
        return factors[self]

    @classmethod
    def from_string(cls, unit_str: str) -> ConcentrationUnit:
        """Parse concentration unit from string.

        Args:
            unit_str: Unit string (e.g., "nM", "uM", "μM").

        Returns:
            Corresponding ConcentrationUnit.

        Raises:
            ValueError: If unit string is not recognized.
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
    """Concentration value with unit.

    Value Object representing a concentration measurement.
    Supports unit conversion between different scales.

    Invariants:
        - value >= 0 (concentrations cannot be negative)
        - unit is a valid ConcentrationUnit

    Examples:
        >>> c = Concentration(100.0, ConcentrationUnit.NANOMOLAR)
        >>> c.to_unit(ConcentrationUnit.MICROMOLAR)
        Concentration(value=0.1, unit=<ConcentrationUnit.MICROMOLAR: 'μM'>)
    """

    value: float
    unit: ConcentrationUnit

    def __post_init__(self) -> None:
        """Validate concentration invariants."""
        if self.value < 0:
            raise ValueError(f"Concentration cannot be negative: {self.value}")

    def to_unit(self, target_unit: ConcentrationUnit) -> Concentration:
        """Convert to a different unit.

        Args:
            target_unit: Target concentration unit.

        Returns:
            New Concentration with converted value.
        """
        # Convert to molar first, then to target unit
        molar_value = self.value * self.unit.to_molar_factor
        target_value = molar_value / target_unit.to_molar_factor
        return Concentration(value=target_value, unit=target_unit)

    def to_molar(self) -> Concentration:
        """Convert to molar (M)."""
        return self.to_unit(ConcentrationUnit.MOLAR)

    def to_nanomolar(self) -> Concentration:
        """Convert to nanomolar (nM) - common standard unit."""
        return self.to_unit(ConcentrationUnit.NANOMOLAR)

    @property
    def molar_value(self) -> float:
        """Get value in molar (M)."""
        return self.value * self.unit.to_molar_factor

    @classmethod
    def from_string(cls, s: str) -> Concentration:
        """Parse concentration from string.

        Args:
            s: String like "100 nM" or "0.1 μM".

        Returns:
            Parsed Concentration.

        Raises:
            ValueError: If string cannot be parsed.
        """
        # Pattern: number (optional whitespace) unit
        match = re.match(r"([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*([a-zμ]+)", s.strip(), re.IGNORECASE)
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


class ActivityType(str, Enum):
    """Types of bioactivity measurements.

    Common activity types in drug discovery assays.
    """

    # Inhibition constants
    IC50 = "IC50"  # Half-maximal inhibitory concentration
    IC90 = "IC90"  # 90% inhibitory concentration
    KI = "Ki"      # Inhibition constant
    KD = "Kd"      # Dissociation constant

    # Activation constants
    EC50 = "EC50"  # Half-maximal effective concentration
    AC50 = "AC50"  # Half-maximal activating concentration
    ED50 = "ED50"  # Half-maximal effective dose

    # Growth/toxicity
    GI50 = "GI50"  # Half-maximal growth inhibition
    LC50 = "LC50"  # Lethal concentration 50%
    LD50 = "LD50"  # Lethal dose 50%
    ID50 = "ID50"  # Infective dose 50%

    # Other measurements
    POTENCY = "Potency"
    INHIBITION = "Inhibition"
    PERCENT_INHIBITION = "% Inhibition"
    ACTIVITY = "Activity"
    RATIO = "Ratio"

    @classmethod
    def from_string(cls, s: str) -> ActivityType:
        """Parse activity type from string.

        Args:
            s: Activity type string.

        Returns:
            Corresponding ActivityType.

        Raises:
            ValueError: If type string is not recognized.
        """
        normalized = s.strip().upper()

        # Handle common variations
        type_map = {
            "IC50": cls.IC50,
            "IC90": cls.IC90,
            "KI": cls.KI,
            "KD": cls.KD,
            "EC50": cls.EC50,
            "AC50": cls.AC50,
            "ED50": cls.ED50,
            "GI50": cls.GI50,
            "LC50": cls.LC50,
            "LD50": cls.LD50,
            "ID50": cls.ID50,
            "POTENCY": cls.POTENCY,
            "INHIBITION": cls.INHIBITION,
            "% INHIBITION": cls.PERCENT_INHIBITION,
            "ACTIVITY": cls.ACTIVITY,
            "RATIO": cls.RATIO,
        }

        activity_type = type_map.get(normalized)
        if activity_type is None:
            raise ValueError(f"Unknown activity type: {s!r}")

        return activity_type

    def is_inhibition_type(self) -> bool:
        """Check if this is an inhibition-type measurement."""
        return self in {
            ActivityType.IC50,
            ActivityType.IC90,
            ActivityType.KI,
            ActivityType.INHIBITION,
            ActivityType.PERCENT_INHIBITION,
        }

    def is_binding_type(self) -> bool:
        """Check if this is a binding affinity measurement."""
        return self in {
            ActivityType.KI,
            ActivityType.KD,
        }


@dataclass(frozen=True, slots=True)
class PChemblValue:
    """pChEMBL value: -log10 of molar activity.

    The pChEMBL value is a standardized measure of potency.
    Higher values indicate higher potency.

    Range: Typically 2-14, with most drug-like compounds in 5-9 range.

    Invariants:
        - value >= 0 (cannot be negative)
        - value <= 14 (physical limit)
    """

    value: float

    def __post_init__(self) -> None:
        """Validate pChEMBL value invariants."""
        if self.value < 0:
            raise ValueError(f"pChEMBL value cannot be negative: {self.value}")
        if self.value > 14:
            raise ValueError(
                f"pChEMBL value exceeds physical limit (14): {self.value}"
            )

    def to_molar(self) -> float:
        """Convert to molar concentration.

        Returns:
            Concentration in molar (M).
        """
        return 10 ** (-self.value)

    def to_concentration(self, unit: ConcentrationUnit = ConcentrationUnit.NANOMOLAR) -> Concentration:
        """Convert to Concentration value object.

        Args:
            unit: Target concentration unit (default: nM).

        Returns:
            Concentration object.
        """
        molar = self.to_molar()
        value_in_unit = molar / unit.to_molar_factor
        return Concentration(value=value_in_unit, unit=unit)

    @classmethod
    def from_molar(cls, molar_concentration: float) -> PChemblValue:
        """Create from molar concentration.

        Args:
            molar_concentration: Concentration in molar (M).

        Returns:
            Corresponding pChEMBL value.

        Raises:
            ValueError: If concentration is not positive.
        """
        if molar_concentration <= 0:
            raise ValueError(
                f"Molar concentration must be positive: {molar_concentration}"
            )

        import math
        pchembl = -math.log10(molar_concentration)
        return cls(value=pchembl)

    @classmethod
    def from_concentration(cls, concentration: Concentration) -> PChemblValue:
        """Create from Concentration value object.

        Args:
            concentration: Concentration value object.

        Returns:
            Corresponding pChEMBL value.
        """
        return cls.from_molar(concentration.molar_value)

    @property
    def is_potent(self) -> bool:
        """Check if this is considered potent (pChEMBL >= 5)."""
        return self.value >= 5.0

    @property
    def is_highly_potent(self) -> bool:
        """Check if this is considered highly potent (pChEMBL >= 7)."""
        return self.value >= 7.0

    def __str__(self) -> str:
        """String representation."""
        return f"{self.value:.2f}"

    def __eq__(self, other: object) -> bool:
        """Compare by value."""
        if not isinstance(other, PChemblValue):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash based on value."""
        return hash(self.value)

    def __lt__(self, other: PChemblValue) -> bool:
        """Compare for ordering (higher pChEMBL = more potent)."""
        if not isinstance(other, PChemblValue):
            return NotImplemented
        return self.value < other.value
