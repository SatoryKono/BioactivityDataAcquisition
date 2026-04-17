"""Unit tests for ActivityAggregator service."""

from __future__ import annotations

import pytest

from bioetl.domain.services.activity_aggregator import (
    ActivityAggregator,
    AggregationMethod,
)
from bioetl.domain.value_objects import Concentration, ConcentrationUnit


class TestActivityAggregatorBasic:
    """Basic tests for ActivityAggregator."""

    @pytest.fixture
    def aggregator(self) -> ActivityAggregator:
        """Create an ActivityAggregator instance."""
        return ActivityAggregator()

    # ==========================================================================
    # aggregate_values() tests
    # ==========================================================================

    def test_aggregate_mean(self, aggregator: ActivityAggregator) -> None:
        """Test mean aggregation."""
        values = [100.0, 200.0, 300.0]
        result = aggregator.aggregate_values(values, "mean")
        assert result == pytest.approx(200.0)

    def test_aggregate_median(self, aggregator: ActivityAggregator) -> None:
        """Test median aggregation."""
        values = [100.0, 200.0, 300.0, 400.0]
        result = aggregator.aggregate_values(values, "median")
        assert result == pytest.approx(250.0)

    def test_aggregate_median_odd_count(self, aggregator: ActivityAggregator) -> None:
        """Test median with odd count of values."""
        values = [100.0, 200.0, 300.0]
        result = aggregator.aggregate_values(values, "median")
        assert result == pytest.approx(200.0)

    def test_aggregate_geometric_mean(self, aggregator: ActivityAggregator) -> None:
        """Test geometric mean aggregation."""
        values = [1.0, 10.0, 100.0]
        result = aggregator.aggregate_values(values, "geometric_mean")
        # Geometric mean of 1, 10, 100 = (1 * 10 * 100)^(1/3) = 10
        assert result == pytest.approx(10.0)

    def test_aggregate_min(self, aggregator: ActivityAggregator) -> None:
        """Test minimum aggregation."""
        values = [100.0, 50.0, 200.0]
        result = aggregator.aggregate_values(values, "min")
        assert result == pytest.approx(50.0)

    def test_aggregate_max(self, aggregator: ActivityAggregator) -> None:
        """Test maximum aggregation."""
        values = [100.0, 50.0, 200.0]
        result = aggregator.aggregate_values(values, "max")
        assert result == pytest.approx(200.0)

    def test_aggregate_with_enum(self, aggregator: ActivityAggregator) -> None:
        """Test aggregation with AggregationMethod enum."""
        values = [100.0, 200.0, 300.0]
        result = aggregator.aggregate_values(values, AggregationMethod.MEAN)
        assert result == pytest.approx(200.0)

    def test_aggregate_empty_raises(self, aggregator: ActivityAggregator) -> None:
        """Test that empty sequence raises ValueError."""
        with pytest.raises(ValueError, match="Cannot aggregate empty"):
            aggregator.aggregate_values([], "mean")

    def test_aggregate_unknown_method_raises(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test that unknown method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown aggregation method"):
            aggregator.aggregate_values([1.0, 2.0], "unknown_method")

    def test_aggregate_single_value(self, aggregator: ActivityAggregator) -> None:
        """Test aggregation of single value."""
        result = aggregator.aggregate_values([42.0], "mean")
        assert result == pytest.approx(42.0)


class TestActivityAggregatorUncertainty:
    """Tests for aggregation with uncertainty."""

    @pytest.fixture
    def aggregator(self) -> ActivityAggregator:
        return ActivityAggregator()

    def test_aggregate_with_uncertainty_mean(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test mean aggregation returns stddev as uncertainty."""
        values = [90.0, 100.0, 110.0]
        value, uncertainty = aggregator.aggregate_with_uncertainty(values, "mean")
        assert value == pytest.approx(100.0)
        # Standard deviation of [90, 100, 110] = 10
        assert uncertainty == pytest.approx(10.0)

    def test_aggregate_with_uncertainty_median(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test median aggregation returns MAD as uncertainty."""
        values = [90.0, 100.0, 100.0, 110.0]
        value, uncertainty = aggregator.aggregate_with_uncertainty(values, "median")
        # Median is 100
        assert value == pytest.approx(100.0)
        # MAD = median(|x - median|) = median([10, 0, 0, 10]) = 5
        assert uncertainty == pytest.approx(5.0)

    def test_aggregate_with_uncertainty_single_value(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test that single value has zero uncertainty."""
        value, uncertainty = aggregator.aggregate_with_uncertainty([100.0], "mean")
        assert value == pytest.approx(100.0)
        assert uncertainty == pytest.approx(0.0)


class TestActivityAggregatorConcentrations:
    """Tests for concentration aggregation."""

    @pytest.fixture
    def aggregator(self) -> ActivityAggregator:
        return ActivityAggregator()

    def test_aggregate_concentrations_same_unit(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test aggregation of concentrations with same unit."""
        concs = [
            Concentration(100.0, ConcentrationUnit.NANOMOLAR),
            Concentration(200.0, ConcentrationUnit.NANOMOLAR),
            Concentration(300.0, ConcentrationUnit.NANOMOLAR),
        ]
        result = aggregator.aggregate_concentrations(concs, "mean")
        assert result.value == pytest.approx(200.0)
        assert result.unit == ConcentrationUnit.NANOMOLAR

    def test_aggregate_concentrations_mixed_units(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test aggregation of concentrations with different units."""
        concs = [
            Concentration(100.0, ConcentrationUnit.NANOMOLAR),  # 100 nM
            Concentration(0.1, ConcentrationUnit.MICROMOLAR),  # 100 nM
            Concentration(0.2, ConcentrationUnit.MICROMOLAR),  # 200 nM
        ]
        result = aggregator.aggregate_concentrations(concs, "median")
        # Values in nM: [100, 100, 200], median = 100
        assert result.value == pytest.approx(100.0)
        assert result.unit == ConcentrationUnit.NANOMOLAR

    def test_aggregate_concentrations_empty_raises(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test that empty concentration list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot aggregate empty"):
            aggregator.aggregate_concentrations([], "mean")

    def test_aggregate_concentrations_with_uncertainty(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test concentration aggregation with uncertainty."""
        concs = [
            Concentration(90.0, ConcentrationUnit.NANOMOLAR),
            Concentration(100.0, ConcentrationUnit.NANOMOLAR),
            Concentration(110.0, ConcentrationUnit.NANOMOLAR),
        ]
        result, uncertainty = aggregator.aggregate_concentrations_with_uncertainty(
            concs, "mean"
        )
        assert result.value == pytest.approx(100.0)
        assert result.unit == ConcentrationUnit.NANOMOLAR
        assert uncertainty == pytest.approx(10.0)


class TestActivityAggregatorWeighted:
    """Tests for weighted aggregation."""

    @pytest.fixture
    def aggregator(self) -> ActivityAggregator:
        return ActivityAggregator()

    def test_weighted_aggregate_equal_weights(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test weighted average with equal weights equals mean."""
        values = [100.0, 200.0, 300.0]
        weights = [1.0, 1.0, 1.0]
        result = aggregator.weighted_aggregate(values, weights)
        assert result == pytest.approx(200.0)

    def test_weighted_aggregate_unequal_weights(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test weighted average with unequal weights."""
        values = [100.0, 200.0, 300.0]
        weights = [3.0, 2.0, 1.0]  # Higher weight on lower values
        result = aggregator.weighted_aggregate(values, weights)
        assert result == pytest.approx(166.67, rel=0.01)

    def test_weighted_aggregate_length_mismatch_raises(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test that mismatched lengths raise ValueError."""
        with pytest.raises(ValueError, match="must have same length"):
            aggregator.weighted_aggregate([1.0, 2.0], [1.0])

    def test_weighted_aggregate_zero_weights_raises(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test that zero total weight raises ValueError."""
        with pytest.raises(ValueError, match="cannot be zero"):
            aggregator.weighted_aggregate([1.0, 2.0], [0.0, 0.0])


class TestActivityAggregatorFilterAndAggregate:
    """Tests for filter and aggregate."""

    @pytest.fixture
    def aggregator(self) -> ActivityAggregator:
        return ActivityAggregator()

    def test_filter_and_aggregate_with_min(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test filtering with minimum value."""
        values = [10.0, 100.0, 200.0, 1000.0]
        result = aggregator.filter_and_aggregate(values, "median", min_value=50.0)
        # Values >= 50: [100, 200, 1000], median = 200
        assert result == pytest.approx(200.0)

    def test_filter_and_aggregate_with_max(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test filtering with maximum value."""
        values = [10.0, 100.0, 200.0, 1000.0]
        result = aggregator.filter_and_aggregate(values, "median", max_value=500.0)
        # Values <= 500: [10, 100, 200], median = 100
        assert result == pytest.approx(100.0)

    def test_filter_and_aggregate_with_range(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test filtering with both min and max."""
        values = [10.0, 100.0, 200.0, 1000.0]
        result = aggregator.filter_and_aggregate(
            values, "mean", min_value=50.0, max_value=500.0
        )
        # Values in [50, 500]: [100, 200], mean = 150
        assert result == pytest.approx(150.0)

    def test_filter_and_aggregate_all_filtered(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test that filtering all values returns None."""
        values = [10.0, 20.0, 30.0]
        result = aggregator.filter_and_aggregate(values, "mean", min_value=100.0)
        assert result is None

    def test_filter_and_aggregate_no_filter(
        self, aggregator: ActivityAggregator
    ) -> None:
        """Test without filter parameters."""
        values = [100.0, 200.0, 300.0]
        result = aggregator.filter_and_aggregate(values, "mean")
        assert result == pytest.approx(200.0)


class TestAggregationMethodEnum:
    """Tests for AggregationMethod enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected values."""
        assert AggregationMethod.MEAN.value == "mean"
        assert AggregationMethod.MEDIAN.value == "median"
        assert AggregationMethod.GEOMETRIC_MEAN.value == "geometric_mean"
        assert AggregationMethod.MINIMUM.value == "min"
        assert AggregationMethod.MAXIMUM.value == "max"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert AggregationMethod("mean") == AggregationMethod.MEAN
        assert AggregationMethod("median") == AggregationMethod.MEDIAN
