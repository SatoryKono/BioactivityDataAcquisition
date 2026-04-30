"""Filter strategy helpers for organism classification service."""

from __future__ import annotations

from bioetl.domain.behavior.organism_classification_service_models import (
    CellularityFilterStrategy,
)
from bioetl.domain.types import CellularityType

__all__ = ["build_filter_strategy"]


def _include_strategy(
    include: set[CellularityType],
    keep_unresolved: bool,
) -> CellularityFilterStrategy:
    """Return include-only filter strategy."""

    def strategy(cellularity: CellularityType | None) -> bool:
        if cellularity is None:
            return keep_unresolved
        return cellularity in include

    return strategy


def _exclude_strategy(
    exclude: set[CellularityType],
    keep_unresolved: bool,
) -> CellularityFilterStrategy:
    """Return exclusion filter strategy."""

    def strategy(cellularity: CellularityType | None) -> bool:
        if cellularity is None:
            return keep_unresolved
        return cellularity not in exclude

    return strategy


def _pass_all_strategy(keep_unresolved: bool) -> CellularityFilterStrategy:
    """Return strategy when neither include nor exclude is provided."""

    def strategy(cellularity: CellularityType | None) -> bool:
        if cellularity is None:
            return keep_unresolved
        return True

    return strategy


def build_filter_strategy(
    *,
    include: set[CellularityType] | None,
    exclude: set[CellularityType] | None,
    keep_unresolved: bool,
) -> CellularityFilterStrategy:
    """Build filter strategy for include/exclude/unresolved policy.

    Precedence: include > exclude > pass-all.

    Args:
        include: If provided, only records with cellularity in this set are kept.
        exclude: If provided, records with cellularity in this set are removed.
        keep_unresolved: Whether records with unknown cellularity are retained.

    Returns:
        Callable CellularityFilterStrategy that accepts a CellularityType or None
        and returns True if the record should be kept.
    """
    if include is not None:
        return _include_strategy(include, keep_unresolved)
    if exclude is not None:
        return _exclude_strategy(exclude, keep_unresolved)
    return _pass_all_strategy(keep_unresolved)
