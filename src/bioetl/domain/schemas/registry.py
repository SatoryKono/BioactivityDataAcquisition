"""
Registry implementation for Pandera schemas.
"""
from typing import Type
import pandera.pandas as pa

from bioetl.domain.validation import SchemaProviderABC


class SchemaRegistry(SchemaProviderABC):
    """
    Реестр схем данных.
    """

    def __init__(self) -> None:
        self._schemas: dict[str, Type[pa.DataFrameModel]] = {}

    def register(self, name: str, schema: Type[pa.DataFrameModel]) -> None:
        """Register a schema by name."""
        self._schemas[name] = schema

    def get_schema(self, name: str) -> Type[pa.DataFrameModel]:
        """Get schema by name, raises ValueError if not found."""
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        return self._schemas[name]

    def list_schemas(self) -> list[str]:
        """Return list of registered schema names."""
        return list(self._schemas.keys())


# Global registry singleton
registry = SchemaRegistry()
