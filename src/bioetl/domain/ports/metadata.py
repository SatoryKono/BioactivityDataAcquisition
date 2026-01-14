"""Metadata writer port for Medallion layer sidecar files.

Defines the protocol for writing _metadata.yaml files alongside
data artifacts in Bronze, Silver, and Gold layers.

Implements RULES.md 2.3 and 02-user-rules.md 2.4:
- Lineage tracking
- QC information
- Runtime context
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )


@runtime_checkable
class MetadataWriterPort(Protocol):
    """Port for writing metadata sidecar files.

    Implementations write _metadata.yaml files alongside data artifacts
    in the Medallion layers (Bronze, Silver, Gold).

    Metadata files contain:
    - Runtime context (run_id, timestamps)
    - Pipeline identification
    - Lineage information
    - Data quality metrics
    - Environment information
    """

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

        Note:
            Uses atomic write (temp file + rename) for consistency.
        """
        ...

    async def write_silver_metadata(
        self,
        base_path: str | Path,
        metadata: SilverMetadata,
    ) -> str:
        """Write Silver layer metadata sidecar file.

        Args:
            base_path: Base path where Silver Delta table is stored.
                      Metadata will be written to {base_path}/_metadata.yaml
            metadata: Silver metadata model with lineage, DQ metrics, and Delta info.

        Returns:
            Absolute path to the written metadata file.

        Note:
            Updates existing metadata file on each pipeline run.
            Uses atomic write (temp file + rename) for consistency.
        """
        ...

    async def write_gold_metadata(
        self,
        base_path: str | Path,
        metadata: GoldMetadata,
    ) -> str:
        """Write Gold layer metadata sidecar file.

        Args:
            base_path: Base path where Gold Delta/Parquet table is stored.
                      Metadata will be written to {base_path}/_metadata.yaml
            metadata: Gold metadata model with lineage, schema contract, and SCD info.

        Returns:
            Absolute path to the written metadata file.

        Note:
            Updates existing metadata file on each rebuild.
            Uses atomic write (temp file + rename) for consistency.
        """
        ...

    async def aclose(self) -> None:
        """Release any resources held by the metadata writer."""
        ...
