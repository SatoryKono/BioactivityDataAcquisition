"""Core record source interfaces and helpers.

This module defines the abstract interface for record sources (RecordSourceABC)
and the SourceRecordModel Pydantic model for API response parsing.

Terminology & Migration Guide
-----------------------------
+------------------+-------------------+---------------------------------------------+
| Old Name         | New Name          | Notes                                       |
+==================+===================+=============================================+
| SourceRecord     | SourceRecordModel | Pydantic model for API boundary parsing.    |
|                  |                   | SourceRecord kept as deprecated alias.      |
+------------------+-------------------+---------------------------------------------+
| RawRecord        | (removed)         | Was deprecated alias for SourceRecord.      |
|                  |                   | Use Mapping[str, Any] or domain.data.Record |
+------------------+-------------------+---------------------------------------------+

SourceRecordModel Usage
-----------------------
``SourceRecordModel`` is a Pydantic model intended for use ONLY at system
boundaries (parsing API responses). It provides validation and serialization.

For internal domain contracts, use the pandas-free abstractions:
    - ``Mapping[str, Any]`` for single records
    - ``Sequence[Mapping[str, Any]]`` for batches (RecordBatch from domain.data)
    - ``Record`` protocol from domain.data for typed access

Example migration::

    # Before (deprecated)
    from bioetl.domain.record_source import SourceRecord, RawRecord

    def parse_response(data: dict) -> list[SourceRecord]:
        return [SourceRecord.model_validate(r) for r in data["items"]]

    # After (recommended) - for API boundary
    from bioetl.domain.record_source import SourceRecordModel

    def parse_response(data: dict) -> list[SourceRecordModel]:
        return [SourceRecordModel.model_validate(r) for r in data["items"]]

    # After (recommended) - for domain contracts
    from collections.abc import Mapping, Sequence
    from typing import Any

    def process_records(records: Sequence[Mapping[str, Any]]) -> None:
        for record in records:
            # Process using Mapping interface
            ...

See also:
    - bioetl.domain.data: Record, RecordBatch, TabularData protocols
    - bioetl.application.sources.ApiRecordSource: API-based record source
    - bioetl.application.files: File-based record sources
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from bioetl.domain._deprecations import (
    emit_deprecation_warning,
    resolve_deprecated_type,
    get_deprecated_names_for_module,
)


class SourceRecordModel(BaseModel):
    """Pydantic model for records extracted from external data sources.

    This model is intended for use at system boundaries (parsing API responses,
    validating external data). It uses ``extra="allow"`` to accept any fields.

    For internal domain contracts, prefer using ``Mapping[str, Any]`` or the
    ``Record`` protocol from ``bioetl.domain.data``.

    Example:
        >>> # At API boundary - validation and parsing
        >>> record = SourceRecordModel.model_validate({"id": "123", "name": "Test"})
        >>> record.model_dump()
        {'id': '123', 'name': 'Test'}

        >>> # For domain contracts, use generic types
        >>> from collections.abc import Mapping
        >>> def process(record: Mapping[str, Any]) -> str:
        ...     return record["id"]

    Attributes:
        Any fields are accepted due to ``extra="allow"`` configuration.

    Note:
        Previously named ``SourceRecord``. The old name is available as a
        deprecated alias for backward compatibility.
    """

    model_config = ConfigDict(extra="allow")


# =============================================================================
# Deprecated Aliases (backward compatibility)
# =============================================================================

# Deprecated alias - use SourceRecordModel instead
SourceRecord = SourceRecordModel
"""Deprecated alias for SourceRecordModel.

.. deprecated:: 2.1
    Use ``SourceRecordModel`` instead. ``SourceRecord`` will be removed in v3.0.
"""


# Get deprecated names for this module from central registry
_DEPRECATED_NAMES = get_deprecated_names_for_module(__name__)


def __getattr__(name: str) -> Any:
    """Module-level __getattr__ for deprecation warnings.

    Uses centralized deprecation registry from bioetl.domain._deprecations.
    """
    if name in _DEPRECATED_NAMES:
        emit_deprecation_warning(name, stacklevel=2)
        return resolve_deprecated_type(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Type alias for backward compatibility in TYPE_CHECKING
if TYPE_CHECKING:
    # Allow static type checkers to see deprecated aliases
    pass  # SourceRecord already defined above


# =============================================================================
# Record Source Abstract Base Classes
# =============================================================================


class RecordSourceABC(ABC):
    """Abstract base class for record sources returning record batches.

    Record sources provide iteration over batches of records from various
    data sources (API, files, databases, etc.).

    The ``iter_records`` method returns generic ``Sequence[Mapping[str, Any]]``
    batches, allowing implementations to return any mapping-like objects
    without coupling to specific Pydantic models.

    Example:
        >>> class MyRecordSource(RecordSourceABC):
        ...     def iter_records(self) -> Iterable[Sequence[Mapping[str, Any]]]:
        ...         yield [{"id": "1", "name": "first"}, {"id": "2", "name": "second"}]

    Note:
        Implementations may internally use SourceRecordModel for validation,
        but the interface returns generic Mapping types for flexibility.
    """

    @abstractmethod
    def iter_records(self) -> Iterable[Sequence[Mapping[str, Any]]]:
        """Yield batches of records from the source.

        Returns:
            Iterable of record batches. Each batch is a Sequence of Mappings.
            Empty batches may be yielded; consumers should handle them.

        Yields:
            Sequence[Mapping[str, Any]]: A batch of records where each record
            is a mapping of field names to values.
        """


class InMemoryRecordSource(RecordSourceABC):
    """Simple record source backed by an in-memory list.

    Useful for testing and for wrapping pre-loaded data.

    Args:
        records: List of records (SourceRecordModel or Mapping[str, Any]).
        chunk_size: Optional size for chunking. If None or <= 0, yields all at once.

    Example:
        >>> records = [{"id": "1"}, {"id": "2"}]
        >>> source = InMemoryRecordSource(records)
        >>> list(source.iter_records())
        [[{'id': '1'}, {'id': '2'}]]

        >>> # With chunking
        >>> source = InMemoryRecordSource(records, chunk_size=1)
        >>> list(source.iter_records())
        [[{'id': '1'}], [{'id': '2'}]]
    """

    def __init__(
        self,
        records: list[SourceRecordModel] | list[Mapping[str, Any]],
        chunk_size: int | None = None,
    ):
        # Normalize to list of mappings
        self._records: list[Mapping[str, Any]] = [
            r.model_dump() if isinstance(r, BaseModel) else dict(r) for r in records
        ]
        self._chunk_size = chunk_size

    def iter_records(self) -> Iterable[Sequence[Mapping[str, Any]]]:
        """Yield in-memory records in configured chunk sizes."""
        if self._chunk_size is None or self._chunk_size <= 0:
            yield self._records[:]
            return

        for start in range(0, len(self._records), self._chunk_size):
            yield self._records[start : start + self._chunk_size]


# Deprecated type alias for backward compatibility
RecordSource = RecordSourceABC
"""Deprecated alias for RecordSourceABC.

.. deprecated:: 2.0
    Use ``RecordSourceABC`` directly. Will be removed in v3.0.
"""

__all__ = [
    # Canonical exports
    "SourceRecordModel",
    "RecordSourceABC",
    "InMemoryRecordSource",
    # Deprecated aliases (for backward compatibility)
    "SourceRecord",
    "RecordSource",
]
