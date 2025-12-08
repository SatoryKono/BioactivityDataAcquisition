"""
Registry implementation for schema objects (technology-agnostic).
"""

from bioetl.domain.validation import SchemaProviderABC, schema_type


class SchemaRegistry(SchemaProviderABC):
    """
    Реестр схем данных.
    """

    def __init__(self) -> None:
        self._schemas: dict[str, schema_type] = {}
        self._schema_columns: dict[str, list[str] | None] = {}

    def register(
        self,
        name: str,
        schema: schema_type,
        *,
        column_order: list[str] | None = None,
    ) -> None:
        """Register a schema by name."""
        self._schemas[name] = schema
        self._schema_columns[name] = list(column_order) if column_order else None

    def get_schema(self, name: str) -> schema_type:
        """Get schema by name, raises ValueError if not found."""
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        return self._schemas[name]

    def get_schema_columns(self, name: str) -> list[str]:
        """Return column order for schema."""
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        column_order = self._schema_columns.get(name)
        if column_order:
            return list(column_order)
        # Best-effort extraction of column order if schema exposes to_schema
        schema = self._schemas[name]
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


def default_schema_provider() -> SchemaProviderABC:
    """Return the default schema provider (in-memory registry)."""

    return registry


__all__ = ["SchemaRegistry", "registry", "default_schema_provider"]
