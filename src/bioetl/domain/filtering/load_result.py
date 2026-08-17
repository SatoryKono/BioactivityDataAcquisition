"""Filter load result.

Provides the result container for loading filter IDs with deduplication metadata.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

__all__ = [
    "FilterLoadResult",
]


@dataclass(frozen=True)
class FilterLoadResult:
    """Filter ID load result with deduplication metadata.

    Supports both single-column and multi-column filtering modes:
    - Single-column: Use ids, total_count, unique_count, duplicate_count, duplicates
    - Multi-column: Use column_ids for per-field unique IDs, valid_combinations for
      exact row-wise combinations to filter

    Attributes:
        ids: Unique sorted IDs (single-column mode).
        total_count: Total records in the source (before deduplication).
        unique_count: Number of unique IDs (single-column mode).
        duplicate_count: Number of removed duplicates.
        duplicates: IDs that appeared more than once.
        column_ids: Per-field unique IDs for multi-column mode.
            Mapping from filter_field to tuple of unique IDs.
        valid_combinations: Exact row-wise combinations to match (multi-column mode).
            Each tuple contains values in the same order as columns were defined.
        filter_fields: Ordered tuple of filter field names for valid_combinations.
    """

    ids: tuple[str, ...] = ()
    total_count: int = 0
    unique_count: int = 0
    duplicate_count: int = 0
    duplicates: frozenset[str] = field(default_factory=frozenset)
    column_ids: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    valid_combinations: frozenset[tuple[str, ...]] = field(default_factory=frozenset)
    filter_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate result consistency."""
        if self.column_ids:
            _validate_multi_column_result(
                column_ids=self.column_ids,
                valid_combinations=self.valid_combinations,
                filter_fields=self.filter_fields,
            )
            return
        _validate_single_column_result(self)

    def _validate_multi_column(self) -> None:
        """Fail closed when multi-column combinations do not match declared fields."""
        fields = self.filter_fields or tuple(self.column_ids.keys())
        if self.filter_fields and tuple(self.filter_fields) != tuple(
            self.column_ids.keys()
        ):
            raise ValueError(
                "filter_fields must match column_ids keys in order: "
                f"expected {tuple(self.column_ids.keys())}, got {self.filter_fields}"
            )
        arity = len(fields)
        for combination in self.valid_combinations:
            if len(combination) != arity:
                raise ValueError(
                    "valid_combinations entries must have length "
                    f"{arity}, got {len(combination)}"
                )
            for field_name, value in zip(fields, combination, strict=True):
                allowed = self.column_ids.get(field_name, ())
                if value not in allowed:
                    raise ValueError(
                        f"combination value {value!r} is not in column_ids[{field_name!r}]"
                    )

    @property
    def has_duplicates(self) -> bool:
        """Check whether any duplicates were found."""
        return self.duplicate_count > 0

    @property
    def is_multi_column(self) -> bool:
        """Check if this is a multi-column filter result."""
        return bool(self.column_ids) and len(self.column_ids) > 1


def _validate_single_column_result(result: FilterLoadResult) -> None:
    """Validate counts for a single-column filter result."""
    if result.unique_count != len(result.ids):
        raise ValueError(
            f"unique_count ({result.unique_count}) must match "
            f"len(ids) ({len(result.ids)})"
        )
    if result.duplicate_count != result.total_count - result.unique_count:
        raise ValueError(
            f"duplicate_count ({result.duplicate_count}) must equal "
            f"total_count - unique_count ({result.total_count - result.unique_count})"
        )


def _validate_multi_column_result(
    *,
    column_ids: Mapping[str, tuple[str, ...]],
    valid_combinations: frozenset[tuple[str, ...]],
    filter_fields: tuple[str, ...],
) -> None:
    """Validate ordered fields and exact combinations for column-mode results."""
    if tuple(column_ids) != filter_fields:
        raise ValueError("filter_fields must match column_ids keys in order")
    allowed_values = tuple(column_ids[field] for field in filter_fields)
    for combination in valid_combinations:
        _validate_multi_column_combination(combination, allowed_values)


def _validate_multi_column_combination(
    combination: tuple[str, ...],
    allowed_values: tuple[tuple[str, ...], ...],
) -> None:
    """Validate one row-wise multi-column value combination."""
    if len(combination) != len(allowed_values):
        raise ValueError("valid_combinations entries must match filter_fields arity")
    if any(
        value not in allowed
        for value, allowed in zip(combination, allowed_values, strict=True)
    ):
        raise ValueError("valid_combinations values must belong to column_ids")
