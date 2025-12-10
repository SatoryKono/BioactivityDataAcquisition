"""Application layer implementation of schema contract provider."""

from __future__ import annotations

from typing import Any

from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.schemas.fields import build_field_configs_from_schema
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.validation import SchemaProviderABC


class SchemaContractProviderImpl(SchemaContractProviderABC):
    """Application layer implementation of schema contract provider.

    This adapter bridges the domain schema functionality with infrastructure
    components that need schema information without direct domain dependencies.
    """

    def __init__(self, schema_provider: SchemaProviderABC) -> None:
        """Initialize with a schema provider.

        Args:
            schema_provider: Provider for accessing registered schemas.
        """
        self._provider = schema_provider

    def get_output_schema_name(
        self,
        pipeline_code: str,
        *,
        default_entity: str | None = None,
    ) -> str:
        """Get output schema name for pipeline.

        Args:
            pipeline_code: Pipeline identifier (e.g., 'chembl.activity').
            default_entity: Fallback entity name if pipeline has no explicit contract.

        Returns:
            Schema name to use for output validation and field derivation.
        """
        contract = get_pipeline_contract(pipeline_code, default_entity=default_entity)
        return contract.get_output_schema()

    def get_field_configs(self, schema_name: str) -> list[dict[str, Any]]:
        """Get field configurations from schema.

        Args:
            schema_name: Name of the registered schema.

        Returns:
            List of field configuration dictionaries.

        Raises:
            ValueError: If schema is not registered.
        """
        schema = self._provider.get_schema(schema_name)
        return build_field_configs_from_schema(schema)


__all__ = ["SchemaContractProviderImpl"]
