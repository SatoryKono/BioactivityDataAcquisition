"""Port for loading pipeline schema contracts from configuration.

This module defines the abstract contract for loading pipeline schema
mappings from external configuration sources (YAML, database, etc.)
instead of hardcoding them in the domain layer.

The separation allows:
- Adding new pipelines without modifying domain code
- Environment-specific contract overrides
- Easier testing with mock contracts
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel


class PipelineContractLoaderPortABC(ABC):
    """Abstract port for loading pipeline schema contracts.

    Implementations load contract definitions from external sources
    (YAML files, databases, etc.) and provide them to the application layer.

    Example:
        >>> class YamlContractLoader(PipelineContractLoaderPortABC):
        ...     def load_contracts(self) -> dict[str, PipelineSchemaModel]:
        ...         return load_from_yaml("configs/pipeline_contracts.yaml")
    """

    @abstractmethod
    def load_contracts(self) -> dict[str, PipelineSchemaModel]:
        """Load all pipeline contracts from configuration.

        Returns:
            Dictionary mapping pipeline_code to PipelineSchemaModel.

        Raises:
            ConfigurationError: If contracts cannot be loaded.
        """

    @abstractmethod
    def get_contract(
        self,
        pipeline_code: str,
        *,
        default_entity: str | None = None,
    ) -> PipelineSchemaModel:
        """Get schema contract for a specific pipeline.

        Args:
            pipeline_code: Pipeline identifier (e.g., "chembl.activity").
            default_entity: Fallback entity name if pipeline_code not found.

        Returns:
            PipelineSchemaModel containing input/output schema names.

        Raises:
            ValueError: If pipeline contract cannot be resolved and no default.
        """

    @abstractmethod
    def has_contract(self, pipeline_code: str) -> bool:
        """Check if a contract exists for the given pipeline.

        Args:
            pipeline_code: Pipeline identifier to check.

        Returns:
            True if contract is defined, False otherwise.
        """

    @abstractmethod
    def list_pipeline_codes(self) -> list[str]:
        """List all registered pipeline codes.

        Returns:
            List of pipeline codes with defined contracts.
        """


class PipelineContractLoaderError(Exception):
    """Error loading pipeline contracts from configuration."""


__all__ = [
    "PipelineContractLoaderPortABC",
    "PipelineContractLoaderError",
]
