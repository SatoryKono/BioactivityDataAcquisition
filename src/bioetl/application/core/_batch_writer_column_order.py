"""Column prefix/suffix ordering for batch writer projections."""

from __future__ import annotations


def apply_system_prefix_order(columns: list[str]) -> list[str]:
    """Ensure system fields are first and DQ fields are last."""
    from bioetl.domain.schemas.column_order import (
        DQ_FIELDS_SUFFIX,
        LOOKUP_FIELDS_PREFIX,
        SYSTEM_FIELDS_PREFIX,
    )

    if not columns:
        return columns
    column_set = set(columns)
    prefix = [item for item in SYSTEM_FIELDS_PREFIX if item in column_set]
    lookup = [item for item in LOOKUP_FIELDS_PREFIX if item in column_set]
    suffix = [item for item in DQ_FIELDS_SUFFIX if item in column_set]
    assigned = {*prefix, *lookup, *suffix}
    middle = [item for item in columns if item not in assigned]
    return prefix + lookup + middle + suffix
