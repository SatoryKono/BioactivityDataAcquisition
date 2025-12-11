"""Domain contracts for schema generation.

This module defines protocol interfaces for schema generation functionality.
Implementations belong in the infrastructure layer (Pandera, YAML parsers, etc.).

These protocols allow the domain to remain pure and independent of specific
validation libraries like Pandera.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class SchemaGeneratorProtocol(Protocol):
    """Protocol for schema generators.

    Implementations create validation schemas from column descriptors.
    The actual schema type depends on the implementation
    (e.g., Pandera DataFrameSchema).

    Example:
        >>> generator = PanderaSchemaGenerator()
        >>> schema = generator.generate_from_column_order(["id", "name", "value"])
    """

    def generate_from_column_order(self, columns: list[str]) -> Any:
        """Generate schema from column order.

        Args:
            columns: List of column names in desired order.

        Returns:
            A validation schema (implementation-specific type).
        """
        ...


class ColumnOrderLoaderProtocol(Protocol):
    """Protocol for loading column orders from files.

    Implementations can load column orders from various sources (YAML, JSON, etc.).

    Example:
        >>> loader = YamlColumnOrderLoader()
        >>> columns = loader.load("path/to/columns.yaml")
    """

    def load(self, path: str | Path) -> list[str]:
        """Load column order from file.

        Args:
            path: Path to the column order file.

        Returns:
            List of column names in order.

        Raises:
            ValueError: If the file format is invalid.
            FileNotFoundError: If the file does not exist.
        """
        ...


__all__ = [
    "SchemaGeneratorProtocol",
    "ColumnOrderLoaderProtocol",
]
