"""Pandas adapter for TabularData protocol.

This module provides an adapter that wraps pandas DataFrame to conform
to the domain's TabularData protocol, enabling infrastructure layer
to work with domain abstractions.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    import pandas as pd


class PandasTabularAdapter:
    """Adapter wrapping pandas DataFrame to TabularData protocol.

    This adapter enables the infrastructure layer to pass DataFrames
    through domain layer contracts that expect TabularData.

    Note:
        pandas.DataFrame already satisfies TabularData protocol in most cases.
        This adapter is provided for explicit wrapping and for cases where
        additional control is needed.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        >>> tabular = PandasTabularAdapter(df)
        >>> print(tabular.columns)
        ['id', 'name']
        >>> print(tabular.shape)
        (2, 2)
    """

    def __init__(self, df: "pd.DataFrame") -> None:
        """Initialize adapter with a pandas DataFrame.

        Args:
            df: pandas DataFrame to wrap.
        """
        self._df = df

    @property
    def columns(self) -> list[str]:
        """Return list of column names."""
        return list(self._df.columns)

    @property
    def shape(self) -> tuple[int, int]:
        """Return (rows, columns) dimensions."""
        return self._df.shape

    def __len__(self) -> int:
        """Return number of rows."""
        return len(self._df)

    def __iter__(self) -> Iterator[str]:
        """Iterate over column names."""
        return iter(self._df.columns)

    def iterrows(self) -> Iterator[tuple[int, Mapping[str, Any]]]:
        """Iterate over rows as (index, record) pairs."""
        for idx, row in self._df.iterrows():
            yield idx, row.to_dict()

    def to_records(self) -> list[dict[str, Any]]:
        """Convert to list of dictionaries."""
        return self._df.to_dict(orient="records")

    @property
    def underlying(self) -> "pd.DataFrame":
        """Access underlying DataFrame for infrastructure operations.

        This property is intentionally not part of TabularData protocol
        and should only be used in infrastructure layer.
        """
        return self._df

    def copy(self) -> "PandasTabularAdapter":
        """Create a copy of the adapter with copied DataFrame."""
        return PandasTabularAdapter(self._df.copy())

    def __setitem__(self, key: str, value: Any) -> None:
        """Set column values (for MutableTabularData compatibility)."""
        self._df[key] = value


__all__ = ["PandasTabularAdapter"]
