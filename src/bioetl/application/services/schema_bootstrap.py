"""Schema bootstrap service for application initialization."""

from __future__ import annotations

from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.schemas.registry import get_default_schema_registry
from bioetl.domain.validation import SchemaProviderABC


class SchemaBootstrapService:
    """Service for initializing schema infrastructure.

    This service handles the creation and registration of schemas,
    providing a clean entry point for application bootstrap.
    """

    def __init__(
        self,
        schema_provider: SchemaProviderABC | None = None,
    ) -> None:
        """Initialize the bootstrap service.

        Args:
            schema_provider: Optional pre-configured schema provider.
                If None, uses the default schema registry.
        """
        self._schema_provider = schema_provider

    def ensure_registered(self) -> SchemaProviderABC:
        """Ensure schemas are registered and return the provider.

        Returns:
            The schema provider with all schemas registered.
        """
        if self._schema_provider is None:
            self._schema_provider = get_default_schema_registry()
        return self._schema_provider

    def create_contract_provider(self) -> SchemaContractProviderABC:
        """Create a schema contract provider.

        Returns:
            A configured SchemaContractProviderImpl instance.
        """
        schema_provider = self.ensure_registered()
        return SchemaContractProviderImpl(schema_provider)


def create_schema_bootstrap_service(
    schema_provider: SchemaProviderABC | None = None,
) -> SchemaBootstrapService:
    """Factory function for creating the schema bootstrap service.

    Args:
        schema_provider: Optional pre-configured schema provider.

    Returns:
        A configured SchemaBootstrapService instance.
    """
    return SchemaBootstrapService(schema_provider)


__all__ = [
    "SchemaBootstrapService",
    "create_schema_bootstrap_service",
]
