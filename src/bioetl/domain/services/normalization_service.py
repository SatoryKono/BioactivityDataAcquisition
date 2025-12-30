"""Normalization service facade for bioactivity data.

Orchestrates unit conversion, validation, and aggregation services
to provide a unified interface for normalizing bioactivity measurements.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.services.activity_aggregator import ActivityAggregator
from bioetl.domain.services.normalization_config import NormalizationConfig
from bioetl.domain.services.unit_converter import UnitConverter
from bioetl.domain.services.value_validator import ValueValidator
from bioetl.domain.value_objects.activity_values import PChemblValue

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.value_objects.activity_values import Concentration


@dataclass(slots=True)
class NormalizationResult:
    """Result of normalizing a bioactivity value.

    Attributes:
        value: Normalized value.
        unit: Normalized unit (typically "nM").
        pchembl: Optional pChEMBL value if calculable.
        is_valid: Whether the value passed validation.
        validation_message: Error message if validation failed.
        is_potent: Whether pChEMBL >= potency threshold.
    """

    value: float
    unit: str
    pchembl: PChemblValue | None = None
    is_valid: bool = True
    validation_message: str | None = None
    is_potent: bool = False


@dataclass(slots=True)
class NormalizationService:
    """Facade service for bioactivity data normalization.

    Orchestrates specialized services for comprehensive normalization:
    - UnitConverter: Converts between concentration units
    - ValueValidator: Validates value ranges
    - ActivityAggregator: Aggregates replicate measurements

    This service is a thin orchestrator following the Facade pattern.
    All business logic is delegated to specialized services.

    Attributes:
        config: Configuration for normalization behavior.
        converter: Unit converter service (injected or created).
        validator: Value validator service (injected or created).
        aggregator: Activity aggregator service (injected or created).

    Example:
        >>> config = NormalizationConfig()
        >>> service = NormalizationService(config)
        >>> result = service.normalize_activity(100.0, "nM", "IC50")
        >>> print(f"{result.value} {result.unit}, pChEMBL={result.pchembl}")
        100.0 nM, pChEMBL=7.00

        >>> # With validation
        >>> result = service.normalize_activity(-50.0, "nM", "IC50")
        >>> print(result.is_valid, result.validation_message)
        False Concentration cannot be negative: -50.0
    """

    config: NormalizationConfig = field(default_factory=NormalizationConfig)
    converter: UnitConverter = field(default_factory=UnitConverter)
    validator: ValueValidator = field(default_factory=ValueValidator)
    aggregator: ActivityAggregator = field(default_factory=ActivityAggregator)

    def __post_init__(self) -> None:
        """Initialize validator with config settings."""
        self.validator.strict = self.config.strict_validation

    def normalize_activity(
        self,
        value: float,
        unit: str,
        activity_type: str,  # noqa: ARG002 - reserved for type-specific validation
        *,
        validate: bool = True,
    ) -> NormalizationResult:
        """Normalize a single activity value.

        Converts to standard unit (nM), validates, and calculates pChEMBL.

        Args:
            value: Raw activity value.
            unit: Unit of the value (e.g., "nM", "µM").
            activity_type: Type of measurement (IC50, EC50, Ki, etc.).
                Reserved for future type-specific validation.
            validate: Whether to validate the value.

        Returns:
            NormalizationResult with normalized value and metadata.

        Example:
            >>> service = NormalizationService()
            >>> result = service.normalize_activity(1.0, "µM", "IC50")
            >>> print(f"{result.value} {result.unit}")
            1000.0 nM
        """
        # Validate first if requested
        if validate:
            is_valid, error = self.validator.validate_concentration(value, unit)
            if not is_valid:
                return NormalizationResult(
                    value=value,
                    unit=unit,
                    is_valid=False,
                    validation_message=error,
                )

        # Convert to standard unit (nM)
        target_unit = self.config.default_output_unit
        try:
            normalized_value = self.converter.convert(value, unit, target_unit)
        except ValueError as e:
            return NormalizationResult(
                value=value,
                unit=unit,
                is_valid=False,
                validation_message=str(e),
            )

        # Calculate pChEMBL if possible
        pchembl = None
        is_potent = False
        try:
            pchembl = self.converter.value_to_pchembl(normalized_value, target_unit)
            is_potent = pchembl.value >= self.config.potency_threshold
        except ValueError:
            # Value might be zero or negative - pChEMBL not calculable
            pass

        return NormalizationResult(
            value=normalized_value,
            unit=target_unit,
            pchembl=pchembl,
            is_valid=True,
            is_potent=is_potent,
        )

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

        Example:
            >>> service = NormalizationService()
            >>> pchembl = service.normalize_to_pchembl(100.0, "nM")
            >>> print(pchembl)
            7.00
        """
        try:
            pchembl = self.converter.value_to_pchembl(value, unit)

            if validate:
                is_valid, _ = self.validator.validate_pchembl(pchembl.value)
                if not is_valid:
                    return None

            return pchembl
        except ValueError:
            return None

    def normalize_multiple(
        self,
        values: Sequence[float],
        unit: str,
        activity_type: str,
        *,
        aggregate: bool = True,
        filter_invalid: bool = True,
    ) -> NormalizationResult | list[NormalizationResult]:
        """Normalize multiple activity values.

        Can optionally aggregate into a single representative value.

        Args:
            values: Sequence of activity values.
            unit: Common unit for all values.
            activity_type: Type of measurement.
            aggregate: If True, return single aggregated result.
            filter_invalid: If True, exclude invalid values from aggregation.

        Returns:
            Single NormalizationResult if aggregate=True,
            otherwise list of NormalizationResult.

        Example:
            >>> service = NormalizationService()
            >>> result = service.normalize_multiple(
            ...     [90.0, 100.0, 110.0],
            ...     "nM",
            ...     "IC50"
            ... )
            >>> print(f"{result.value} {result.unit}")
            100.0 nM
        """
        # Normalize each value
        results = [
            self.normalize_activity(v, unit, activity_type, validate=True)
            for v in values
        ]

        if not aggregate:
            return results

        # Filter to valid values if requested
        if filter_invalid:
            valid_results = [r for r in results if r.is_valid]
        else:
            valid_results = results

        if not valid_results:
            return NormalizationResult(
                value=0.0,
                unit=self.config.default_output_unit,
                is_valid=False,
                validation_message="No valid values to aggregate",
            )

        # Aggregate values
        valid_values = [r.value for r in valid_results]
        aggregated = self.aggregator.aggregate_values(
            valid_values,
            self.config.default_aggregation_method,
        )

        # Calculate pChEMBL for aggregated value
        pchembl = None
        is_potent = False
        target_unit = self.config.default_output_unit
        try:
            pchembl = self.converter.value_to_pchembl(aggregated, target_unit)
            is_potent = pchembl.value >= self.config.potency_threshold
        except ValueError:
            pass

        return NormalizationResult(
            value=aggregated,
            unit=target_unit,
            pchembl=pchembl,
            is_valid=True,
            is_potent=is_potent,
        )

    def normalize_concentrations(
        self,
        concentrations: Sequence[Concentration],
        activity_type: str = "IC50",  # noqa: ARG002 - reserved for type-specific
    ) -> NormalizationResult:
        """Normalize and aggregate Concentration objects.

        Args:
            concentrations: Sequence of Concentration value objects.
            activity_type: Type of measurement.
                Reserved for future type-specific aggregation.

        Returns:
            Aggregated NormalizationResult.

        Example:
            >>> from bioetl.domain.value_objects import Concentration, ConcentrationUnit
            >>> service = NormalizationService()
            >>> concs = [
            ...     Concentration(100.0, ConcentrationUnit.NANOMOLAR),
            ...     Concentration(0.1, ConcentrationUnit.MICROMOLAR),
            ... ]
            >>> result = service.normalize_concentrations(concs)
        """
        if not concentrations:
            return NormalizationResult(
                value=0.0,
                unit=self.config.default_output_unit,
                is_valid=False,
                validation_message="No concentrations to normalize",
            )

        # Aggregate concentrations
        aggregated = self.aggregator.aggregate_concentrations(
            concentrations,
            self.config.default_aggregation_method,
        )

        # Calculate pChEMBL
        pchembl = None
        is_potent = False
        try:
            pchembl = self.converter.to_pchembl(aggregated)
            is_potent = pchembl.value >= self.config.potency_threshold
        except ValueError:
            pass

        return NormalizationResult(
            value=aggregated.value,
            unit=aggregated.unit.value,
            pchembl=pchembl,
            is_valid=True,
            is_potent=is_potent,
        )

    def is_potent(self, pchembl_value: float) -> bool:
        """Check if pChEMBL value indicates potent activity.

        Args:
            pchembl_value: pChEMBL value to check.

        Returns:
            True if potent (pChEMBL >= threshold).
        """
        return self.validator.is_potent(
            pchembl_value,
            self.config.potency_threshold,
        )

    def is_highly_potent(self, pchembl_value: float) -> bool:
        """Check if pChEMBL value indicates highly potent activity.

        Args:
            pchembl_value: pChEMBL value to check.

        Returns:
            True if highly potent (pChEMBL >= high threshold).
        """
        return self.validator.is_highly_potent(
            pchembl_value,
            self.config.high_potency_threshold,
        )

    def classify_potency(
        self,
        pchembl_value: float,
    ) -> str:
        """Classify potency level based on pChEMBL value.

        Args:
            pchembl_value: pChEMBL value to classify.

        Returns:
            Potency classification: "inactive", "weak", "moderate",
            "potent", or "highly_potent".

        Example:
            >>> service = NormalizationService()
            >>> service.classify_potency(4.0)
            'weak'
            >>> service.classify_potency(7.5)
            'potent'
        """
        if pchembl_value < 4.0:
            return "inactive"
        elif pchembl_value < self.config.potency_threshold:
            return "weak"
        elif pchembl_value < 6.0:
            return "moderate"
        elif pchembl_value < self.config.high_potency_threshold:
            return "potent"
        else:
            return "highly_potent"
