"""List-based filters for Gold layer records.

Provides filtering by list length and list content.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GoldListContainsFilter",
    "GoldListLengthFilter",
]


@dataclass(frozen=True, slots=True)
class GoldListLengthFilter:
    """Filter by list length in a column.

    Attributes:
        column: Column name (must contain a list).
        min_length: Minimum length.
        max_length: Maximum length.
    """

    column: str
    min_length: int | None = None
    max_length: int | None = None

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if not self.column:
            raise ValueError("column name cannot be empty")
        if self.min_length is None and self.max_length is None:
            raise ValueError(
                f"At least one of min_length or max_length must be provided for column '{self.column}'"
            )


@dataclass(frozen=True, slots=True)
class GoldListContainsFilter:
    """Filter for list value containment (subset check).

    Attributes:
        column: Column name (list).
        values: Allowed values.
        mode: 'all' (all list elements must be in values) or 'any' (at least one).
    """

    column: str
    values: frozenset[str]
    mode: str = "all"  # "all" or "any"

    def __post_init__(self) -> None:
        if not self.column:
            raise ValueError("column name cannot be empty")
        if not self.values:
            raise ValueError(f"values for column '{self.column}' cannot be empty")
        if self.mode not in ("all", "any"):
            raise ValueError("mode must be 'all' or 'any'")
