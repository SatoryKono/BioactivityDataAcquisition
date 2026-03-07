"""Aggregation method enum and statistical helper functions.

Pure math utilities used by ActivityAggregator — no I/O, no domain I/O ports.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from enum import StrEnum


class AggregationMethod(StrEnum):
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
            raise ValueError(f"Geometric mean requires positive values, got {v}")

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


def _is_in_range(
    value: float,
    min_value: float | None,
    max_value: float | None,
) -> bool:
    """Check if value is within the specified range (inclusive)."""
    if min_value is not None and value < min_value:
        return False
    return not (max_value is not None and value > max_value)


def _filter_values_by_range(
    values: Sequence[float],
    min_value: float | None,
    max_value: float | None,
) -> list[float]:
    """Filter values to those within the specified range."""
    return [v for v in values if _is_in_range(v, min_value, max_value)]
