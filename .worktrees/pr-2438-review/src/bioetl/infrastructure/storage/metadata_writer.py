"""Metadata writer implementation for Medallion layer sidecar files.

Writes _metadata.yaml files alongside data artifacts in Bronze, Silver,
and Gold layers using atomic write pattern for consistency.

Implements RULES.md 2.3 and 02-user-rules.md 2.4:
- Lineage tracking
- QC information
- Runtime context
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bioetl.infrastructure.storage._atomic import atomic_write_text

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports import LoggerPort

# Default metadata sidecar filename (fallback)
METADATA_FILENAME = "_metadata.yaml"


def _get_metadata_filename(provider: str | None, entity: str | None) -> str:
    """Generate metadata filename based on provider and entity.

    Args:
        provider: Provider name (e.g., 'chembl').
        entity: Entity type (e.g., 'activity').

    Returns:
        Filename in format {provider}_{entity}_metadata.yaml if both provided,
        otherwise falls back to _metadata.yaml.
    """
    if provider and entity:
        return f"{provider}_{entity}_metadata.yaml"
    return METADATA_FILENAME


class MetadataWriter:
    """Writer for metadata sidecar files.

    Writes _metadata.yaml files alongside data artifacts in the
    Medallion layers (Bronze, Silver, Gold).

    Uses atomic write pattern (temp file + rename) to ensure
    consistency even during crashes.

    Attributes:
        logger: Structured logger for observability.
    """

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize metadata writer.

        Args:
            logger: Structured logger for observability (MUST be injected).

        Note:
            LoggerPort is required per RULES.md DI requirements.
        """
        self._logger = logger

    async def write_bronze_metadata(
        self,
        base_path: str | Path,
        metadata: BronzeMetadata,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Bronze layer metadata sidecar file.

        Args:
            base_path: Base path where Bronze data is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Bronze metadata model with lineage and source info.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_metadata(
            base_path, metadata, "bronze", provider=provider, entity=entity
        )

    async def write_silver_metadata(
        self,
        base_path: str | Path,
        metadata: SilverMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Silver layer metadata sidecar file.

        Args:
            base_path: Base path where Silver Delta table is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Silver metadata model with lineage, DQ metrics, and Delta info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_metadata(
            base_path,
            metadata,
            "silver",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def write_gold_metadata(
        self,
        base_path: str | Path,
        metadata: GoldMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Gold layer metadata sidecar file.

        Args:
            base_path: Base path where Gold Delta/Parquet table is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Gold metadata model with lineage, schema contract, and SCD info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_metadata(
            base_path,
            metadata,
            "gold",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def _write_metadata(
        self,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write metadata to sidecar file.

        Args:
            base_path: Base path for metadata file.
            metadata: Pydantic metadata model.
            layer: Layer name for logging.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to written metadata file.
        """
        path = Path(base_path)

        # Use provider/entity naming if both are provided
        if provider and entity:
            filename = _get_metadata_filename(provider, entity)
            metadata_path = path / filename
        elif flat_structure and table_name:
            # Backward compatibility: use table_name if flat_structure is True
            metadata_path = path / f"{table_name}_metadata.yaml"
        else:
            metadata_path = path / METADATA_FILENAME

        # Serialize to dict with JSON mode for datetime handling
        metadata_dict = metadata.model_dump(mode="json", by_alias=True)

        # Convert to YAML
        yaml_content = yaml.safe_dump(
            metadata_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        # Write atomically in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: atomic_write_text(metadata_path, yaml_content),
        )

        self._logger.info(
            "metadata_written",
            layer=layer,
            path=str(metadata_path),
            run_id=metadata.runtime.run_id,
        )

        return str(metadata_path.resolve())

    async def aclose(self) -> None:
        """Release any resources held by the metadata writer.

        No resources to release for filesystem-based writer.
        """
