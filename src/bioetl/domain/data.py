"""Domain abstractions for tabular data.

This module provides Protocol-based abstractions for working with tabular data
in the domain layer, decoupling domain logic from pandas implementation details.

The abstractions are designed to be minimal yet sufficient for domain operations:
- Record: Single data record (row)
- RecordSet: Collection of records with schema information
- TabularData: Full tabular data abstraction with iteration and shape

Infrastructure layer provides concrete implementations (e.g., PandasAdapter).

Example usage in domain contracts::

    from bioetl.domain.data import TabularData, Record

    class ValidatorABC(ABC):
        @abstractmethod
        def validate(self, data: TabularData) -> ValidationResult:
            '''Validates tabular data and returns result.'''

Migration Guide
---------------
Replace pd.DataFrame with TabularData in domain contracts:

+-----------------------+------------------+
| Before (pandas)       | After (domain)   |
+=======================+==================+
| df: pd.DataFrame      | data: TabularData|
+-----------------------+------------------+
| row: pd.Series        | row: Record      |
+-----------------------+------------------+

Infrastructure adapters implement these protocols wrapping pandas objects.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Iterator, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass

# Type alias for a batch of records (pandas-free)
RecordBatch = Sequence[Mapping[str, Any]]
"""Type alias for a sequence of records.

RecordBatch represents a collection of records without pandas dependency.
Each record is a Mapping (dict-like) of field names to values.

This is the CANONICAL definition for batch/collection of records in the domain layer.
Use this type alias instead of the deprecated ``list[RawRecord]`` from ``domain.types``.

Example:
    >>> batch: RecordBatch = [
    ...     {"id": "CHEMBL123", "name": "Aspirin", "mw": 180.16},
    ...     {"id": "CHEMBL456", "name": "Ibuprofen", "mw": 206.29},
    ... ]
    >>> def process_batch(records: RecordBatch) -> list[dict[str, Any]]:
    ...     return [dict(r) for r in records]

Note:
    ``Sequence[Mapping[str, Any]]`` is more general than ``list[dict[str, Any]]``,
    allowing tuple of dicts, list of OrderedDicts, etc.
"""

__all__ = [
    "Record",
    "RecordBatch",
    "RecordSet",
    "TabularData",
    "MutableTabularData",
]


@runtime_checkable
class Record(Protocol):
    """Single data record abstraction.

    Represents a single row of tabular data with dict-like access.
    Implementations should provide key-value access to record fields.

    This protocol is compatible with:
    - dict[str, Any]
    - pd.Series (via adapter)
    - Any Mapping[str, Any]

    Example:
        >>> def process_record(record: Record) -> str:
        ...     return record["molecule_chembl_id"]
    """

    def __getitem__(self, key: str) -> Any:
        """Get value by column name.

        Args:
            key: Column/field name.

        Returns:
            Value at the given key.

        Raises:
            KeyError: If key does not exist.
        """
        ...

    def keys(self) -> Iterator[str]:
        """Return iterator over column names.

        Returns:
            Iterator yielding column/field names.
        """
        ...

    def values(self) -> Iterator[Any]:
        """Return iterator over values.

        Returns:
            Iterator yielding field values.
        """
        ...

    def items(self) -> Iterator[tuple[str, Any]]:
        """Return iterator over (key, value) pairs.

        Returns:
            Iterator yielding (column_name, value) tuples.
        """
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key with optional default.

        Args:
            key: Column/field name.
            default: Value to return if key doesn't exist.

        Returns:
            Value at key or default.
        """
        ...


@runtime_checkable
class RecordSet(Protocol):
    """Collection of records with schema information.

    Represents a read-only collection of records that can be iterated.
    Provides schema information via columns() method.

    Example:
        >>> def count_records(records: RecordSet) -> int:
        ...     return len(records)
        ...
        >>> def get_columns(records: RecordSet) -> list[str]:
        ...     return records.columns()
    """

    def columns(self) -> list[str]:
        """Return list of column names.

        Returns:
            Ordered list of column names defining the schema.
        """
        ...

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        """Iterate over records as mappings.

        Yields:
            Each record as a Mapping[str, Any].
        """
        ...

    def __len__(self) -> int:
        """Return number of records.

        Returns:
            Count of records in the collection.
        """
        ...


@runtime_checkable
class TabularData(Protocol):
    """Tabular data abstraction replacing pd.DataFrame in domain contracts.

    This protocol defines the minimal interface needed for domain operations
    on tabular data. It is intentionally minimal to:
    1. Keep domain layer pure and implementation-agnostic
    2. Allow multiple backends (pandas, polars, etc.)
    3. Support testing with simple dict-based implementations

    Key design decisions:
    - columns is a property (not method) for pandas compatibility
    - iterrows returns (index, Mapping) for row-by-row processing
    - to_records returns list[dict] for serialization/interop

    Example:
        >>> def process_data(data: TabularData) -> int:
        ...     print(f"Processing {data.shape[0]} rows, {data.shape[1]} columns")
        ...     for idx, row in data.iterrows():
        ...         # Process each row
        ...         pass
        ...     return data.shape[0]
    """

    @property
    def columns(self) -> list[str]:
        """Return list of column names.

        Returns:
            Ordered list of column names.
        """
        ...

    @property
    def shape(self) -> tuple[int, int]:
        """Return (rows, columns) dimensions.

        Returns:
            Tuple of (num_rows, num_columns).
        """
        ...

    def iterrows(self) -> Iterator[tuple[int, Mapping[str, Any]]]:
        """Iterate over rows as (index, record) pairs.

        Yields:
            Tuple of (row_index, row_data) where row_data is a Mapping.

        Note:
            Index is typically integer position but may vary by implementation.
        """
        ...

    def to_records(self) -> list[dict[str, Any]]:
        """Convert to list of dictionaries.

        Returns:
            List where each element is a dict representing one row.

        Note:
            This creates a copy of the data. Use iterrows() for
            memory-efficient iteration.
        """
        ...

    def __len__(self) -> int:
        """Return number of rows.

        Returns:
            Row count (same as shape[0]).
        """
        ...

    def __iter__(self) -> Iterator[str]:
        """Iterate over column names.

        Yields:
            Column names (for pandas compatibility).
        """
        ...


@runtime_checkable
class MutableTabularData(TabularData, Protocol):
    """Mutable tabular data with column operations.

    Extends TabularData with mutation capabilities needed for
    transformation operations in the domain layer.

    Note:
        Most domain contracts should use TabularData (immutable).
        Use MutableTabularData only when mutation is required.
    """

    def __setitem__(self, key: str, value: Any) -> None:
        """Set column values.

        Args:
            key: Column name.
            value: Values to set (scalar or sequence).
        """
        ...

    def copy(self) -> "MutableTabularData":
        """Create a copy of the data.

        Returns:
            New MutableTabularData with copied data.
        """
        ...
