"""Storage port for Medallion layer operations.

This module defines narrow, layer-specific storage ports following the
Interface Segregation Principle (ISP). Each port covers a single concern:

- BronzeStoragePort: Bronze layer write and cleanup
- SilverStoragePort: Silver layer write, read, and clear
- GoldStoragePort: Gold layer write and clear
- MergedStoragePort: Composite pipeline merged writes
- StorageMaintenancePort: Cross-layer maintenance (vacuum, optimize, archive, path)
- StorageLifecyclePort: Resource lifecycle (aclose, health_check)

StoragePort is an aggregate facade inheriting all narrow ports for backward
compatibility. New consumers SHOULD depend on the narrowest port they need.

Note:
    Lock validation is performed at Application layer (BatchWriter)
    per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O adapters.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

from bioetl.domain.ports.storage_maintenance import StorageMaintenancePort
from bioetl.domain.types import (
    ArrowSchema,
    BatchID,
    BronzeRecord,
    GoldRecord,
    HealthStatus,
    MetaDict,
    RunID,
    RunType,
    ScdConfig,
)
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult

if TYPE_CHECKING:
    from pandera.api.dataframe.container import DataFrameSchema

    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.models.metadata import SourceMetadata

__all__ = [
    "BronzeStoragePort",
    "GoldStoragePort",
    "MergedStoragePort",
    "SilverStoragePort",
    "StorageLifecyclePort",
    "StorageMaintenancePort",
    "StoragePort",
]


# ---------------------------------------------------------------------------
# Narrow layer-specific ports
# ---------------------------------------------------------------------------


@runtime_checkable
class BronzeStoragePort(Protocol):
    """Port for Bronze layer storage operations.

    Covers raw data ingestion and Bronze retention cleanup.
    """

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write raw records to the Bronze layer.

        Args:
            records: An iterable of byte strings, where each string is a raw record.
            provider: The name of the data provider.
            entity: The type of entity being written.
            date: The datetime for the data partition.
            batch_id: The unique identifier for the batch of records.
            run_id: The unique identifier for the pipeline run (for traceability).
            run_type: The type of pipeline run (incremental, backfill, rebuild).
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking. If None, a minimal
                           SourceMetadata is created with type="api".

        Returns:
            BronzeWriteResult: Result containing path, record count, sizes,
                and checksum for downstream lineage tracking.
        """
        ...

    async def cleanup_bronze(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention).

        Args:
            cutoff_date: Files older than this date will be removed.
            dry_run: If True, only count what would be removed.

        Returns:
            Dict with cleanup stats (files_removed, bytes_freed, directories_removed).
        """
        ...


@runtime_checkable
class SilverStoragePort(Protocol):
    """Port for Silver layer storage operations.

    Covers Silver write (with schema), read-back, and layer clear.
    """

    async def write_silver(
        self,
        table_name: str,
        records: list[
            BronzeRecord
        ],  # BronzeRecord: normalized records before Silver write
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
        key_nullability_rules: list[KeyNullabilityRule] | None = None,
    ) -> SilverWriteResult | None:
        """Write transformed records to the Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
            on_schema_mismatch: How to handle schema drift:
                - 'error': Raise SchemaEvolutionError (default)
                - 'evolve': Allow schema evolution (add new columns)
                - 'ignore': Proceed without changes (filter to existing schema)
            column_order: Optional explicit column order to apply.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).
            key_nullability_rules: Optional rules for key nullability handling.

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Raises:
            SchemaEvolutionError: If schema drift detected and on_schema_mismatch='error'
        """
        ...

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[
        BronzeRecord
    ]:  # BronzeRecord: read-back Silver records share the same shape
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        ...

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        ...


@runtime_checkable
class GoldStoragePort(Protocol):
    """Port for Gold layer storage operations.

    Covers Gold write (with Pandera validation) and layer clear.
    """

    async def write_gold(
        self,
        table_name: str,
        records: list[GoldRecord],
        schema: Any,  # Any: Pandera DataFrameModel which has no common base type
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        scd_config: ScdConfig | None = None,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: (
            list[Any] | None  # Any: port contract allows heterogeneous list items
        ) = None,  # Any: port contract allows heterogeneous list items
    ) -> None:
        """Write aggregated or validated records to the Gold layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a gold record.
            schema: Pandera DataFrameSchema for strict validation (required).
            primary_keys: Optional list of column names for sorting/deduplication.
            mode: The write mode (e.g., 'overwrite', 'append', 'scd2').
            scd_config: Optional SCD2 configuration.
            column_order: Optional explicit column order to apply.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required for audit.
            run_id: Run identifier for audit correlation across layers.
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Raises:
            ValueError: If schema validation fails (strict=True required).
        """
        ...

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        ...


@runtime_checkable
class MergedStoragePort(Protocol):
    """Port for composite pipeline merged writes.

    Used by composite pipelines where schema is dynamically determined
    by the merge operation, bypassing strict schema validation.
    """

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],  # BronzeRecord: merged Silver records
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Used by composite pipelines where schema is dynamically determined
        by the merge operation. Schema is inferred from the records.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical_column_order()
                and preserve the column order from records (e.g. semantic
                ordering applied by ColumnOrderer in composite pipelines).
        """
        ...

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
        schema: DataFrameSchema | None = None,  # type: ignore[type-arg]
    ) -> None:
        """Write merged records to Gold layer without Pandera schema.

        Used by composite pipelines where schema is dynamically determined
        by the merge operation. Optional Pandera validation can be applied
        when a composite contract is available.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical_column_order()
                and preserve the column order from records (e.g. semantic
                ordering applied by ColumnOrderer in composite pipelines).
            schema: Optional Pandera schema used for strict contract validation.
        """
        ...


@runtime_checkable
class StorageLifecyclePort(Protocol):
    """Port for storage resource lifecycle management.

    Covers graceful shutdown and health checking.
    """

    async def aclose(self) -> None:
        """Gracefully close the storage connection and release resources."""
        ...

    async def health_check(self) -> HealthStatus:
        """Check storage accessibility and basic write capability.

        Validates:
        - Bronze, Silver, Gold directories exist or can be created
        - Directories are writable

        Returns:
            HealthStatus indicating storage health:
            - HEALTHY: All layers accessible and writable
            - DEGRADED: Partial access (some layers unavailable)
            - UNHEALTHY: Storage completely unavailable
        """
        ...


# ---------------------------------------------------------------------------
# Aggregate facade (backward compatibility)
# ---------------------------------------------------------------------------


@runtime_checkable
class StoragePort(
    BronzeStoragePort,
    SilverStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    StorageMaintenancePort,
    StorageLifecyclePort,
    Protocol,
):
    """Aggregate storage port — union of all narrow layer-specific ports.

    Exists for backward compatibility. New consumers SHOULD depend on the
    narrowest port they need (e.g., ``SilverStoragePort`` instead of
    ``StoragePort``).

    See Also:
        BronzeStoragePort, SilverStoragePort, GoldStoragePort,
        MergedStoragePort, StorageMaintenancePort, StorageLifecyclePort.
    """

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> MetaDict:
        """Compatibility re-declaration for legacy StoragePort patch points.

        The authoritative contract lives on ``StorageMaintenancePort``.
        """
        ...

    ...
