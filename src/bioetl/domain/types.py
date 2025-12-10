"""Unified type aliases for the domain layer.

This module provides canonical type aliases for API-specific types used
throughout the domain layer to ensure consistency.

Canonical Type Aliases
----------------------
- ``ApiPayload``: Raw API response payload (dict[str, Any]).
- ``FieldConfig``: Field configuration dictionary (dict[str, Any]).

Tabular Data Types (moved to domain.data)
-----------------------------------------
For tabular data abstractions, import from ``bioetl.domain.data``:

- ``RecordBatch``: Sequence of records (Sequence[Mapping[str, Any]])
- ``Record``: Single data record protocol
- ``RecordSet``: Collection of records with schema
- ``TabularData``: Full tabular data abstraction

Migration Guide
---------------
The following type aliases have been moved or deprecated:

+------------------+---------------+---------------------------------------------+
| Old Location     | New Location  | Notes                                       |
+==================+===============+=============================================+
| types.RawRecord  | (removed)     | Use Mapping[str, Any] or domain.data.Record |
+------------------+---------------+---------------------------------------------+
| types.RecordBatch| data.RecordBatch | More general type: Sequence[Mapping]     |
+------------------+---------------+---------------------------------------------+

Legacy deprecated aliases (will be removed in v3.0):

+------------------+---------------+---------------------------------------------+
| Legacy Name      | New Name      | Module                                      |
+==================+===============+=============================================+
| RawRecordDict    | (removed)     | Use Mapping[str, Any]                       |
+------------------+---------------+---------------------------------------------+
| RawRecordBatch   | RecordBatch   | bioetl.domain.data                          |
+------------------+---------------+---------------------------------------------+
| RawRecordList    | RecordBatch   | bioetl.domain.data                          |
+------------------+---------------+---------------------------------------------+
| RawPayload       | ApiPayload    | bioetl.domain.types                         |
+------------------+---------------+---------------------------------------------+

Example migration::

    # Before (deprecated)
    from bioetl.domain.types import RawRecord, RecordBatch

    def process(records: RecordBatch) -> RawRecord:
        ...

    # After (recommended)
    from bioetl.domain.data import RecordBatch
    from typing import Mapping, Any

    def process(records: RecordBatch) -> Mapping[str, Any]:
        ...

Usage Notes
-----------
Import API-specific types from this module::

    from bioetl.domain.types import ApiPayload, FieldConfig

Import tabular data types from domain.data::

    from bioetl.domain.data import RecordBatch, Record, TabularData
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    # Canonical type aliases (API-specific)
    "ApiPayload",
    "FieldConfig",
]

# =============================================================================
# Canonical Type Aliases (API-specific)
# =============================================================================

ApiPayload: TypeAlias = dict[str, Any]
"""Raw API response payload.

Represents the complete, unprocessed response from an external API,
including metadata, pagination info, and record data.

Example:
    >>> payload: ApiPayload = {
    ...     "page_meta": {"total_count": 100, "offset": 0},
    ...     "molecules": [{"id": "CHEMBL123"}],
    ... }
"""

FieldConfig: TypeAlias = dict[str, Any]
"""Field configuration dictionary.

Used for defining field-level settings such as normalization rules,
validation constraints, or transformation parameters.

Example:
    >>> config: FieldConfig = {
    ...     "name": "molecule_chembl_id",
    ...     "required": True,
    ...     "normalizer": "chembl_id",
    ... }
"""


# =============================================================================
# Deprecated Type Aliases (Backward Compatibility via __getattr__)
# =============================================================================

# Map of deprecated names to (new_location, deprecation_message)
_DEPRECATED_NAMES: dict[str, tuple[str, str]] = {
    "RawRecord": (
        "Mapping[str, Any]",
        "RawRecord is deprecated. Use Mapping[str, Any] directly or "
        "bioetl.domain.data.Record protocol for typed access.",
    ),
    "RecordBatch": (
        "bioetl.domain.data.RecordBatch",
        "RecordBatch has moved to bioetl.domain.data. "
        "Import from there: from bioetl.domain.data import RecordBatch",
    ),
    "RawRecordDict": (
        "Mapping[str, Any]",
        "RawRecordDict is deprecated. Use Mapping[str, Any] directly.",
    ),
    "RawRecordBatch": (
        "bioetl.domain.data.RecordBatch",
        "RawRecordBatch is deprecated. Use RecordBatch from bioetl.domain.data.",
    ),
    "RawRecordList": (
        "bioetl.domain.data.RecordBatch",
        "RawRecordList is deprecated. Use RecordBatch from bioetl.domain.data.",
    ),
    "RawPayload": (
        "ApiPayload",
        "RawPayload is deprecated. Use ApiPayload instead.",
    ),
}


def __getattr__(name: str) -> TypeAlias:
    """Emit deprecation warning for legacy type alias access.

    Provides backward compatibility for deprecated type aliases by returning
    appropriate types while emitting deprecation warnings.
    """
    if name in _DEPRECATED_NAMES:
        new_location, message = _DEPRECATED_NAMES[name]
        warnings.warn(
            f"{message} See migration guide in bioetl.domain.types module docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Return appropriate fallback types for backward compatibility
        if name in ("RawRecord", "RawRecordDict"):
            return dict[str, Any]
        elif name in ("RecordBatch", "RawRecordBatch", "RawRecordList"):
            # Import from data module for the actual type
            from bioetl.domain.data import RecordBatch as _RecordBatch

            return _RecordBatch
        elif name == "RawPayload":
            return ApiPayload

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
