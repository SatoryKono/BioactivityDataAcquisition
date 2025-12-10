"""Schema contract provider implementation."""

from __future__ import annotations

from typing import Any

from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.schemas.fields import build_field_configs_from_schema
from bioetl.domain.schemas.pipeline_contracts import (
    PipelineSchemaModel,
    get_pipeline_contract,
)
from bioetl.domain.validation import SchemaProviderABC


class SchemaContractProviderImpl(SchemaContractProviderABC):
    """Implementation of schema contract provider.

    This class provides access to schema contracts and schema metadata
    for pipeline components. It wraps the pipeline contracts registry
    and delegates to the schema provider for schema access.

    Example:
        >>> from bioetl.domain.schemas.registry import get_default_schema_registry
        >>> schema_provider = get_default_schema_registry()
        >>> contract_provider = SchemaContractProviderImpl(schema_provider)
        >>> contract = contract_provider.get_contract("chembl.activity")
        >>> print(contract.schema_out)  # "activity"
    """

    def __init__(self, schema_provider: SchemaProviderABC) -> None:
        """Initialize with a schema provider.

        Args:
            schema_provider: Provider for accessing registered schemas.
        """
        self._schema_provider = schema_provider

    @property
    def schema_provider(self) -> SchemaProviderABC:
        """Access the underlying schema provider."""
        return self._schema_provider

    def get_contract(
        self,
        pipeline_id: str,
        *,
        default_entity: str | None = None,
    ) -> PipelineSchemaModel:
        """Get schema contract for a pipeline.

        Args:
            pipeline_id: Pipeline identifier (e.g., "chembl.activity").
            default_entity: Fallback entity name if pipeline_id not found.

        Returns:
            PipelineSchemaModel containing input/output schema names.
        """
        return get_pipeline_contract(pipeline_id, default_entity=default_entity)

    def get_input_schema_name(
        self,
        pipeline_id: str,
        *,
        default_entity: str | None = None,
    ) -> str:
        """Get input schema name for a pipeline.

        Args:
            pipeline_id: Pipeline identifier.
            default_entity: Fallback entity name.

        Returns:
            Name of the input schema (e.g., "activity_input").
        """
        contract = self.get_contract(pipeline_id, default_entity=default_entity)
        return contract.schema_in or contract.schema_out

    def get_output_schema_name(
        self,
        pipeline_id: str,
        *,
        default_entity: str | None = None,
    ) -> str:
        """Get output schema name for a pipeline.

        Args:
            pipeline_id: Pipeline identifier.
            default_entity: Fallback entity name.

        Returns:
            Name of the output schema (e.g., "activity_output").
        """
        contract = self.get_contract(pipeline_id, default_entity=default_entity)
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
        schema = self._schema_provider.get_schema(schema_name)
        return build_field_configs_from_schema(schema)


__all__ = ["SchemaContractProviderImpl"]
