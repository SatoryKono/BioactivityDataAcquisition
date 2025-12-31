"""Activity aggregator service for bioactivity measurements.

Handles aggregation of multiple activity measurements into
representative values with uncertainty estimates.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.activity_values import (
    Concentration,
    ConcentrationUnit,
)

if TYPE_CHECKING:
    from bioetl.domain.services.normalization_config import NormalizationConfig


class AggregationMethod(str, Enum):
    """Supported aggregation methods for bioactivity values."""

    MEAN = "mean"
    MEDIAN = "median"
    GEOMETRIC_MEAN = "geometric_mean"
    MINIMUM = "min"
    MAXIMUM = "max"


def _geometric_mean(values: Sequence[float]) -> float:
    """Calculate geometric mean of positive values.

    Args:
        values: Sequence of positive values.

    Returns:
        Geometric mean.

    Raises:
        ValueError: If any value is not positive.
    """
    if not values:
        raise ValueError("Cannot calculate geometric mean of empty sequence")

    for v in values:
        if v <= 0:
            raise ValueError(
                f"Geometric mean requires positive values, got {v}"
            )

    log_sum = sum(math.log(v) for v in values)
    return math.exp(log_sum / len(values))


def _median_absolute_deviation(values: Sequence[float]) -> float:
    """Calculate Median Absolute Deviation (MAD).

    MAD is a robust measure of statistical dispersion.

    Args:
        values: Sequence of values.

    Returns:
        MAD value.
    """
    if len(values) < 2:
        return 0.0

    med = statistics.median(values)
    deviations = [abs(v - med) for v in values]
    return statistics.median(deviations)


@dataclass(slots=True)
class ActivityAggregator:
    """Service for aggregating multiple activity measurements.

    Combines replicate measurements using various statistical methods
    and calculates uncertainty estimates.

    Attributes:
        config: Optional configuration for aggregation settings.
        default_method: Default aggregation method (median recommended
            for robustness against outliers).

    Example:
        >>> aggregator = ActivityAggregator()
        >>> values = [95.0, 100.0, 105.0, 110.0]
        >>> result = aggregator.aggregate_values(values)
        >>> print(result)
        102.5

        >>> value, uncertainty = aggregator.aggregate_with_uncertainty(values)
        >>> print(f"{value:.1f} +/- {uncertainty:.1f}")
        102.5 +/- 5.0
    """

    config: NormalizationConfig | None = None
    default_method: AggregationMethod = AggregationMethod.MEDIAN

    def aggregate_values(
        self,
        values: Sequence[float],
        method: str | AggregationMethod = "median",
    ) -> float:
        """Aggregate multiple values into a single representative value.

        Args:
            values: Sequence of values to aggregate (must be non-empty).
            method: Aggregation method. Supported: "mean", "median",
                "geometric_mean", "min", "max".

        Returns:
            Aggregated value.

        Raises:
            ValueError: If values is empty or method is unknown.

        Example:
            >>> aggregator = ActivityAggregator()
            >>> aggregator.aggregate_values([1.0, 2.0, 3.0], "mean")
            2.0
            >>> aggregator.aggregate_values([1.0, 2.0, 3.0], "median")
            2.0
        """
        if not values:
            raise ValueError("Cannot aggregate empty sequence")

        value_list = list(values)
        parsed_method = self._parse_method(method)
        return self._apply_aggregation(value_list, parsed_method)

    def _parse_method(self, method: str | AggregationMethod) -> AggregationMethod:
        """Parse aggregation method string to enum."""
        if isinstance(method, AggregationMethod):
            return method
        try:
            return AggregationMethod(method.lower())
        except ValueError as err:
            raise ValueError(f"Unknown aggregation method: {method}") from err

    def _apply_aggregation(
        self,
        values: list[float],
        method: AggregationMethod,
    ) -> float:
        """Apply aggregation method to values."""
        aggregators: dict[AggregationMethod, Callable[[Sequence[float]], float]] = {
            AggregationMethod.MEAN: statistics.mean,
            AggregationMethod.MEDIAN: statistics.median,
            AggregationMethod.GEOMETRIC_MEAN: _geometric_mean,
            AggregationMethod.MINIMUM: min,
            AggregationMethod.MAXIMUM: max,
        }
        aggregator = aggregators.get(method)
        if aggregator is None:
            raise ValueError(f"Unsupported aggregation method: {method}")
        return aggregator(values)

    def aggregate_with_uncertainty(
        self,
        values: Sequence[float],
        method: str | AggregationMethod = "median",
    ) -> tuple[float, float]:
        """Aggregate values and calculate uncertainty.

        For mean: uses standard deviation.
        For median: uses Median Absolute Deviation (MAD).
        For geometric_mean: uses log-space standard deviation.

        Args:
            values: Sequence of values to aggregate.
            method: Aggregation method.

        Returns:
            Tuple of (aggregated_value, uncertainty).

        Example:
            >>> aggregator = ActivityAggregator()
            >>> values = [95.0, 100.0, 105.0, 110.0]
            >>> value, uncertainty = aggregator.aggregate_with_uncertainty(values, "mean")
            >>> print(f"{value:.1f} +/- {uncertainty:.1f}")
            102.5 +/- 6.5
        """
        if not values:
            raise ValueError("Cannot aggregate empty sequence")

        value_list = list(values)
        aggregated = self.aggregate_values(value_list, method)
        parsed_method = self._parse_method(method)
        uncertainty = self._calculate_uncertainty(value_list, parsed_method, aggregated)

        return aggregated, uncertainty

    def _calculate_uncertainty(
        self,
        values: list[float],
        method: AggregationMethod,
        aggregated: float,
    ) -> float:
        """Calculate uncertainty based on aggregation method."""
        if len(values) < 2:
            return 0.0

        if method == AggregationMethod.MEDIAN:
            return _median_absolute_deviation(values)
        if method == AggregationMethod.GEOMETRIC_MEAN:
            return self._geometric_uncertainty(values, aggregated)
        return statistics.stdev(values)

    def _geometric_uncertainty(
        self,
        values: list[float],
        aggregated: float,
    ) -> float:
        """Calculate uncertainty for geometric mean using log-space std."""
        log_values = [math.log(v) for v in values if v > 0]
        if len(log_values) < 2:
            return 0.0
        log_std = statistics.stdev(log_values)
        return aggregated * (math.exp(log_std) - 1)

    def aggregate_concentrations(
        self,
        concentrations: Sequence[Concentration],
        method: str | AggregationMethod = "median",
    ) -> Concentration:
        """Aggregate multiple concentration measurements.

        All concentrations are converted to nanomolar before aggregation,
        then the result is returned in nanomolar.

        Args:
            concentrations: Sequence of Concentration objects.
            method: Aggregation method.

        Returns:
            Aggregated Concentration in nanomolar (nM).

        Raises:
            ValueError: If concentrations is empty.

        Example:
            >>> from bioetl.domain.value_objects import Concentration, ConcentrationUnit
            >>> aggregator = ActivityAggregator()
            >>> concs = [
            ...     Concentration(100.0, ConcentrationUnit.NANOMOLAR),
            ...     Concentration(0.1, ConcentrationUnit.MICROMOLAR),
            ...     Concentration(0.15, ConcentrationUnit.MICROMOLAR),
            ... ]
            >>> result = aggregator.aggregate_concentrations(concs)
            >>> print(f"{result.value:.1f} {result.unit.value}")
            100.0 nM
        """
        if not concentrations:
            raise ValueError("Cannot aggregate empty sequence of concentrations")

        # Convert all to nanomolar
        nm_values = [c.to_nanomolar().value for c in concentrations]

        # Aggregate
        aggregated = self.aggregate_values(nm_values, method)

        return Concentration(value=aggregated, unit=ConcentrationUnit.NANOMOLAR)

    def aggregate_concentrations_with_uncertainty(
        self,
        concentrations: Sequence[Concentration],
        method: str | AggregationMethod = "median",
    ) -> tuple[Concentration, float]:
        """Aggregate concentrations with uncertainty estimate.

        Args:
            concentrations: Sequence of Concentration objects.
            method: Aggregation method.

        Returns:
            Tuple of (aggregated_concentration, uncertainty_in_nm).

        Example:
            >>> aggregator = ActivityAggregator()
            >>> # ... setup concentrations
            >>> conc, uncertainty = aggregator.aggregate_concentrations_with_uncertainty(concs)
        """
        if not concentrations:
            raise ValueError("Cannot aggregate empty sequence of concentrations")

        nm_values = [c.to_nanomolar().value for c in concentrations]
        aggregated, uncertainty = self.aggregate_with_uncertainty(nm_values, method)

        result_conc = Concentration(
            value=aggregated,
            unit=ConcentrationUnit.NANOMOLAR,
        )

        return result_conc, uncertainty

    def weighted_aggregate(
        self,
        values: Sequence[float],
        weights: Sequence[float],
    ) -> float:
        """Calculate weighted average of values.

        Args:
            values: Sequence of values.
            weights: Sequence of weights (must have same length as values).

        Returns:
            Weighted average.

        Raises:
            ValueError: If lengths don't match or weights sum to zero.

        Example:
            >>> aggregator = ActivityAggregator()
            >>> values = [100.0, 200.0, 300.0]
            >>> weights = [3.0, 2.0, 1.0]  # First value has highest weight
            >>> aggregator.weighted_aggregate(values, weights)
            166.66666666666666
        """
        if len(values) != len(weights):
            raise ValueError("Values and weights must have same length")

        weight_sum = sum(weights)
        if weight_sum == 0:
            raise ValueError("Sum of weights cannot be zero")

        weighted_sum = sum(v * w for v, w in zip(values, weights, strict=True))
        return weighted_sum / weight_sum

    def filter_and_aggregate(
        self,
        values: Sequence[float],
        method: str | AggregationMethod = "median",
        *,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> float | None:
        """Filter values by range and aggregate.

        Args:
            values: Sequence of values.
            method: Aggregation method.
            min_value: Minimum valid value (inclusive).
            max_value: Maximum valid value (inclusive).

        Returns:
            Aggregated value or None if no values pass filter.

        Example:
            >>> aggregator = ActivityAggregator()
            >>> values = [10.0, 100.0, 200.0, 1000.0]
            >>> aggregator.filter_and_aggregate(values, min_value=50.0, max_value=500.0)
            150.0
        """
        filtered = self._filter_by_range(values, min_value, max_value)

        if not filtered:
            return None

        return self.aggregate_values(filtered, method)

    def _filter_by_range(
        self,
        values: Sequence[float],
        min_value: float | None,
        max_value: float | None,
    ) -> list[float]:
        """Filter values to those within the specified range."""
        return [
            v for v in values
            if self._is_in_range(v, min_value, max_value)
        ]

    def _is_in_range(
        self,
        value: float,
        min_value: float | None,
        max_value: float | None,
    ) -> bool:
        """Check if value is within the specified range (inclusive)."""
        if min_value is not None and value < min_value:
            return False
        return not (max_value is not None and value > max_value)
