"""DEPRECATED: Schema generator moved to infrastructure.

This module is deprecated. Use bioetl.infrastructure.validation.schema_generator
instead for schema generation functionality.

The domain layer should not depend on Pandera or YAML parsing directly.
Use the protocol interfaces from bioetl.domain.schemas.contracts for type hints.

Migration guide:
    Old:
        from bioetl.domain.schemas.generator import generate_schema_from_column_order
        schema = generate_schema_from_column_order(columns)

    New:
        from bioetl.infrastructure.validation.schema_generator import (
            generate_schema_from_column_order,
        )
        schema = generate_schema_from_column_order(columns)

For DI-based usage:
    from bioetl.domain.schemas.contracts import SchemaGeneratorProtocol
    from bioetl.infrastructure.validation.schema_generator import PanderaSchemaGenerator

    def my_function(generator: SchemaGeneratorProtocol) -> None:
        schema = generator.generate_from_column_order(columns)

    # At composition root:
    generator = PanderaSchemaGenerator()
    my_function(generator)
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

__all__ = ["generate_schema_from_column_order", "load_column_order_from_yaml"]


def generate_schema_from_column_order(columns: list[str]) -> Any:
    """DEPRECATED: Use PanderaSchemaGenerator from infrastructure.

    Build a permissive Pandera schema using the provided column order.

    .. deprecated:: 2.0
        Use bioetl.infrastructure.validation.schema_generator.generate_schema_from_column_order
        or PanderaSchemaGenerator().generate_from_column_order() instead.

    Parameters
    ----------
    columns
        List of column names in desired order.

    Returns
    -------
    pa.DataFrameSchema
        A permissive schema accepting any data types.
    """
    warnings.warn(
        "bioetl.domain.schemas.generator.generate_schema_from_column_order is deprecated. "
        "Use bioetl.infrastructure.validation.schema_generator.generate_schema_from_column_order "
        "instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Lazy import to maintain backward compatibility
    from bioetl.infrastructure.validation.schema_generator import (
        generate_schema_from_column_order as _impl,
    )

    return _impl(columns)


def load_column_order_from_yaml(path: str | Path) -> list[str]:
    """DEPRECATED: Use YamlColumnOrderLoader from infrastructure.

    Load column order from YAML file.

    .. deprecated:: 2.0
        Use bioetl.infrastructure.validation.schema_generator.load_column_order_from_yaml
        or YamlColumnOrderLoader().load() instead.

    Args:
        path: Path to YAML file (str or Path object).

    Returns:
        List of column names in order.

    Raises:
        ValueError: If YAML format is invalid.
    """
    warnings.warn(
        "bioetl.domain.schemas.generator.load_column_order_from_yaml is deprecated. "
        "Use bioetl.infrastructure.validation.schema_generator.load_column_order_from_yaml "
        "instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from bioetl.infrastructure.validation.schema_generator import (
        load_column_order_from_yaml as _impl,
    )

    return _impl(path)
