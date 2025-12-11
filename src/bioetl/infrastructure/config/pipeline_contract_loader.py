"""YAML-based pipeline contract loader implementation.

This module provides the infrastructure adapter for loading pipeline schema
contracts from YAML configuration files instead of hardcoded dictionaries.

Usage:
    >>> from bioetl.infrastructure.config.pipeline_contract_loader import (
    ...     YamlPipelineContractLoader,
    ... )
    >>> loader = YamlPipelineContractLoader()
    >>> contract = loader.get_contract("chembl.activity")
    >>> print(contract.schema_out)  # "activity"
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.domain.ports.pipeline_contract_loader import (
    PipelineContractLoaderError,
    PipelineContractLoaderPortABC,
)
from bioetl.infrastructure.config.sources import get_configs_root, get_yaml

if TYPE_CHECKING:
    from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel

# Default contract file name
DEFAULT_CONTRACTS_FILE = "pipeline_contracts.yaml"


class YamlPipelineContractLoader(PipelineContractLoaderPortABC):
    """Load pipeline contracts from YAML configuration file.

    This adapter implements the PipelineContractLoaderPortABC port,
    loading contract definitions from a YAML file instead of hardcoded
    dictionaries in the domain layer.

    The loader supports:
    - Loading contracts from configurable YAML path
    - Fallback to default contract generation for unknown pipelines
    - Caching of loaded contracts for performance

    Example:
        >>> loader = YamlPipelineContractLoader()
        >>> contracts = loader.load_contracts()
        >>> print(list(contracts.keys()))
        ['chembl.activity', 'chembl.assay', ...]

    Attributes:
        config_path: Path to the contracts YAML file.
    """

    def __init__(
        self,
        config_path: Path | str | None = None,
        *,
        base_dir: Path | str | None = None,
    ) -> None:
        """Initialize loader with optional custom config path.

        Args:
            config_path: Explicit path to contracts YAML file.
                If None, uses default location in configs directory.
            base_dir: Base directory for config resolution.
                Only used if config_path is None.
        """
        if config_path is not None:
            self._config_path = Path(config_path)
        else:
            configs_root = get_configs_root(base_dir)
            self._config_path = configs_root / DEFAULT_CONTRACTS_FILE

        self._contracts: dict[str, PipelineSchemaModel] | None = None
        self._default_template: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        """Path to the contracts configuration file."""
        return self._config_path

    def load_contracts(self) -> dict[str, PipelineSchemaModel]:
        """Load all pipeline contracts from YAML configuration.

        Returns:
            Dictionary mapping pipeline_code to PipelineSchemaModel.

        Raises:
            PipelineContractLoaderError: If contracts cannot be loaded.
        """
        if self._contracts is not None:
            return self._contracts

        self._contracts, self._default_template = self._load_from_yaml()
        return self._contracts

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
        """
        contracts = self.load_contracts()

        if pipeline_code in contracts:
            return contracts[pipeline_code]

        # Generate default contract for unknown pipeline
        return self._create_default_contract(pipeline_code, default_entity)

    def has_contract(self, pipeline_code: str) -> bool:
        """Check if a contract exists for the given pipeline.

        Args:
            pipeline_code: Pipeline identifier to check.

        Returns:
            True if contract is explicitly defined, False otherwise.
        """
        contracts = self.load_contracts()
        return pipeline_code in contracts

    def list_pipeline_codes(self) -> list[str]:
        """List all registered pipeline codes.

        Returns:
            List of pipeline codes with defined contracts.
        """
        contracts = self.load_contracts()
        return list(contracts.keys())

    def _load_from_yaml(
        self,
    ) -> tuple[dict[str, PipelineSchemaModel], dict[str, Any] | None]:
        """Load contracts from YAML file.

        Returns:
            Tuple of (contracts dict, default template dict or None).

        Raises:
            PipelineContractLoaderError: If file cannot be loaded or parsed.
        """
        if not self._config_path.exists():
            # Return empty contracts if file doesn't exist
            # This allows fallback to hardcoded defaults
            return {}, None

        try:
            raw_data = get_yaml(self._config_path)
        except Exception as exc:
            raise PipelineContractLoaderError(
                f"Failed to load contracts from {self._config_path}: {exc}"
            ) from exc

        contracts_data = raw_data.get("contracts", {})
        if not isinstance(contracts_data, dict):
            raise PipelineContractLoaderError(
                f"Invalid contracts format in {self._config_path}: "
                "expected 'contracts' to be a mapping"
            )

        contracts: dict[str, PipelineSchemaModel] = {}
        for pipeline_code, contract_data in contracts_data.items():
            try:
                contracts[pipeline_code] = self._parse_contract(
                    pipeline_code, contract_data
                )
            except Exception as exc:
                raise PipelineContractLoaderError(
                    f"Invalid contract definition for '{pipeline_code}': {exc}"
                ) from exc

        default_template = raw_data.get("default_template")

        return contracts, default_template

    @staticmethod
    def _parse_contract(
        pipeline_code: str,
        data: dict[str, Any],
    ) -> PipelineSchemaModel:
        """Parse contract data into PipelineSchemaModel.

        Args:
            pipeline_code: Pipeline identifier for this contract.
            data: Raw contract data from YAML.

        Returns:
            Parsed PipelineSchemaModel instance.
        """
        # Lazy import to comply with architecture rules
        # (infrastructure should not import domain.schemas at module level)
        from bioetl.domain.schemas.pipeline_contracts import (
            PipelineSchemaModel as SchemaModel,
        )

        return SchemaModel(
            pipeline_code=data.get("pipeline_code", pipeline_code),
            schema_out=data["schema_out"],
            schema_in=data.get("schema_in"),
            output_schema=data.get("output_schema"),
        )

    def _create_default_contract(
        self,
        pipeline_code: str,
        default_entity: str | None,
    ) -> PipelineSchemaModel:
        """Create default contract for unknown pipeline.

        Uses default_template from YAML if available, otherwise creates
        a simple contract using the entity name.

        Args:
            pipeline_code: Pipeline identifier.
            default_entity: Optional entity name override.

        Returns:
            Generated PipelineSchemaModel.
        """
        # Lazy import to comply with architecture rules
        from bioetl.domain.schemas.pipeline_contracts import (
            PipelineSchemaModel as SchemaModel,
        )

        # Ensure contracts are loaded to get default_template
        self.load_contracts()

        entity = default_entity
        if entity is None:
            # Extract entity from pipeline_code (e.g., "chembl.activity" -> "activity")
            parts = pipeline_code.split(".")
            entity = parts[-1] if parts else pipeline_code

        if self._default_template:
            # Use template configuration
            suffix_in = self._default_template.get("schema_suffix_in", "_input")
            suffix_out = self._default_template.get("schema_suffix_out", "_output")

            return SchemaModel(
                pipeline_code=pipeline_code,
                schema_out=entity,
                schema_in=f"{entity}{suffix_in}",
                output_schema=f"{entity}{suffix_out}",
            )

        # Simple default: use entity name for all schemas
        return SchemaModel(
            pipeline_code=pipeline_code,
            schema_out=entity,
            schema_in=entity,
            output_schema=entity,
        )


@lru_cache(maxsize=1)
def get_default_contract_loader(
    base_dir: Path | str | None = None,
) -> YamlPipelineContractLoader:
    """Get cached default contract loader instance.

    Args:
        base_dir: Optional base directory for config resolution.

    Returns:
        Cached YamlPipelineContractLoader instance.
    """
    return YamlPipelineContractLoader(base_dir=base_dir)


__all__ = [
    "YamlPipelineContractLoader",
    "get_default_contract_loader",
    "DEFAULT_CONTRACTS_FILE",
]
