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

# Metadata sidecar filename
METADATA_FILENAME = "_metadata.yaml"


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
    ) -> str:
        """Write Bronze layer metadata sidecar file.

        Args:
            base_path: Base path where Bronze data is stored.
                      Metadata will be written to {base_path}/_metadata.yaml
            metadata: Bronze metadata model with lineage and source info.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_metadata(base_path, metadata, "bronze")

    async def write_silver_metadata(
        self,
        base_path: str | Path,
        metadata: SilverMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
    ) -> str:
        """Write Silver layer metadata sidecar file.

        Args:
            base_path: Base path where Silver Delta table is stored.
                      Metadata will be written to {base_path}/_metadata.yaml
            metadata: Silver metadata model with lineage, DQ metrics, and Delta info.
            table_name: Table name for flat_structure naming pattern.
            flat_structure: If True, write as {table_name}_metadata.yaml instead of
                          _metadata.yaml in a subdirectory.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_metadata(
            base_path, metadata, "silver", table_name=table_name, flat_structure=flat_structure
        )

    async def write_gold_metadata(
        self,
        base_path: str | Path,
        metadata: GoldMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
    ) -> str:
        """Write Gold layer metadata sidecar file.

        Args:
            base_path: Base path where Gold Delta/Parquet table is stored.
                      Metadata will be written to {base_path}/_metadata.yaml
            metadata: Gold metadata model with lineage, schema contract, and SCD info.
            table_name: Table name for flat_structure naming pattern.
            flat_structure: If True, write as {table_name}_metadata.yaml instead of
                          _metadata.yaml in a subdirectory.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_metadata(
            base_path, metadata, "gold", table_name=table_name, flat_structure=flat_structure
        )

    async def _write_metadata(
        self,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
    ) -> str:
        """Write metadata to sidecar file.

        Args:
            base_path: Base path for metadata file.
            metadata: Pydantic metadata model.
            layer: Layer name for logging.
            table_name: Table name for flat_structure naming pattern.
            flat_structure: If True, write as {table_name}_metadata.yaml.

        Returns:
            Absolute path to written metadata file.
        """
        path = Path(base_path)
        if flat_structure and table_name:
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
        pass


class NoOpMetadataWriter:
    """No-op implementation of MetadataWriterPort.

    Used when save_metadata is disabled or for testing.
    """

    async def write_bronze_metadata(
        self,
        base_path: str | Path,
        metadata: BronzeMetadata,
    ) -> str:
        """No-op Bronze metadata write."""
        return ""

    async def write_silver_metadata(
        self,
        base_path: str | Path,
        metadata: SilverMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
    ) -> str:
        """No-op Silver metadata write."""
        return ""

    async def write_gold_metadata(
        self,
        base_path: str | Path,
        metadata: GoldMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
    ) -> str:
        """No-op Gold metadata write."""
        return ""

    async def aclose(self) -> None:
        """No-op close."""
        pass
