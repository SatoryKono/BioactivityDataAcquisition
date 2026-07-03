"""Bioactivity normalization service for ChEMBL activity measurements.

Scope — batch and single-value normalization of bioactivity data (IC50, Ki,
EC50, etc.): unit conversion to a canonical output unit (default: nM), pChEMBL
calculation, potency classification, and multi-value aggregation.

Internal design — mixin chain::

    _NormalizationActivityMixin   (single-value: convert, validate, pChEMBL)
        └── _NormalizationBatchMixin  (multi-value: aggregate, concentrations)
                └── BioactivityNormalizer  (public facade, @dataclass)

Collaborators (all injected via dataclass fields):
- ``NormalizationConfig``  — thresholds, default unit, aggregation method
- ``UnitConverter``        — concentration unit conversion + pChEMBL math
- ``ValueValidator``       — range / format validation
- ``ActivityAggregator``   — geometric-mean / median aggregation

This service is **not** a DataNormalizationPort implementation.
It handles ChEMBL-specific bioactivity scalars only, not cross-provider
metadata fields (authors, DOIs, dates, text).

Cross-reference
---------------
For cross-provider metadata normalization (author, DOI, PMID, date, text)
see :mod:`bioetl.domain.behavior.data_normalization_service`
(``DefaultDataNormalizer``).

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.behavior.activity_aggregator import ActivityAggregator
from bioetl.domain.behavior.normalization_config import NormalizationConfig
from bioetl.domain.behavior.unit_converter import UnitConverter
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.value_objects import PChemblValue

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.value_objects import Concentration

__all__ = [
    "BioactivityNormalizer",
    "NormalizationResult",
]


@dataclass(slots=True)
class NormalizationResult:
    """Result of normalizing a bioactivity value."""

    value: float
    unit: str
    pchembl: PChemblValue | None = None
    is_valid: bool = True
    validation_message: str | None = None
    is_potent: bool = False


class _NormalizationActivityMixin:
    """Single-value normalization and potency classification methods."""

    config: NormalizationConfig
    converter: UnitConverter
    validator: ValueValidator

    def normalize_activity(
        self,
        value: float,
        unit: str,
        activity_type: str,
        *,
        validate: bool = True,
    ) -> NormalizationResult:
        """Normalize a single activity value to canonical unit with pChEMBL."""
        del activity_type
        if validate:
            is_valid, error = self.validator.validate_concentration(value, unit)
            if not is_valid:
                return NormalizationResult(
                    value=value, unit=unit, is_valid=False, validation_message=error
                )

        target_unit = self.config.default_output_unit
        try:
            normalized_value = self.converter.convert(value, unit, target_unit)
        except ValueError as error:
            return NormalizationResult(
                value=value, unit=unit, is_valid=False, validation_message=str(error)
            )

        pchembl, is_potent = self._compute_pchembl_for_value(normalized_value)
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
        """Normalize activity to pChEMBL value, or None on failure."""
        try:
            pchembl = self.converter.value_to_pchembl(value, unit)
            if validate:
                is_valid, _ = self.validator.validate_pchembl(pchembl.value)
                if not is_valid:
                    return None
            return pchembl
        except ValueError:
            return None

    def _compute_pchembl_for_value(
        self, value: float
    ) -> tuple[PChemblValue | None, bool]:
        """Compute pChEMBL value and potency for a normalized value."""
        try:
            pchembl = self.converter.value_to_pchembl(
                value, self.config.default_output_unit
            )
            return pchembl, pchembl.value >= self.config.potency_threshold
        except ValueError:
            return None, False

    def is_potent(self, pchembl_value: float) -> bool:
        """Check if pChEMBL value meets the configured potency threshold."""
        return self.validator.is_potent(pchembl_value, self.config.potency_threshold)

    def is_highly_potent(self, pchembl_value: float) -> bool:
        """Check if pChEMBL value meets the configured high-potency threshold."""
        return self.validator.is_highly_potent(
            pchembl_value, self.config.high_potency_threshold
        )

    def classify_potency(self, pchembl_value: float) -> str:
        """Classify potency level based on pChEMBL value."""
        if pchembl_value < 4.0:
            return "inactive"
        if pchembl_value < self.config.potency_threshold:
            return "weak"
        if pchembl_value < 6.0:
            return "moderate"
        if pchembl_value < self.config.high_potency_threshold:
            return "potent"
        return "highly_potent"


class _NormalizationBatchMixin(_NormalizationActivityMixin):
    """Batch normalization and aggregation methods."""

    config: NormalizationConfig
    aggregator: ActivityAggregator

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

        Args:
            values: Sequence of raw activity measurements to normalize.
            unit: Unit string shared by all values (e.g., 'nM').
            activity_type: Activity type label for each value (e.g., 'IC50').
            aggregate: If True, aggregate results into a single value. Defaults to True.
            filter_invalid: If True, exclude invalid results before aggregation. Defaults to True.

        Returns:
            Single aggregated NormalizationResult if aggregate is True, otherwise a list
            of individual NormalizationResult objects for each input value.
        """
        results = [
            self.normalize_activity(v, unit, activity_type, validate=True)
            for v in values
        ]
        return (
            self._aggregate_results(results, filter_invalid) if aggregate else results
        )

    def _aggregate_results(
        self,
        results: list[NormalizationResult],
        filter_invalid: bool,
    ) -> NormalizationResult:
        """Aggregate multiple normalization results into one."""
        valid_results = (
            [r for r in results if r.is_valid] if filter_invalid else results
        )
        if not valid_results:
            return NormalizationResult(
                value=0.0,
                unit=self.config.default_output_unit,
                is_valid=False,
                validation_message="No valid values to aggregate",
            )
        return self._build_aggregated_result(valid_results)

    def _build_aggregated_result(
        self, valid_results: list[NormalizationResult]
    ) -> NormalizationResult:
        """Build aggregated result from valid results."""
        aggregated = self.aggregator.aggregate_values(
            [result.value for result in valid_results],
            self.config.default_aggregation_method,
        )
        pchembl, is_potent = self._compute_pchembl_for_value(aggregated)
        return NormalizationResult(
            value=aggregated,
            unit=self.config.default_output_unit,
            pchembl=pchembl,
            is_valid=True,
            is_potent=is_potent,
        )

    def normalize_concentrations(
        self,
        concentrations: Sequence[Concentration],
        activity_type: str = "IC50",
    ) -> NormalizationResult:
        """Normalize and aggregate Concentration objects.

        Args:
            concentrations: Sequence of Concentration value objects to normalize and aggregate.
            activity_type: Activity type label. Reserved for future type-specific logic. Defaults to 'IC50'.

        Returns:
            Single NormalizationResult with aggregated value. Returns an invalid result if
            concentrations is empty.
        """
        del activity_type
        if not concentrations:
            return NormalizationResult(
                value=0.0,
                unit=self.config.default_output_unit,
                is_valid=False,
                validation_message="No concentrations to normalize",
            )

        aggregated = self.aggregator.aggregate_concentrations(
            concentrations, self.config.default_aggregation_method
        )

        pchembl, is_potent = None, False
        try:
            pchembl = self.converter.to_pchembl(aggregated)
            is_potent = pchembl.value >= self.config.potency_threshold
        except ValueError:
            pass  # Why: pChEMBL conversion not applicable for this unit; return result without pchembl

        return NormalizationResult(
            value=aggregated.value,
            unit=aggregated.unit.value,
            pchembl=pchembl,
            is_valid=True,
            is_potent=is_potent,
        )


@dataclass(slots=True)
class BioactivityNormalizer(_NormalizationBatchMixin):
    """Facade normalizer for bioactivity activity-value normalization."""

    config: NormalizationConfig = field(default_factory=NormalizationConfig)
    converter: UnitConverter = field(default_factory=UnitConverter)
    validator: ValueValidator = field(default_factory=ValueValidator)
    aggregator: ActivityAggregator = field(default_factory=ActivityAggregator)

    def __post_init__(self) -> None:
        """Initialize validator with config settings."""
        self.validator.strict = self.config.strict_validation
