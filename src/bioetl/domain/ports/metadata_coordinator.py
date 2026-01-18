"""Port for Metadata Coordinator.

Defines the interface for metadata coordination across Medallion layers.
The implementation lives in composition layer.

Implements RULES.md §1.2 - Domain Ports pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
        SourceMetadata,
    )
    from bioetl.domain.types import BatchID


@dataclass(frozen=True, slots=True)
class BronzeMetadataInput:
    """Input data for Bronze metadata creation.

    Attributes:
        batch_id: Unique identifier for the batch.
        record_count: Number of records written.
        compressed_size: Size of compressed file in bytes.
        output_path: Relative path to the written file.
        started_at: UTC timestamp when write started.
        completed_at: UTC timestamp when write completed.
        source_metadata: Optional pre-built SourceMetadata with API request
                        details for rich lineage tracking.
    """

    batch_id: BatchID
    record_count: int
    compressed_size: int
    output_path: str
    started_at: datetime
    completed_at: datetime
    source_metadata: SourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class SilverMetadataInput:
    """Input data for Silver metadata creation.

    Attributes:
        table_path: Full path to the Delta table.
        records: List of records written.
        primary_keys: Primary key columns.
        mode: Write mode (merge, append, delete).
        bronze_refs: Optional list of BronzeWriteResult for lineage.
        dq_metrics: Optional BatchDQMetrics for DQ summary.
        version_after: Delta table version after write.
        transform_version: Optional semver version of transform applied.
        transform_steps: Optional list of transform step names applied.
    """

    table_path: str
    records: list[dict[str, Any]]
    primary_keys: list[str]
    mode: Any  # SilverWriteMode - avoid circular import
    bronze_refs: Any | None = None  # list[BronzeWriteResult] | None
    dq_metrics: Any | None = None  # BatchDQMetrics | None
    version_after: int | None = None
    transform_version: str | None = None
    transform_steps: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class SilverRef:
    """Reference to a Silver table for Gold lineage tracking.

    Captures the exact Silver source used for Gold transformation,
    enabling full data lineage from Bronze → Silver → Gold.

    Attributes:
        table_name: Silver table name (e.g., "chembl.activity").
        table_path: Full path to Silver Delta table.
        delta_version: Delta version of Silver table when read.
    """

    table_name: str
    table_path: str
    delta_version: int


@dataclass(frozen=True, slots=True)
class GoldMetadataInput:
    """Input data for Gold metadata creation.

    Attributes:
        table_path: Full path to the Delta table.
        table_name: Table name.
        records: List of records written.
        mode: Write mode (overwrite, append, scd2).
        scd_config: SCD2 configuration if applicable.
        completed_at: UTC timestamp when write completed.
        silver_refs: List of Silver source references for lineage tracking.
        transform_version: Optional semver version of transform applied.
        transform_steps: Optional list of transform step names applied.
    """

    table_path: str
    table_name: str
    records: list[dict[str, Any]]
    mode: Any  # GoldWriteMode - avoid circular import
    scd_config: dict[str, Any] | None = None
    completed_at: datetime | None = None
    silver_refs: list[SilverRef] | None = None
    transform_version: str | None = None
    transform_steps: tuple[str, ...] | None = None


@runtime_checkable
class MetadataCoordinatorPort(Protocol):
    """Port for metadata coordination across Medallion layers.

    Implementations must provide factory methods for creating
    layer-specific metadata with consistent run context.
    """

    def create_bronze_metadata(self, input_data: BronzeMetadataInput) -> BronzeMetadata:
        """Create Bronze layer metadata.

        Args:
            input_data: Bronze-specific metadata inputs.

        Returns:
            Complete BronzeMetadata for sidecar file.
        """
        ...

    def create_silver_metadata(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Create Silver layer metadata.

        Args:
            input_data: Silver-specific metadata inputs.

        Returns:
            Complete SilverMetadata for sidecar file.
        """
        ...

    def create_gold_metadata(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Create Gold layer metadata.

        Args:
            input_data: Gold-specific metadata inputs.

        Returns:
            Complete GoldMetadata for sidecar file.
        """
        ...
