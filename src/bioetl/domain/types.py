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

+------------------+------------------+---------------------------------------------+
| Old Location     | New Location     | Notes                                       |
+==================+==================+=============================================+
| types.RecordBatch| data.RecordBatch | More general type: Sequence[Mapping]        |
+------------------+------------------+---------------------------------------------+

Removed types (no longer available):

+------------------+-------------------------------------------------------------+
| Removed Name     | Replacement                                                 |
+==================+=============================================================+
| RawRecord        | Use ``Mapping[str, Any]`` or ``domain.data.Record`` protocol|
+------------------+-------------------------------------------------------------+

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

from typing import TYPE_CHECKING, Any, TypeAlias

from bioetl.domain._deprecations import (
    emit_deprecation_warning,
    resolve_deprecated_type,
    get_deprecated_names_for_module,
)

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

# Deprecated names are now managed centrally in bioetl.domain._deprecations.
# This module handles: RecordBatch, RawRecordDict, RawRecordBatch, RawRecordList, RawPayload
# NOTE: RawRecord has been removed completely. Do not add it here.
# Use Mapping[str, Any] or bioetl.domain.data.Record protocol instead.

_DEPRECATED_NAMES = get_deprecated_names_for_module(__name__)


def __getattr__(name: str) -> TypeAlias:
    """Emit deprecation warning for legacy type alias access.

    Provides backward compatibility for deprecated type aliases by returning
    appropriate types while emitting deprecation warnings.

    Uses centralized deprecation registry from bioetl.domain._deprecations.
    """
    if name in _DEPRECATED_NAMES:
        emit_deprecation_warning(name, stacklevel=2)
        return resolve_deprecated_type(name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
