"""Metadata operations for Silver layer (DQ metrics, lineage, audit)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
)
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult

if TYPE_CHECKING:
    import pyarrow as pa


class SilverMetadataOperations:
    """Metadata operations for Silver layer storage.
    
    Handles DQ metrics calculation, metadata writing, lineage tracking, and auditing.
    This service replaces SilverWriterMetadataMixin through composition.
    """
    
    def __init__(
        self,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        audit: AuditPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        lineage_store: LineageStorePort | None = None,
        dq_calculator: DQMetricsCalculator | None = None,
    ) -> None:
        """Initialize metadata operations.
        
        Args:
            logger: Logger for metadata operations
            metrics: Optional metrics port for instrumentation
            audit: Optional audit port for logging
            metadata_writer: Optional metadata writer
            metadata_coordinator: Optional metadata coordinator
            lineage_store: Optional lineage store
            dq_calculator: Optional DQ metrics calculator
        """
        self._logger = logger
        self._metrics = metrics
        self._audit = audit
        self._metadata_writer = metadata_writer
        self._metadata_coordinator = metadata_coordinator
        self._lineage_store = lineage_store
        self._dq_calculator = dq_calculator
    
    async def compute_dq_metrics(
        self,
        table_name: str,
        arrow_data: pa.Table,
        primary_keys: list[str],
        mode: str,
        validated_mode: SilverWriteMode,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
    ) -> BatchDQMetrics:
        """Compute data quality metrics for Silver write.
        
        Args:
            table_name: Name of the table
            arrow_data: PyArrow table with data
            primary_keys: List of primary key columns
            mode: Write mode (append, merge, delete)
            validated_mode: Validated write mode
            run_id: Optional run ID
            run_type: Optional run type
            source_batch_id: Optional source batch ID
            ingestion_ts: Optional ingestion timestamp
        
        Returns:
            Computed DQ metrics
        """
        if self._dq_calculator is None:
            return BatchDQMetrics.empty()
        
        return self._dq_calculator.calculate(
            table_name=table_name,
            arrow_data=arrow_data,
            primary_keys=primary_keys,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )
    
    async def write_silver_metadata(
        self,
        table_name: str,
        dq_metrics: BatchDQMetrics,
        records: list[BronzeRecord],
        bronze_refs: list[BronzeWriteResult] | None = None,
        mode: str = "merge",
        validated_mode: SilverWriteMode = SilverWriteMode.MERGE,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
    ) -> SilverWriteResult | None:
        """Write metadata for Silver layer.
        
        Args:
            table_name: Name of the table
            dq_metrics: Data quality metrics
            records: Original bronze records
            bronze_refs: Optional bronze write results
            mode: Write mode
            validated_mode: Validated write mode
            run_id: Optional run ID
            run_type: Optional run type
            source_batch_id: Optional source batch ID
            ingestion_ts: Optional ingestion timestamp
            transform_version: Optional transform version
            transform_steps: Optional transform steps
        
        Returns:
            Silver write result or None if metadata writing is disabled
        """
        if self._metadata_writer is None:
            return None
        
        # Build metadata
        metadata = SilverMetadata(
            table_name=table_name,
            dq_metrics=dq_metrics,
            records=records,
            bronze_refs=bronze_refs,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )
        
        # Write metadata
        result = await self._metadata_writer.write(metadata)
        
        if self._metrics:
            self._metrics.increment_counter("silver.metadata_write_success")
        
        if self._audit:
            self._audit.log_event(
                "SilverMetadataWrite",
                {
                    "table": table_name,
                    "records": len(records),
                    "dq_metrics": dq_metrics.dict() if hasattr(dq_metrics, 'dict') else str(dq_metrics),
                    "status": "success"
                }
            )
        
        return result
    
    async def log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: str,
        validated_mode: SilverWriteMode,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Log Silver write audit event.
        
        Args:
            table_name: Name of the table
            records: Records that were written
            mode: Write mode
            validated_mode: Validated write mode
            run_id: Optional run ID
            run_type: Optional run type
            source_batch_id: Optional source batch ID
            ingestion_ts: Optional ingestion timestamp
            success: Whether the operation succeeded
            error: Optional error message
        """
        if not self._audit:
            return
        
        audit_entry = {
            "table": table_name,
            "records": len(records),
            "mode": mode,
            "validated_mode": validated_mode.value if hasattr(validated_mode, 'value') else str(validated_mode),
            "success": success,
        }
        
        if run_id:
            audit_entry["run_id"] = str(run_id)
        if run_type:
            audit_entry["run_type"] = run_type
        if source_batch_id:
            audit_entry["source_batch_id"] = str(source_batch_id)
        if ingestion_ts:
            audit_entry["ingestion_ts"] = ingestion_ts.isoformat()
        if error:
            audit_entry["error"] = error
        
        self._audit.log_event("SilverWrite", audit_entry)
