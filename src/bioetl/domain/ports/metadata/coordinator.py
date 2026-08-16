"""Port for Metadata Coordinator.

Defines the interface for metadata coordination across Medallion layers.
The implementation lives in composition layer.

Implements RULES.md §1.2 - Domain Ports pattern.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.types import JsonDict, ScdConfig
from bioetl.domain.types.dq_contracts import DQRuleProvenance

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        GovernanceMetadata,
        InputSnapshotRef,
        SchemaInspectionResult,
        SilverMetadata,
        SourceMetadata,
    )
    from bioetl.domain.types import BatchID

__all__ = [
    "BronzeMetadataInput",
    "GoldMetadataInput",
    "MetadataCoordinatorPort",
    "SilverMetadataInput",
    "SilverRef",
]


@dataclass(frozen=True, slots=True)
class BronzeMetadataInput:
    """Input data for Bronze metadata creation.

    Attributes:
        batch_id: Unique identifier for the batch.
        record_count: Number of records written.
        compressed_size: Size of compressed file in bytes.
        output_path: Relative path to the written file.
        output_content_hash: SHA256 hash of the emitted Bronze file bytes.
        started_at: UTC timestamp when write started.
        completed_at: UTC timestamp when write completed.
        source_metadata: Optional pre-built SourceMetadata with API request
                        details for rich lineage tracking.
        query_string: Query string from PipelineRunContext used for data
                     source filtering (e.g., 'assay_type=B').
        governance: Optional governance metadata from pipeline config.
    """

    batch_id: BatchID
    record_count: int
    compressed_size: int
    output_path: str
    started_at: datetime
    completed_at: datetime
    output_content_hash: str | None = None
    source_metadata: SourceMetadata | None = None
    input_snapshots: tuple[InputSnapshotRef, ...] = ()
    query_string: str | None = None
    governance: GovernanceMetadata | None = None


@dataclass(frozen=True, slots=True)
class SilverMetadataInput:
    """Input data for Silver metadata creation.

    Attributes:
        table_path: Full path to the Delta table.
        primary_keys: Primary key columns.
        mode: Write mode (merge, append, delete).
        records: List of records written (current batch).
        total_records: Optional total records for the entire run (aggregates).
        source_batch_ids: Optional list of all source batch IDs for the run.
        bronze_refs: Optional list of BronzeWriteResult for lineage.
        dq_metrics: Optional BatchDQMetrics for DQ summary.
        version_before: Delta table version before write (ADR-029).
        version_after: Delta table version after write.
        transform_version: Optional semver version of transform applied.
        transform_steps: Optional list of transform step names applied.
        dq_report_path: Optional path to generated DQ report for cross-reference.
        dq_rule_provenance: Optional DQ rule provenance entries for traceability.
        partition_by: Partition columns used for the Delta table.
        governance: Optional governance metadata from pipeline config.
        started_at: UTC timestamp when Silver write started.
        completed_at: UTC timestamp when Silver write completed.
        composite_run_id: Optional composite run identifier routed outside row payloads.
        lineage_created_at: Optional composite lineage anchor routed outside row payloads.
        total_bytes: Total size in bytes (ADR-029).
    """

    table_path: str
    primary_keys: list[str]
    mode: object  # object: SilverWriteMode - avoid circular import, only stored
    records: list[JsonDict] | None = None
    total_records: int | None = None
    source_batch_ids: list[str] | None = None
    bronze_refs: object | None = (
        None  # object: list[BronzeWriteResult] - avoid circular import, only stored
    )
    dq_metrics: object | None = (
        None  # object: BatchDQMetrics - avoid circular import, only stored
    )
    version_before: int | None = None  # ADR-029: Delta version before write
    version_after: int | None = None
    transform_version: str | None = None
    transform_steps: tuple[str, ...] | None = None
    dq_report_path: str | None = None
    dq_rule_provenance: list[DQRuleProvenance] | None = None
    partition_by: list[str] | None = None
    governance: GovernanceMetadata | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    composite_run_id: str | None = None
    lineage_created_at: datetime | None = None
    total_bytes: int = 0  # ADR-029: Total size in bytes


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
        mode: Write mode (overwrite, append, scd2).
        records: List of records written (current batch).
        total_records: Optional total records for the entire run (aggregates).
        scd_config: Required config for SCD2 mode.
        started_at: UTC timestamp when write started (ADR-029).
        completed_at: UTC timestamp when write completed.
        silver_refs: List of Silver source references for lineage tracking.
        transform_version: Optional semver version of transform applied.
        transform_steps: Optional list of transform step names applied.
        schema_inspection: Optional framework-neutral schema inspection result.
        governance: Optional governance metadata from pipeline config.
        total_bytes: Total size in bytes (ADR-029).
        partition_count: Number of partitions (ADR-029).
        composite_run_id: Optional composite run identifier routed outside row payloads.
        lineage_created_at: Optional composite lineage anchor routed outside row payloads.
        schema_validation_enabled: Whether schema validation ran before write.
        schema_validation_strict: Whether validation used strict mode.
        dq_rule_provenance: List of DQ rule provenance entries for traceability.
        dq_policy_hash: Hash of the effective DQ policy for consistency checking.
        contract_ref: Reference to the DQ contract used for validation.
        contract_version: Version of the DQ contract used for validation.
    """

    table_path: str
    table_name: str
    mode: object  # object: GoldWriteMode - avoid circular import, only stored
    records: list[JsonDict] | None = None
    total_records: int | None = None
    scd_config: ScdConfig | None = None
    started_at: datetime | None = None  # ADR-029: Write start timestamp
    completed_at: datetime | None = None
    silver_refs: list[SilverRef] | None = None
    transform_version: str | None = None
    transform_steps: tuple[str, ...] | None = None
    dq_report_path: str | None = None
    schema_inspection: SchemaInspectionResult | None = None
    governance: GovernanceMetadata | None = None
    total_bytes: int = 0  # ADR-029: Total size in bytes
    partition_count: int = 0  # ADR-029: Number of partitions
    composite_run_id: str | None = None
    lineage_created_at: datetime | None = None
    schema_validation_enabled: bool = False
    schema_validation_strict: bool | None = None
    dq_rule_provenance: list[DQRuleProvenance] | None = None
    dq_policy_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None

    def __post_init__(self) -> None:
        """Coerce legacy mapping payloads into typed SCD config."""
        if isinstance(self.scd_config, Mapping):
            object.__setattr__(
                self,
                "scd_config",
                ScdConfig.from_mapping(self.scd_config),
            )


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
