"""
Registry implementation for schema objects (technology-agnostic).
"""

from dataclasses import dataclass

from bioetl.domain.validation import SchemaProviderABC, SchemaType


@dataclass
class _SchemaEntry:
    schema: SchemaType
    column_order: list[str] | None = None


class SchemaRegistry(SchemaProviderABC):
    """
    Реестр схем данных.
    """

    def __init__(self) -> None:
        self._schemas: dict[str, _SchemaEntry] = {}

    def register(
        self,
        name: str,
        schema: SchemaType,
        *,
        column_order: list[str] | None = None,
    ) -> None:
        """Register a schema by name."""
        self._schemas[name] = _SchemaEntry(schema=schema, column_order=column_order)

    def get_schema(self, name: str) -> SchemaType:
        """Get schema by name, raises ValueError if not found."""
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        return self._schemas[name].schema

    def get_schema_columns(self, name: str) -> list[str]:
        """Return column order for schema."""
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        entry = self._schemas[name]
        if entry.column_order:
            return list(entry.column_order)
        # Best-effort extraction of column order if schema exposes to_schema
        schema = entry.schema
        if hasattr(schema, "to_schema"):
            columns = getattr(schema, "to_schema")().columns
            if hasattr(columns, "keys"):
                return list(columns.keys())
        raise ValueError(f"Column order for schema '{name}' is not available.")

    def list_schemas(self) -> list[str]:
        """Return list of registered schema names."""
        return list(self._schemas.keys())


# Global registry singleton
registry = SchemaRegistry()
