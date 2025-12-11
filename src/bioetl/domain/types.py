"""Unified type aliases for the domain layer.

This module provides canonical type aliases for API-specific types used
throughout the domain layer to ensure consistency.

Canonical Type Aliases
----------------------
- ``ApiPayload``: Raw API response payload (dict[str, Any]).
- ``FieldConfig``: Field configuration dictionary (dict[str, Any]).

Tabular Data Types
------------------
For tabular data abstractions, import from ``bioetl.domain.data``:

- ``RecordBatch``: Sequence of records (Sequence[Mapping[str, Any]])
- ``Record``: Single data record protocol
- ``RecordSet``: Collection of records with schema
- ``TabularData``: Full tabular data abstraction

Usage Notes
-----------
Import API-specific types from this module::

    from bioetl.domain.types import ApiPayload, FieldConfig

Import tabular data types from domain.data::

    from bioetl.domain.data import RecordBatch, Record, TabularData
"""

from __future__ import annotations

from typing import Any, TypeAlias

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
