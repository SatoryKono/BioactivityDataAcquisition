"""Domain port for schema contract operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SchemaContractProviderABC(ABC):
    """Port for accessing schema contracts.

    This port defines the interface for retrieving schema-related information
    needed by infrastructure components without direct domain dependencies.
    """

    @abstractmethod
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

    @abstractmethod
    def get_field_configs(self, schema_name: str) -> list[dict[str, Any]]:
        """Get field configurations from schema.

        Args:
            schema_name: Name of the registered schema.

        Returns:
            List of field configuration dictionaries containing name, data_type,
            is_nullable, is_filterable, and description keys.

        Raises:
            ValueError: If schema is not registered.
        """


__all__ = ["SchemaContractProviderABC"]
