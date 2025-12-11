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

import importlib
from pathlib import Path
from typing import NoReturn
import warnings

__all__ = ["generate_schema_from_column_order", "load_column_order_from_yaml"]


def _load_impl() -> object:
    """Load infrastructure implementation lazily to avoid hard dependency."""
    return importlib.import_module("bioetl.infrastructure.validation.schema_generator")


def _raise_missing_impl(func_name: str) -> NoReturn:
    raise RuntimeError(
        f"{func_name} moved to bioetl.infrastructure.validation.schema_generator. "
        "Use the infrastructure module or inject SchemaGeneratorProtocol instead."
    )


def generate_schema_from_column_order(columns: list[str]) -> object:
    """DEPRECATED: Use PanderaSchemaGenerator from infrastructure.

    Build a permissive Pandera schema using the provided column order.

    .. deprecated:: 2.0
        Use bioetl.infrastructure.validation.schema_generator.
        generate_schema_from_column_order or
        PanderaSchemaGenerator().generate_from_column_order() instead.

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
        (
            "bioetl.domain.schemas.generator.generate_schema_from_column_order "
            "is deprecated. Use "
            "bioetl.infrastructure.validation.schema_generator."
            "generate_schema_from_column_order instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        module = _load_impl()
        impl = getattr(module, "generate_schema_from_column_order")
    except Exception:
        _raise_missing_impl("generate_schema_from_column_order")
    return impl(columns)


def load_column_order_from_yaml(path: str | Path) -> list[str]:
    """DEPRECATED: Use YamlColumnOrderLoader from infrastructure.

    Load column order from YAML file.

    .. deprecated:: 2.0
        Use bioetl.infrastructure.validation.schema_generator.
        load_column_order_from_yaml or YamlColumnOrderLoader().load() instead.

    Args:
        path: Path to YAML file (str or Path object).

    Returns:
        List of column names in order.

    Raises:
        ValueError: If YAML format is invalid.
    """
    warnings.warn(
        (
            "bioetl.domain.schemas.generator.load_column_order_from_yaml "
            "is deprecated. Use "
            "bioetl.infrastructure.validation.schema_generator."
            "load_column_order_from_yaml instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        module = _load_impl()
        impl = getattr(module, "load_column_order_from_yaml")
    except Exception:
        _raise_missing_impl("load_column_order_from_yaml")
    return impl(path)
