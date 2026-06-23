"""Extension mixin for ActivityAggregator utility operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.value_objects import Concentration, ConcentrationUnit

from ._methods import AggregationMethod, _filter_values_by_range

if TYPE_CHECKING:

    class _AggregatorHost(Protocol):
        def aggregate_values(
            self, values: Sequence[float], method: str | AggregationMethod = "median"
        ) -> float: ...

        def aggregate_with_uncertainty(
            self, values: Sequence[float], method: str | AggregationMethod = "median"
        ) -> tuple[float, float]: ...


class _ActivityAggregatorExtensions:
    """Concentration and weighted/filter helper methods."""

    def aggregate_concentrations(
        self,
        concentrations: Sequence[Concentration],
        method: str | AggregationMethod = "median",
    ) -> Concentration:
        """Aggregate multiple concentration measurements.

        Args:
            concentrations: Sequence of Concentration values to aggregate;
                must be non-empty.
            method: Aggregation method (e.g., 'median', 'mean'); defaults to 'median'.

        Returns:
            Aggregated Concentration in nanomolar units.

        Raises:
            ValueError: If concentrations is empty.
        """
        if not concentrations:
            raise ValueError("Cannot aggregate empty sequence of concentrations")
        nm_values = [c.to_nanomolar().value for c in concentrations]
        host = cast("_AggregatorHost", self)
        aggregated = host.aggregate_values(nm_values, method)
        return Concentration(value=aggregated, unit=ConcentrationUnit.NANOMOLAR)

    def aggregate_concentrations_with_uncertainty(
        self,
        concentrations: Sequence[Concentration],
        method: str | AggregationMethod = "median",
    ) -> tuple[Concentration, float]:
        """Aggregate concentrations with uncertainty estimate.

        Args:
            concentrations: Sequence of Concentration values to aggregate;
                must be non-empty.
            method: Aggregation method (e.g., 'median', 'mean'); defaults to 'median'.
        """
        if not concentrations:
            raise ValueError("Cannot aggregate empty sequence of concentrations")
        nm_values = [c.to_nanomolar().value for c in concentrations]
        host = cast("_AggregatorHost", self)
        aggregated, uncertainty = host.aggregate_with_uncertainty(nm_values, method)
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
            values: Sequence of numeric values to weight and average.
            weights: Sequence of weights corresponding to each value;
                must be the same length as values and sum to a non-zero total.
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
            values: Sequence of numeric values to filter and aggregate.
            method: Aggregation method (e.g., 'median', 'mean'); defaults to 'median'.
            min_value: Optional lower bound; values below this are excluded; defaults to None.
            max_value: Optional upper bound; values above this are excluded; defaults to None.
        """
        filtered = _filter_values_by_range(values, min_value, max_value)
        if not filtered:
            return None
        host = cast("_AggregatorHost", self)
        return host.aggregate_values(filtered, method)
