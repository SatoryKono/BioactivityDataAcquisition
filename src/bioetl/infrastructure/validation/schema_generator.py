"""Pandera schema generator implementation.

This module provides concrete implementations of schema generation protocols
using Pandera for DataFrame validation and YAML for configuration loading.
"""

from __future__ import annotations

from pathlib import Path

import pandera.pandas as pa
import yaml


class PanderaSchemaGenerator:
    """Generate Pandera schemas from column descriptors.

    This implementation creates permissive Pandera DataFrameSchema instances
    where all columns are typed as `object` with nullable=True.

    Implements: SchemaGeneratorProtocol

    Example:
        >>> generator = PanderaSchemaGenerator()
        >>> schema = generator.generate_from_column_order(["id", "name", "value"])
        >>> validated_df = schema.validate(df)
    """

    def generate_from_column_order(self, columns: list[str]) -> pa.DataFrameSchema:
        """Build a permissive Pandera schema using the provided column order.

        Creates a schema where all columns are typed as `object` with nullable=True.
        This is useful for initial data loading before strict validation.

        Args:
            columns: List of column names in desired order.

        Returns:
            A permissive Pandera DataFrameSchema accepting any data types.
        """
        return pa.DataFrameSchema(
            {col: pa.Column(object, nullable=True, coerce=True) for col in columns}
        )


class YamlColumnOrderLoader:
    """Load column orders from YAML files.

    This implementation supports two YAML formats:
    1. Simple list: ["col1", "col2", "col3"]
    2. Dict with columns key: {"columns": ["col1", "col2", "col3"]}

    Implements: ColumnOrderLoaderProtocol

    Example:
        >>> loader = YamlColumnOrderLoader()
        >>> columns = loader.load("path/to/columns.yaml")
    """

    def load(self, path: str | Path) -> list[str]:
        """Load column order from YAML file.

        Args:
            path: Path to YAML file (str or Path object).

        Returns:
            List of column names in order.

        Raises:
            ValueError: If YAML format is invalid.
            FileNotFoundError: If the file does not exist.
        """
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Column order file not found: {yaml_path}")

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            return [str(x) for x in data]

        if isinstance(data, dict) and "columns" in data:
            cols = data["columns"]
            if isinstance(cols, list):
                return [str(x) for x in cols]

        raise ValueError(
            f"Invalid column-order YAML format in {yaml_path}. "
            "Expected a list or a dict with 'columns' key."
        )


def generate_schema_from_column_order(columns: list[str]) -> pa.DataFrameSchema:
    """Factory function to generate a Pandera schema from column order.

    This is a convenience function for direct use without instantiating
    the generator class.

    Args:
        columns: List of column names in desired order.

    Returns:
        A permissive Pandera DataFrameSchema.
    """
    return PanderaSchemaGenerator().generate_from_column_order(columns)


def load_column_order_from_yaml(path: str | Path) -> list[str]:
    """Factory function to load column order from YAML file.

    This is a convenience function for direct use without instantiating
    the loader class.

    Args:
        path: Path to YAML file.

    Returns:
        List of column names in order.
    """
    return YamlColumnOrderLoader().load(path)


__all__ = [
    "PanderaSchemaGenerator",
    "YamlColumnOrderLoader",
    "generate_schema_from_column_order",
    "load_column_order_from_yaml",
]
