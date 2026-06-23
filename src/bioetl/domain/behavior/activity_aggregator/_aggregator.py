"""ActivityAggregator service implementation.

Handles aggregation of multiple activity measurements into
representative values with uncertainty estimates.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._aggregator_extensions import _ActivityAggregatorExtensions
from ._methods import (
    AggregationMethod,
    _geometric_mean,
    _median_absolute_deviation,
)

if TYPE_CHECKING:
    from bioetl.domain.behavior.normalization_config import NormalizationConfig


@dataclass(slots=True)
class ActivityAggregator(_ActivityAggregatorExtensions):
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
        >>> result
        102.5

        >>> value, uncertainty = aggregator.aggregate_with_uncertainty(values)
        >>> f"{value:.1f} +/- {uncertainty:.1f}"
        '102.5 +/- 5.0'
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
            >>> f"{value:.1f} +/- {uncertainty:.1f}"
            '102.5 +/- 6.5'
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
