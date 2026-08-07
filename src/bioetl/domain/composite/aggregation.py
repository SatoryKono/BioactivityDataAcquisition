"""Aggregation configuration models for 1:M enrichers.

Defines configuration objects for aggregating multiple rows per join key
into a single row before joining with seed data in composite pipelines.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AggregationFunction(StrEnum):
    """Supported aggregation functions for 1:M enrichers.

    These functions are applied to convert multiple rows per join key
    into a single aggregated row before joining with the seed data.

    Attributes:
        COLLECT_LIST: Collect all values into a list.
        COLLECT_SET: Collect unique values into a list.
        COUNT: Count the number of values.
        FIRST: Take the first value.
        CONCAT_STR: Concatenate string values with separator.
    """

    COLLECT_LIST = "collect_list"
    COLLECT_SET = "collect_set"
    COUNT = "count"
    FIRST = "first"
    CONCAT_STR = "concat_str"

    @classmethod
    def from_string(cls, value: str) -> AggregationFunction:
        """Convert string to AggregationFunction enum.

        Args:
            value: String representation of aggregation function.

        Returns:
            Corresponding AggregationFunction enum value.

        Raises:
            ValueError: If the value is not a valid aggregation function.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = [e.value for e in cls]
            raise ValueError(
                f"Invalid aggregation function '{value}'. Valid options: {valid}"
            ) from None


class EnricherCardinality(StrEnum):
    """Cardinality of enricher data relative to seed.

    Describes the relationship between seed rows and enricher rows.

    Attributes:
        ONE_TO_ONE: Default. One enricher row per seed row.
        MANY_TO_ONE: Multiple enricher rows per seed row.
            Requires aggregation config to collapse to 1:1.
    """

    ONE_TO_ONE = "one_to_one"
    MANY_TO_ONE = "many_to_one"

    @classmethod
    def from_string(cls, value: str) -> EnricherCardinality:
        """Convert string to EnricherCardinality enum.

        Args:
            value: String representation of cardinality.

        Returns:
            Corresponding EnricherCardinality enum value.

        Raises:
            ValueError: If the value is not a valid cardinality.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = [e.value for e in cls]
            raise ValueError(
                f"Invalid cardinality '{value}'. Valid options: {valid}"
            ) from None


def _require_non_empty(value: str | tuple[object, ...], name: str) -> None:
    """Validate that a value is non-empty."""
    if not value:
        raise ValueError(f"{name} cannot be empty")


def _coerce_text_sequence(value: object, name: str) -> tuple[object, ...]:
    """Coerce supported config shapes into a tuple before text normalization."""
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple):
        return tuple(value)
    raise TypeError(f"{name} must be a string or sequence of strings")


def _validate_text_tuple(normalized: tuple[str, ...], name: str) -> None:
    """Validate normalized tuple values."""
    if any(not item for item in normalized):
        raise ValueError(f"{name} cannot contain empty values")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} cannot contain duplicate values")


def _coerce_text_tuple(value: object, name: str) -> tuple[str, ...]:
    """Coerce a string/list/tuple config value into a normalized text tuple."""
    if value is None:
        return ()
    normalized = tuple(str(item).strip() for item in _coerce_text_sequence(value, name))
    _validate_text_tuple(normalized, name)
    return normalized


@dataclass(frozen=True, slots=True)
class AggregationFieldSpec:
    """Specification for a single aggregated field.

    Defines how to aggregate a source column from a 1:M enricher
    into a single value per join key.

    Attributes:
        source_field: Source column name to aggregate (e.g., "term").
        agg_function: Aggregation function to apply.
        filter_condition: Optional SQL-like filter condition
            (e.g., "term_type == 'MESH_HEADING'").
        output_field: Output column name. Defaults to source_field if None.
    """

    source_field: str
    agg_function: AggregationFunction
    filter_condition: str | None = None
    output_field: str | None = None

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.agg_function, str):
            object.__setattr__(
                self,
                "agg_function",
                AggregationFunction.from_string(self.agg_function),
            )
        self._validate()

    def _validate(self) -> None:
        """Validate field specification."""
        _require_non_empty(self.source_field, "aggregation source_field")

    @property
    def effective_output_field(self) -> str:
        """Return the effective output field name, defaulting to source_field if not set."""
        return self.output_field or self.source_field


@dataclass(frozen=True, slots=True)
class AggregationConfig:
    """Configuration for 1:M enricher aggregation.

    Applied BEFORE join to convert 1:M relationships into 1:1.
    Groups enricher data by the join key and aggregates specified fields.

    Attributes:
        group_by: Join key to group by (e.g., "document_chembl_id").
        fields: Tuple of field specifications defining aggregations.
        order_by: Canonical row-order columns applied before aggregation.
    """

    group_by: str
    fields: tuple[AggregationFieldSpec, ...]
    order_by: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.fields, list | tuple):
            converted = tuple(
                AggregationFieldSpec(**f) if isinstance(f, dict) else f
                for f in self.fields
            )
            object.__setattr__(self, "fields", converted)
        object.__setattr__(
            self,
            "order_by",
            _coerce_text_tuple(self.order_by, "aggregation.order_by"),
        )
        self._validate()

    def _validate(self) -> None:
        """Validate aggregation configuration."""
        _require_non_empty(self.group_by, "aggregation group_by")
        if not self.fields:
            raise ValueError("aggregation.fields cannot be empty")


__all__ = [
    "AggregationConfig",
    "AggregationFieldSpec",
    "AggregationFunction",
    "EnricherCardinality",
]
