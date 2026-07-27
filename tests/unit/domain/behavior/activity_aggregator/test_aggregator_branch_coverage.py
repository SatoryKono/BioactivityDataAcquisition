"""Branch coverage for ActivityAggregator (TD-R-02 / #6678)."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.activity_aggregator._aggregator import ActivityAggregator
from bioetl.domain.behavior.activity_aggregator._methods import AggregationMethod


def test_aggregate_values_methods_and_errors() -> None:
    agg = ActivityAggregator()
    values = [1.0, 2.0, 4.0]
    assert agg.aggregate_values(values, "mean") == pytest.approx(7.0 / 3.0)
    assert agg.aggregate_values(values, AggregationMethod.MEDIAN) == 2.0
    assert agg.aggregate_values(values, "min") == 1.0
    assert agg.aggregate_values(values, "max") == 4.0
    assert agg.aggregate_values([1.0, 4.0, 16.0], "geometric_mean") == pytest.approx(4.0)
    with pytest.raises(ValueError, match="empty"):
        agg.aggregate_values([])
    with pytest.raises(ValueError, match="Unknown aggregation method"):
        agg.aggregate_values(values, "nope")


def test_aggregate_with_uncertainty_branches() -> None:
    agg = ActivityAggregator()
    value, uncertainty = agg.aggregate_with_uncertainty([10.0], "mean")
    assert value == 10.0
    assert uncertainty == 0.0

    value, uncertainty = agg.aggregate_with_uncertainty([10.0, 20.0, 30.0], "mean")
    assert value == pytest.approx(20.0)
    assert uncertainty > 0.0

    value, uncertainty = agg.aggregate_with_uncertainty([10.0, 20.0, 30.0], "median")
    assert value == 20.0
    assert uncertainty >= 0.0

    value, uncertainty = agg.aggregate_with_uncertainty([1.0, 10.0, 100.0], "geometric_mean")
    assert value == pytest.approx(10.0)
    assert uncertainty >= 0.0

    with pytest.raises(ValueError, match="positive|empty|Geometric"):
        agg.aggregate_with_uncertainty([1.0, -1.0], "geometric_mean")

    with pytest.raises(ValueError, match="empty"):
        agg.aggregate_with_uncertainty([])
