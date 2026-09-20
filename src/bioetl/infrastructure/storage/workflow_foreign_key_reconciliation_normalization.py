"""Foreign-key value normalization for workflow reconciliation.

Pure row-key helpers extracted from
``workflow_foreign_key_reconciliation_support`` to keep the infrastructure
storage surface under the file-size budget. Internal implementation detail
owned by the canonical ``workflow_foreign_key_reconciliation`` adapter
module (AUD-005).
"""

from __future__ import annotations

from math import isnan

__all__ = [
    "NULL_TOKEN",
    "normalize_row_key",
    "normalize_value",
    "row_has_null_foreign_key",
]


NULL_TOKEN = object()


def row_has_null_foreign_key(
    row: dict[str, object],
    keys: tuple[str, ...],
) -> bool:
    """Return True when any foreign-key component is null, blank, or NaN."""
    return any(normalize_value(row.get(key)) is None for key in keys)


def normalize_row_key(
    row: dict[str, object],
    keys: tuple[str, ...],
    *,
    nulls_equal: bool,
) -> tuple[object, ...] | None:
    """Normalize a row key for foreign-key comparison."""
    normalized: list[object] = []
    for key in keys:
        value = row.get(key)
        normalized_value = normalize_value(value)
        if normalized_value is None:
            if nulls_equal:
                normalized.append(NULL_TOKEN)
                continue
            return None
        normalized.append(normalized_value)
    return tuple(normalized)


def normalize_value(value: object) -> object | None:
    """Normalize one foreign-key value for comparison.

    Invariants:
    - ``None``, blank strings, and NaN are null (``None``).
    - Strings stay distinct from numeric values (``"5"`` != ``5``).
    - Integral numbers that differ only by float form match (``5`` == ``5.0``).
    - Booleans are not collapsed into integers.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, float):
        if isnan(value):
            return None
        if value.is_integer():
            return ("int", int(value))
        return ("float", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return ("str", stripped)
    rendered = str(value).strip()
    if not rendered:
        return None
    return ("other", type(value).__name__, rendered)
