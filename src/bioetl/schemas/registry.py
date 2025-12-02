"""
Registry implementation for Pandera schemas.
"""
from typing import Type
import pandera.pandas as pa

from bioetl.validation.contracts import SchemaProviderABC


class SchemaRegistry(SchemaProviderABC):
    """
    Реестр схем данных.
    """

    def __init__(self) -> None:
        self._schemas: dict[str, Type[pa.DataFrameModel]] = {}

    def register(self, name: str, schema: Type[pa.DataFrameModel]) -> None:
        self._schemas[name] = schema

    def get_schema(self, name: str) -> Type[pa.DataFrameModel]:
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        return self._schemas[name]

    def list_schemas(self) -> list[str]:
        return list(self._schemas.keys())


# Global singleton instance
registry = SchemaRegistry()
