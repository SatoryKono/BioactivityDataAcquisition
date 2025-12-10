"""Port for schema contract provision.

This module defines the abstract contract for providing schema information
to pipeline components. The schema contract provider allows pipelines to
access schema metadata without direct coupling to the schema registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel


class SchemaContractProviderABC(ABC):
    """Abstract port for providing schema contracts to pipelines.

    This port defines the contract for accessing schema metadata
    used by pipeline components for validation and transformation.
    Implementations inject schema information from the application layer.

    Example:
        >>> class MySchemaProvider(SchemaContractProviderABC):
        ...     def get_contract(self, pipeline_id: str) -> PipelineSchemaModel:
        ...         return get_pipeline_contract(pipeline_id)
    """

    @abstractmethod
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

        Raises:
            ValueError: If pipeline contract cannot be resolved.
        """

    @abstractmethod
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

    @abstractmethod
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


__all__ = ["SchemaContractProviderABC"]
