"""Write operations mixin for StorageAdapter (Bronze/Silver/Gold)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bioetl.domain.ports.storage.silver_port import (
    SilverWriteRequest,
    coerce_silver_write_request,
)
from bioetl.domain.types import JsonDict, ScdConfig

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.types import BatchID, RunID, RunType
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterWriteMixin"]


class StorageAdapterWriteMixin:
    """Mixin providing core write operations for Bronze, Silver, and Gold layers."""

    bronze: BronzeWriter
    silver: SilverWriter
    gold: GoldWriter

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
        """Write raw records to Bronze layer.

        Args:
            records: Iterator of JSON-encoded record bytes.
            provider: Provider name.
            entity: Entity type.
            date: Date for path partitioning.
            batch_id: Unique batch identifier.
            run_id: Pipeline run identifier.
            run_type: Type of run.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking. If None, a minimal
                           SourceMetadata is created with type="api".

        Returns:
            BronzeWriteResult: Result containing path, record count, sizes,
                and checksum for downstream lineage tracking.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        return await self.bronze.write_bronze(
            records=records,
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            source_metadata=source_metadata,
        )

    async def write_silver(
        self,
        request: SilverWriteRequest | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None:
        """Write transformed records to Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
            on_schema_mismatch: How to handle schema drift.
            column_order: Optional explicit column order to apply.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).
            key_nullability_rules: Optional per-column nullability override rules
                applied during Silver write to relax or tighten key constraints.
            run_id: Optional run identifier for tracing, audit, and metadata.
            run_type: Optional run type for tracing and audit semantics.
            source_batch_id: Optional Bronze batch identifier for lineage metadata.
            ingestion_ts: Optional ingestion timestamp for audit correlation.

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        write_request = coerce_silver_write_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        return await self.silver.write_silver(
            table_name=write_request.table_name,
            records=write_request.records,
            primary_keys=write_request.primary_keys,
            schema=write_request.schema,
            mode=write_request.mode,
            partition_cols=write_request.partition_cols,
            on_schema_mismatch=write_request.on_schema_mismatch,
            column_order=write_request.column_order,
            bronze_refs=write_request.bronze_refs,
            key_nullability_rules=write_request.key_nullability_rules,
            run_id=write_request.run_id,
            run_type=write_request.run_type,
            source_batch_id=write_request.source_batch_id,
            ingestion_ts=write_request.ingestion_ts,
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[JsonDict],  # Any: record/metadata values are heterogeneous
        schema: object,
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        scd_config: ScdConfig | None = None,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Write aggregated records to Gold layer.

        Args:
            table_name: Target table name
            records: Records to write
            schema: Pandera schema for validation
            primary_keys: Optional primary key columns
            mode: Write mode
            scd_config: Optional typed SCD2 configuration when mode is 'scd2'.
            column_order: Optional explicit column order to apply.
            ingestion_ts: Ingestion timestamp for audit (ADR-014)
            run_id: Run identifier for audit correlation
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        await self.gold.write_gold(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=primary_keys,
            mode=mode,
            scd_config=scd_config,
            column_order=column_order,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            silver_refs=silver_refs,
        )
