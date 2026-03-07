"""Extension mixin for ActivityAggregator utility operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.value_objects.activity_values import Concentration, ConcentrationUnit

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
        """Aggregate multiple concentration measurements."""
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
        """Aggregate concentrations with uncertainty estimate."""
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
        """Calculate weighted average of values."""
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
        """Filter values by range and aggregate."""
        filtered = _filter_values_by_range(values, min_value, max_value)
        if not filtered:
            return None
        host = cast("_AggregatorHost", self)
        return host.aggregate_values(filtered, method)
