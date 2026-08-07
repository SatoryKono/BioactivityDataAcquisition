"""pChEMBL value object and conversion helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.value_objects.activity_concentration import (
    Concentration,
    ConcentrationUnit,
)


@dataclass(frozen=True, slots=True)
class PChemblValue:
    """pChEMBL value: -log10 of molar activity."""

    value: float

    def __post_init__(self) -> None:
        """Validate pChEMBL value invariants."""
        if self.value < 0:
            raise ValueError(f"pChEMBL value cannot be negative: {self.value}")
        if self.value > 14:
            raise ValueError(f"pChEMBL value exceeds physical limit (14): {self.value}")

    def to_molar(self) -> float:
        """Convert to molar concentration.

        Returns:
            Molar concentration as 10^(-pChEMBL value) in molar (M) units.
        """
        return 10 ** (-self.value)

    def to_concentration(
        self, unit: ConcentrationUnit = ConcentrationUnit.NANOMOLAR
    ) -> Concentration:
        """Convert to Concentration value object.

        Args:
            unit: Target concentration unit. Defaults to nanomolar (nM).

        Returns:
            Concentration value object expressed in the requested unit.
        """
        molar = self.to_molar()
        value_in_unit = molar / unit.to_molar_factor
        return Concentration(value=value_in_unit, unit=unit)

    @classmethod
    def from_molar(cls, molar_concentration: float) -> PChemblValue:
        """Create from molar concentration.

        Args:
            molar_concentration: Concentration in molar (M) units. Must be positive.

        Returns:
            PChemblValue computed as -log10(molar_concentration).
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
            concentration: Concentration value object in any supported unit.

        Returns:
            PChemblValue derived from the concentration's molar equivalent.
        """
        return cls.from_molar(concentration.molar_value)

    @property
    def is_potent(self) -> bool:
        """Check if compound is considered potent."""
        return self.value >= 5.0

    @property
    def is_highly_potent(self) -> bool:
        """Check if compound is considered highly potent."""
        return self.value >= 7.0

    def __str__(self) -> str:
        """Return string representation with 2 decimal places."""
        return f"{self.value:.2f}"

    def __eq__(self, other: object) -> bool:
        """Compare equality by value."""
        if not isinstance(other, PChemblValue):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        """Compute hash based on value for use in sets and dicts."""
        return hash(self.value)

    def __lt__(self, other: object) -> bool:
        """Compare for ordering (lower value = less potent)."""
        if not isinstance(other, PChemblValue):
            return NotImplemented
        return self.value < other.value


__all__ = ["PChemblValue"]
