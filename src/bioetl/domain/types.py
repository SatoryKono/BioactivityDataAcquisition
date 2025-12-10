"""Unified type aliases for the domain layer.

This module provides canonical type aliases used throughout the domain layer
to ensure consistency and reduce duplication across ports and contracts.

Canonical Type Aliases
----------------------
- ``RawRecord``: A single record as an untyped dictionary (dict[str, Any]).
- ``RecordBatch``: A batch/list of raw records (list[RawRecord]).
- ``ApiPayload``: Raw API response payload (dict[str, Any]).
- ``FieldConfig``: Field configuration dictionary (dict[str, Any]).

Migration Guide
---------------
The following legacy type aliases are deprecated and will be removed in v3.0:

+------------------+---------------+---------------------------------------------+
| Legacy Name      | New Name      | Module                                      |
+==================+===============+=============================================+
| RawRecordDict    | RawRecord     | domain.ports.extraction, domain.ports.parsing|
+------------------+---------------+---------------------------------------------+
| RawRecordBatch   | RecordBatch   | domain.ports.extraction                     |
+------------------+---------------+---------------------------------------------+
| RawRecordList    | RecordBatch   | domain.ports.parsing                        |
+------------------+---------------+---------------------------------------------+
| RawPayload       | ApiPayload    | domain.ports.parsing                        |
+------------------+---------------+---------------------------------------------+

Example migration::

    # Before (deprecated)
    from bioetl.domain.ports.extraction import RawRecordDict, RawRecordBatch

    def process(records: RawRecordBatch) -> RawRecordDict:
        ...

    # After (recommended)
    from bioetl.domain.types import RawRecord, RecordBatch

    def process(records: RecordBatch) -> RawRecord:
        ...

Usage Notes
-----------
Import from this module for new code::

    from bioetl.domain.types import RawRecord, RecordBatch, ApiPayload, FieldConfig

For backward compatibility, legacy aliases are re-exported from their original
modules with deprecation warnings.
"""

from __future__ import annotations

import warnings
from typing import Any, TypeAlias

__all__ = [
    # Canonical type aliases
    "RawRecord",
    "RecordBatch",
    "ApiPayload",
    "FieldConfig",
    # Deprecated aliases (for backward compatibility)
    "RawRecordDict",
    "RawRecordBatch",
    "RawRecordList",
    "RawPayload",
]

# =============================================================================
# Canonical Type Aliases
# =============================================================================

RawRecord: TypeAlias = dict[str, Any]
"""A single record as an untyped dictionary.

Represents a single data record from an external source (API response,
database row, etc.) before domain model mapping.

Example:
    >>> record: RawRecord = {"id": "CHEMBL123", "name": "Aspirin"}
"""

RecordBatch: TypeAlias = list[RawRecord]
"""A batch/list of raw records.

Represents multiple records fetched together, typically from a paginated
API response or batch extraction.

Example:
    >>> batch: RecordBatch = [
    ...     {"id": "CHEMBL123", "name": "Aspirin"},
    ...     {"id": "CHEMBL456", "name": "Ibuprofen"},
    ... ]
"""

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
# Deprecated Aliases (Backward Compatibility)
# =============================================================================


def _deprecated_alias(
    old_name: str, new_name: str, value: TypeAlias
) -> TypeAlias:
    """Helper to create deprecated alias with runtime warning on access.

    Note: TypeAlias assignments are resolved at import time, so we can't
    intercept access. The deprecation warning is emitted via module __getattr__
    for dynamic imports, and via explicit re-exports in ports modules.
    """
    return value


# These are direct assignments for static type checkers.
# Deprecation warnings are emitted via __getattr__ in ports modules.
RawRecordDict: TypeAlias = RawRecord
"""Deprecated: Use ``RawRecord`` instead."""

RawRecordBatch: TypeAlias = RecordBatch
"""Deprecated: Use ``RecordBatch`` instead."""

RawRecordList: TypeAlias = RecordBatch
"""Deprecated: Use ``RecordBatch`` instead."""

RawPayload: TypeAlias = ApiPayload
"""Deprecated: Use ``ApiPayload`` instead."""


# =============================================================================
# Module-level __getattr__ for deprecation warnings
# =============================================================================

_DEPRECATED_NAMES: dict[str, tuple[str, TypeAlias]] = {
    "RawRecordDict": ("RawRecord", RawRecord),
    "RawRecordBatch": ("RecordBatch", RecordBatch),
    "RawRecordList": ("RecordBatch", RecordBatch),
    "RawPayload": ("ApiPayload", ApiPayload),
}


def __getattr__(name: str) -> TypeAlias:
    """Emit deprecation warning for legacy type alias access.

    This is triggered for dynamic imports like:
        getattr(types_module, "RawRecordDict")

    Static imports (from bioetl.domain.types import RawRecordDict) use
    the module-level assignments above, so deprecation warnings for those
    are emitted from the ports modules where they're re-exported.
    """
    if name in _DEPRECATED_NAMES:
        new_name, value = _DEPRECATED_NAMES[name]
        warnings.warn(
            f"{name} is deprecated, use {new_name} from bioetl.domain.types instead. "
            "See migration guide in bioetl.domain.types module docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
