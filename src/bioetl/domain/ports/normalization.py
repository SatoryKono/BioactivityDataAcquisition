"""Normalization service port interfaces (Protocols).

Defines contracts for bioactivity normalization services:
- UnitConverterPort: Unit conversion (nM → µM, IC50 → pIC50)
- ValueValidatorPort: Range validation for bioactivity values
- ActivityAggregatorPort: Aggregation of multiple measurements
- OutlierFilterPort: Anomaly detection and filtering
- NormalizationServicePort: Orchestrator facade

All ports follow the Ports & Adapters pattern per RULES.md §1.1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.value_objects.activity_values import (
        ActivityType,
        Concentration,
        ConcentrationUnit,
        PChemblValue,
    )


@runtime_checkable
class UnitConverterPort(Protocol):
    """Port for unit conversion operations.

    Handles conversion between different concentration units and
    calculation of standardized values (pIC50, pEC50, etc.).
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
            from_unit: Source unit (e.g., "nM", "µM").
            to_unit: Target unit (e.g., "nM", "µM").

        Returns:
            Converted value in target unit.

        Raises:
            ValueError: If units are not recognized.
        """
        ...

    def to_concentration(
        self,
        value: float,
        unit: str,
    ) -> Concentration:
        """Create Concentration value object from raw values.

        Args:
            value: Numeric concentration value.
            unit: Unit string (e.g., "nM", "µM").

        Returns:
            Concentration value object.

        Raises:
            ValueError: If unit is not recognized or value is negative.
        """
        ...

    def to_pchembl(
        self,
        concentration: Concentration,
    ) -> PChemblValue:
        """Convert concentration to pChEMBL value (-log10 molar).

        Args:
            concentration: Concentration value object.

        Returns:
            pChEMBL value object.

        Raises:
            ValueError: If concentration is not positive.
        """
        ...

    def pchembl_to_concentration(
        self,
        pchembl: PChemblValue,
        target_unit: ConcentrationUnit,
    ) -> Concentration:
        """Convert pChEMBL value to concentration.

        Args:
            pchembl: pChEMBL value object.
            target_unit: Target concentration unit.

        Returns:
            Concentration value object.
        """
        ...


@runtime_checkable
class ValueValidatorPort(Protocol):
    """Port for bioactivity value validation.

    Validates that bioactivity values fall within acceptable ranges
    based on the measurement type.
    """

    def validate_concentration(
        self,
        value: float,
        unit: str,
    ) -> tuple[bool, str | None]:
        """Validate concentration value is within acceptable range.

        Args:
            value: Concentration value.
            unit: Unit string.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        ...

    def validate_pchembl(
        self,
        value: float,
    ) -> tuple[bool, str | None]:
        """Validate pChEMBL value is within acceptable range.

        pChEMBL values typically range from 2 to 14.

        Args:
            value: pChEMBL value.

        Returns:
            Tuple of (is_valid, error_message).
        """
        ...

    def validate_activity_value(
        self,
        value: float,
        activity_type: ActivityType,
        unit: str | None = None,
    ) -> tuple[bool, str | None]:
        """Validate activity value based on measurement type.

        Args:
            value: Activity measurement value.
            activity_type: Type of measurement (IC50, EC50, Ki, etc.).
            unit: Optional unit for context-aware validation.

        Returns:
            Tuple of (is_valid, error_message).
        """
        ...


@runtime_checkable
class OutlierFilterPort(Protocol):
    """Port for outlier detection and filtering.

    Detects anomalous values using statistical methods.
    """

    def is_outlier(
        self,
        value: float,
        baseline: Sequence[float],
        threshold: float = 2.0,
    ) -> bool:
        """Check if value is an outlier relative to baseline.

        Args:
            value: Value to check.
            baseline: Historical values for comparison.
            threshold: Detection threshold (e.g., z-score threshold).

        Returns:
            True if value is considered an outlier.
        """
        ...

    def filter_outliers(
        self,
        values: Sequence[float],
        threshold: float = 2.0,
    ) -> list[float]:
        """Filter outliers from a sequence of values.

        Args:
            values: Sequence of values to filter.
            threshold: Detection threshold.

        Returns:
            List of values with outliers removed.
        """
        ...


@runtime_checkable
class ActivityAggregatorPort(Protocol):
    """Port for aggregating multiple activity measurements.

    Handles combination of replicate measurements and
    calculation of summary statistics.
    """

    def aggregate_values(
        self,
        values: Sequence[float],
        method: str = "median",
    ) -> float:
        """Aggregate multiple values into a single representative value.

        Args:
            values: Sequence of values to aggregate.
            method: Aggregation method ("mean", "median", "geometric_mean").

        Returns:
            Aggregated value.

        Raises:
            ValueError: If values is empty or method is unknown.
        """
        ...

    def aggregate_with_uncertainty(
        self,
        values: Sequence[float],
        method: str = "median",
    ) -> tuple[float, float]:
        """Aggregate values and calculate uncertainty.

        Args:
            values: Sequence of values to aggregate.
            method: Aggregation method.

        Returns:
            Tuple of (aggregated_value, uncertainty).
            Uncertainty is standard deviation or MAD depending on method.
        """
        ...

    def aggregate_concentrations(
        self,
        concentrations: Sequence[Concentration],
        method: str = "median",
    ) -> Concentration:
        """Aggregate multiple concentration measurements.

        All concentrations are converted to common unit before aggregation.

        Args:
            concentrations: Sequence of Concentration objects.
            method: Aggregation method.

        Returns:
            Aggregated Concentration in nanomolar (nM).

        Raises:
            ValueError: If concentrations is empty.
        """
        ...


@runtime_checkable
class NormalizationServicePort(Protocol):
    """Port for the normalization service facade.

    Orchestrates unit conversion, validation, filtering, and aggregation
    for bioactivity data normalization.
    """

    @property
    def converter(self) -> UnitConverterPort:
        """Access unit converter service."""
        ...

    @property
    def validator(self) -> ValueValidatorPort:
        """Access value validator service."""
        ...

    @property
    def aggregator(self) -> ActivityAggregatorPort:
        """Access activity aggregator service."""
        ...

    def normalize_activity(
        self,
        value: float,
        unit: str,
        activity_type: str,
        *,
        validate: bool = True,
    ) -> tuple[float, str] | None:
        """Normalize a single activity value.

        Converts to standard unit (nM) and validates.

        Args:
            value: Raw activity value.
            unit: Unit of the value.
            activity_type: Type of measurement (IC50, EC50, etc.).
            validate: Whether to validate the value.

        Returns:
            Tuple of (normalized_value, normalized_unit) or None if invalid.
        """
        ...

    def normalize_to_pchembl(
        self,
        value: float,
        unit: str,
        *,
        validate: bool = True,
    ) -> PChemblValue | None:
        """Normalize activity to pChEMBL value.

        Args:
            value: Activity value.
            unit: Unit of the value.
            validate: Whether to validate the result.

        Returns:
            pChEMBL value or None if invalid/unconvertible.
        """
        ...
