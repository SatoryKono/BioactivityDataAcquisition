"""
Registry implementation for schema objects (technology-agnostic).
"""

from __future__ import annotations

from collections.abc import Callable
import warnings

from bioetl.domain.schemas.generator import generate_schema_from_column_order
from bioetl.domain.validation import SchemaProviderABC, schema_type

# Type alias for schema registration function
SchemaRegisterFn = Callable[["SchemaRegistry"], SchemaProviderABC]


class SchemaRegistry(SchemaProviderABC):
    """Data schema registry."""

    def __init__(self) -> None:
        self._schemas: dict[str, schema_type | None] = {}
        self._schema_columns: dict[str, list[str] | None] = {}

    def register(
        self,
        name: str,
        schema: schema_type | None,
        *,
        column_order: list[str] | None = None,
    ) -> None:
        """Register a schema by name."""
        if schema is None and column_order is None:
            msg = "Either schema or column_order must be provided"
            raise ValueError(msg)

        self._schemas[name] = schema
        self._schema_columns[name] = list(column_order) if column_order else None

    def get_schema(self, name: str) -> schema_type:
        """Get schema by name, raises ValueError if not found."""
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        schema = self._schemas[name]
        if schema is not None:
            return schema

        column_order = self._schema_columns.get(name)
        if not column_order:
            raise ValueError(f"Column order for schema '{name}' is not available.")

        generated_schema = generate_schema_from_column_order(column_order)
        self._schemas[name] = generated_schema
        return generated_schema

    def get_schema_columns(self, name: str) -> list[str]:
        """Return column order for schema."""
        if name not in self._schemas:
            raise ValueError(f"Schema for '{name}' not found in registry.")
        column_order = self._schema_columns.get(name)
        if column_order:
            return list(column_order)
        # Best-effort extraction of column order if schema exposes to_schema
        schema = self._schemas[name]
        if schema is not None:
            if hasattr(schema, "to_schema"):
                columns = getattr(schema, "to_schema")().columns
                if hasattr(columns, "keys"):
                    return list(columns.keys())
        raise ValueError(f"Column order for schema '{name}' is not available.")

    def list_schemas(self) -> list[str]:
        """Return list of registered schema names."""
        return list(self._schemas.keys())


# ---------------------------------------------------------------------------
# Factory functions (preferred over global state)
# ---------------------------------------------------------------------------


def create_default_schema_registry(
    *,
    register_fn: SchemaRegisterFn | None = None,
) -> SchemaRegistry:
    """
    Create a new SchemaRegistry populated with default schemas.

    Parameters
    ----------
    register_fn
        Optional callable that registers schemas into the registry.
        If not provided, an empty registry is returned.
        Useful for testing with custom schema sets.

    Returns
    -------
    SchemaRegistry
        A freshly created and populated registry instance.
    """
    reg = SchemaRegistry()

    if register_fn is not None:
        register_fn(reg)

    return reg


def register_schemas(provider: SchemaProviderABC) -> SchemaProviderABC:
    """Register all default schemas into the given provider.

    This is a stub function in the domain layer. The actual implementation
    should be provided by the infrastructure layer via dependency injection.

    For actual schema registration, use the infrastructure layer's
    register_schemas function from bioetl.infrastructure.validation.bootstrap.

    Args:
        provider: Schema provider to register schemas into.

    Returns:
        The same provider instance (no-op in domain layer).

    Note:
        This function exists for backward compatibility and type hints.
        Real registration must be done by infrastructure layer.
    """
    # Domain layer cannot register schemas directly - this is infrastructure concern
    # Return provider as-is; actual registration should happen via DI
    return provider


# Lazy-initialized default instance for DI containers
_default_registry: SchemaRegistry | None = None


def get_default_schema_registry() -> SchemaRegistry:
    """
    Return the lazily-initialized default schema registry.

    This function provides a singleton-like access pattern suitable for
    dependency injection containers while avoiding module-level global state.

    For tests requiring isolation, use :func:`create_default_schema_registry`
    to create independent instances.
    """
    global _default_registry  # noqa: PLW0603
    if _default_registry is None:
        _default_registry = create_default_schema_registry()
    return _default_registry


def reset_default_schema_registry() -> None:
    """
    Reset the cached default registry (for testing purposes only).

    This allows tests to clear the lazy-initialized singleton.
    """
    global _default_registry  # noqa: PLW0603
    _default_registry = None


# ---------------------------------------------------------------------------
# Backward compatibility - deprecated global singleton
# ---------------------------------------------------------------------------


class _DeprecatedRegistryProxy:
    """
    Proxy that emits deprecation warning on first attribute access.

    This maintains backward compatibility while encouraging migration
    to the factory pattern.
    """

    _warned: bool = False
    _instance: SchemaRegistry | None = None

    def _warn_once(self) -> None:
        if not self._warned:
            warnings.warn(
                "Global 'registry' is deprecated. "
                "Use get_default_schema_registry() or "
                "create_default_schema_registry() instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            self._warned = True

    def _get_instance(self) -> SchemaRegistry:
        if self._instance is None:
            self._instance = get_default_schema_registry()
        return self._instance

    def __getattr__(self, name: str) -> object:
        self._warn_once()
        return getattr(self._get_instance(), name)

    def __repr__(self) -> str:
        return f"<DeprecatedRegistryProxy wrapping {self._get_instance()!r}>"


# Deprecated: use get_default_schema_registry() instead
registry: SchemaRegistry = _DeprecatedRegistryProxy()  # type: ignore[assignment]


def default_schema_provider() -> SchemaProviderABC:
    """Return the default schema provider (in-memory registry)."""
    return get_default_schema_registry()


__all__ = [
    "SchemaRegistry",
    "create_default_schema_registry",
    "register_schemas",
    "get_default_schema_registry",
    "reset_default_schema_registry",
    # Deprecated exports (for backward compatibility)
    "registry",
    "default_schema_provider",
]
