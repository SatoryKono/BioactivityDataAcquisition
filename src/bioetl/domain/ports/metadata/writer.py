"""Metadata writer port for Medallion layer sidecar files.

Defines the protocol for writing _metadata.yaml files alongside
data artifacts in Bronze, Silver, and Gold layers.

Implements RULES.md 2.3 and 02-user-rules.md 2.4:
- Lineage tracking
- QC information
- Runtime context
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )

__all__ = [
    "MetadataWriterPort",
]


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
        base_path: str,
        metadata: BronzeMetadata,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Bronze layer metadata sidecar file.

        Args:
            base_path: Base storage location reference where Bronze data is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Bronze metadata model with lineage and source info.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.

        Note:
            Uses atomic write (temp file + rename) for consistency.
        """
        ...

    async def write_silver_metadata(
        self,
        base_path: str,
        metadata: SilverMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Silver layer metadata sidecar file.

        Args:
            base_path: Base storage location reference where Silver data is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Silver metadata model with lineage, DQ metrics, and Delta info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.

        Note:
            Updates existing metadata file on each pipeline run.
            Uses atomic write (temp file + rename) for consistency.
        """
        ...

    async def finalize_silver_metadata(
        self,
        base_path: str,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
        delta_version_after: int | None = None,
    ) -> str | None:
        """Finalize an existing Silver sidecar without rebuilding metadata.

        Implementations should load the already-written Silver sidecar,
        patch only postrun-final values such as DQ report path or a final
        Delta version anchor, and atomically rewrite the same file.

        Returns:
            Absolute path to the rewritten metadata file, or ``None`` when
            the target sidecar does not exist.
        """
        ...

    async def write_gold_metadata(
        self,
        base_path: str,
        metadata: GoldMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Gold layer metadata sidecar file.

        Args:
            base_path: Base storage location reference where Gold data is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Gold metadata model with lineage, schema contract, and SCD info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.

        Note:
            Updates existing metadata file on each rebuild.
            Uses atomic write (temp file + rename) for consistency.
        """
        ...

    async def finalize_gold_metadata(
        self,
        base_path: str,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
    ) -> str | None:
        """Finalize an existing Gold sidecar without rebuilding metadata.

        Implementations should load the already-written Gold sidecar,
        patch only postrun-final values, and atomically rewrite the same file.

        Returns:
            Absolute path to the rewritten metadata file, or ``None`` when
            the target sidecar does not exist.
        """
        ...

    async def aclose(self) -> None:
        """Release any resources held by the metadata writer."""
        ...
