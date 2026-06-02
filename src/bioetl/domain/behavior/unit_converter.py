"""Unit converter service for bioactivity measurements.

Wraps domain value objects (Concentration, PChemblValue) to provide
a service interface for unit conversion operations.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.value_objects import (
    Concentration,
    ConcentrationUnit,
    PChemblValue,
)

__all__ = [
    "UnitConverter",
]


@dataclass(frozen=True, slots=True)
class UnitConverter:
    """Service for converting between bioactivity units.

    Wraps domain value objects to provide convenient conversion methods.
    Stateless and thread-safe.

    Example:
        >>> converter = UnitConverter()
        >>> result = converter.convert(100.0, "nM", "µM")
        >>> result
        0.1

        >>> conc = converter.to_concentration(100.0, "nM")
        >>> pchembl = converter.to_pchembl(conc)
        >>> str(pchembl)
        '7.00'
    """

    def convert(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> float:
        """Convert value between concentration units.

        Args:
            value: Numeric value to convert.
            from_unit: Source unit (e.g., "nM", "µM", "uM", "mM", "M").
            to_unit: Target unit.

        Returns:
            Converted value in target unit.

        Raises:
            ValueError: If units are not recognized or value is negative.

        Example:
            >>> converter = UnitConverter()
            >>> converter.convert(1000.0, "nM", "µM")
            1.0
            >>> converter.convert(1.0, "µM", "nM")
            1000.0
        """
        source_unit = ConcentrationUnit.from_string(from_unit)
        target_unit = ConcentrationUnit.from_string(to_unit)

        concentration = Concentration(value=value, unit=source_unit)
        converted = concentration.to_unit(target_unit)

        return converted.value

    def to_concentration(
        self,
        value: float,
        unit: str,
    ) -> Concentration:
        """Create Concentration value object from raw values.

        Args:
            value: Numeric concentration value (must be >= 0).
            unit: Unit string (e.g., "nM", "µM", "uM", "mM").

        Returns:
            Concentration value object.

        Raises:
            ValueError: If unit is not recognized or value is negative.

        Example:
            >>> converter = UnitConverter()
            >>> conc = converter.to_concentration(100.0, "nM")
            >>> str(conc)
            '100 nM'
        """
        parsed_unit = ConcentrationUnit.from_string(unit)
        return Concentration(value=value, unit=parsed_unit)

    def to_pchembl(
        self,
        concentration: Concentration,
    ) -> PChemblValue:
        """Convert concentration to pChEMBL value (-log10 molar).

        pChEMBL values are standardized potency measures.
        Higher values indicate higher potency.

        Args:
            concentration: Concentration value object.

        Returns:
            pChEMBL value object.

        Raises:
            ValueError: If concentration is zero or negative.

        Example:
            >>> converter = UnitConverter()
            >>> conc = Concentration(100.0, ConcentrationUnit.NANOMOLAR)
            >>> pchembl = converter.to_pchembl(conc)
            >>> str(pchembl)
            '7.00'
        """
        return PChemblValue.from_concentration(concentration)

    def pchembl_to_concentration(
        self,
        pchembl: PChemblValue,
        target_unit: ConcentrationUnit | str = ConcentrationUnit.NANOMOLAR,
    ) -> Concentration:
        """Convert pChEMBL value to concentration.

        Args:
            pchembl: pChEMBL value object.
            target_unit: Target concentration unit (default: nM).

        Returns:
            Concentration value object.

        Example:
            >>> converter = UnitConverter()
            >>> pchembl = PChemblValue(7.0)  # 100 nM
            >>> conc = converter.pchembl_to_concentration(pchembl)
            >>> f"{conc.value:.1f} {conc.unit.value}"
            '100.0 nM'
        """
        if isinstance(target_unit, str):
            target_unit = ConcentrationUnit.from_string(target_unit)
        return pchembl.to_concentration(target_unit)

    def normalize_to_nanomolar(
        self,
        value: float,
        unit: str,
    ) -> float:
        """Normalize any concentration to nanomolar.

        Convenience method for standardizing to common unit.

        Args:
            value: Concentration value.
            unit: Source unit string.

        Returns:
            Value in nanomolar (nM).

        Example:
            >>> converter = UnitConverter()
            >>> converter.normalize_to_nanomolar(1.0, "µM")
            1000.0
        """
        return self.convert(value, unit, "nM")

    def normalize_to_micromolar(
        self,
        value: float,
        unit: str,
    ) -> float:
        """Normalize any concentration to micromolar.

        Args:
            value: Concentration value.
            unit: Source unit string.

        Returns:
            Value in micromolar (µM).

        Example:
            >>> converter = UnitConverter()
            >>> converter.normalize_to_micromolar(1000.0, "nM")
            1.0
        """
        return self.convert(value, unit, "uM")

    def value_to_pchembl(
        self,
        value: float,
        unit: str,
    ) -> PChemblValue:
        """Convert raw value with unit directly to pChEMBL.

        Convenience method combining to_concentration and to_pchembl.

        Args:
            value: Concentration value (must be positive).
            unit: Unit string.

        Returns:
            pChEMBL value object.

        Raises:
            ValueError: If value is not positive or unit unknown.

        Example:
            >>> converter = UnitConverter()
            >>> pchembl = converter.value_to_pchembl(100.0, "nM")
            >>> str(pchembl)
            '7.00'
        """
        concentration = self.to_concentration(value, unit)
        return self.to_pchembl(concentration)
