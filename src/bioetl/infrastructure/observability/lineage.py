"""Data lineage tracking for ETL pipelines.

Tracks data flow through Bronze → Silver → Gold layers:
- Source information (provider, batch_id, timestamp)
- Transformations applied at each layer
- Parent-child relationships between records
- Audit trail for compliance and debugging

Lineage is stored in Delta Lake tables for queryability.

Usage:
    tracker = LineageTracker(
        delta_path="s3://bucket/lineage",
        pipeline_name="chembl_activity"
    )

    # Record bronze ingestion
    tracker.record_bronze(
        batch_id="batch_001",
        provider="chembl",
        entity_type="activities",
        record_count=1000,
    )

    # Record silver transformation
    tracker.record_transformation(
        source_layer="bronze",
        target_layer="silver",
        source_batch_id="batch_001",
        entity_ids=["chembl_activity_001", "chembl_activity_002"],
        transformation="normalize_activity",
    )
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import polars as pl
from deltalake import DeltaTable, write_deltalake

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LineageRecord:
    """Lineage record for a data transformation.

    Attributes:
        lineage_id: Unique identifier for this lineage record
        pipeline_name: Name of pipeline (e.g., "chembl_activity")
        run_id: Pipeline run identifier
        source_layer: Source data layer (bronze, silver, gold)
        target_layer: Target data layer
        source_batch_id: Source batch identifier
        entity_ids: List of entity IDs affected
        transformation: Name of transformation applied
        record_count: Number of records processed
        success_count: Number of successful transformations
        failure_count: Number of failed transformations
        metadata: Additional metadata (JSON-serializable)
        timestamp: When transformation occurred
    """

    lineage_id: str
    pipeline_name: str
    run_id: str
    source_layer: str
    target_layer: str
    source_batch_id: str
    entity_ids: list[str]
    transformation: str
    record_count: int
    success_count: int
    failure_count: int
    metadata: dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass(frozen=True)
class BatchLineage:
    """Lineage for a complete batch ingestion.

    Attributes:
        batch_id: Batch identifier
        pipeline_name: Pipeline name
        run_id: Run identifier
        provider: Data provider (chembl, pubchem, uniprot)
        entity_type: Entity type (activity, compound, protein)
        layer: Data layer (bronze, silver, gold)
        record_count: Number of records in batch
        file_path: Storage path for batch
        watermark: Watermark value after this batch
        metadata: Additional metadata
        timestamp: Batch ingestion timestamp
    """

    batch_id: str
    pipeline_name: str
    run_id: str
    provider: str
    entity_type: str
    layer: str
    record_count: int
    file_path: str
    watermark: str | None
    metadata: dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


class LineageTracker:
    """Track data lineage across ETL pipeline layers.

    Stores lineage information in Delta Lake tables:
    - batch_lineage: Batch-level lineage (ingestion events)
    - transformation_lineage: Record-level transformations

    Attributes:
        delta_path: Base path for Delta Lake tables
        pipeline_name: Pipeline name for filtering
    """

    def __init__(
        self,
        delta_path: str | Path,
        pipeline_name: str,
    ) -> None:
        """Initialize lineage tracker.

        Args:
            delta_path: Base path for lineage Delta tables
            pipeline_name: Pipeline identifier
        """
        from pathlib import Path

        self.delta_path = Path(delta_path)
        self.pipeline_name = pipeline_name

        # Table paths
        self.batch_table_path = self.delta_path / "batch_lineage"
        self.transformation_table_path = self.delta_path / "transformation_lineage"

    def record_bronze(
        self,
        batch_id: str,
        run_id: str,
        provider: str,
        entity_type: str,
        record_count: int,
        file_path: str,
        watermark: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record bronze layer batch ingestion.

        Args:
            batch_id: Batch identifier
            run_id: Pipeline run ID
            provider: Data provider
            entity_type: Entity type
            record_count: Number of records
            file_path: Storage location
            watermark: Current watermark value
            metadata: Additional metadata
        """
        batch = BatchLineage(
            batch_id=batch_id,
            pipeline_name=self.pipeline_name,
            run_id=run_id,
            provider=provider,
            entity_type=entity_type,
            layer="bronze",
            record_count=record_count,
            file_path=file_path,
            watermark=watermark,
            metadata=metadata or {},
            timestamp=datetime.now(UTC),
        )

        self._write_batch_lineage(batch)

    def record_transformation(
        self,
        run_id: str,
        source_layer: str,
        target_layer: str,
        source_batch_id: str,
        entity_ids: list[str],
        transformation: str,
        record_count: int,
        success_count: int,
        failure_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record data transformation between layers.

        Args:
            run_id: Pipeline run ID
            source_layer: Source layer (bronze, silver)
            target_layer: Target layer (silver, gold)
            source_batch_id: Source batch ID
            entity_ids: Entity IDs transformed
            transformation: Transformation name
            record_count: Total records processed
            success_count: Successful transformations
            failure_count: Failed transformations
            metadata: Additional metadata
        """
        lineage = LineageRecord(
            lineage_id=str(uuid4()),
            pipeline_name=self.pipeline_name,
            run_id=run_id,
            source_layer=source_layer,
            target_layer=target_layer,
            source_batch_id=source_batch_id,
            entity_ids=entity_ids,
            transformation=transformation,
            record_count=record_count,
            success_count=success_count,
            failure_count=failure_count,
            metadata=metadata or {},
            timestamp=datetime.now(UTC),
        )

        self._write_transformation_lineage(lineage)

    def _write_batch_lineage(self, batch: BatchLineage) -> None:
        """Write batch lineage to Delta table.

        Args:
            batch: Batch lineage record
        """
        df = pl.DataFrame([batch.to_dict()])

        try:
            write_deltalake(
                str(self.batch_table_path),
                df.to_arrow(),
                mode="append",
                schema_mode="merge",
            )
            logger.debug(f"Recorded batch lineage: {batch.batch_id}")
        except Exception as e:
            logger.error(f"Failed to write batch lineage: {e}")
            raise

    def _write_transformation_lineage(self, lineage: LineageRecord) -> None:
        """Write transformation lineage to Delta table.

        Args:
            lineage: Transformation lineage record
        """
        # Convert list of entity_ids to string for storage
        record_dict = lineage.to_dict()
        record_dict["entity_ids"] = ",".join(lineage.entity_ids)

        df = pl.DataFrame([record_dict])

        try:
            write_deltalake(
                str(self.transformation_table_path),
                df.to_arrow(),
                mode="append",
                schema_mode="merge",
            )
            logger.debug(f"Recorded transformation lineage: {lineage.lineage_id}")
        except Exception as e:
            logger.error(f"Failed to write transformation lineage: {e}")
            raise

    def query_batch_history(
        self,
        layer: str | None = None,
        provider: str | None = None,
        limit: int = 100,
    ) -> pl.DataFrame:
        """Query batch lineage history.

        Args:
            layer: Filter by layer (bronze, silver, gold)
            provider: Filter by provider
            limit: Maximum records to return

        Returns:
            DataFrame with batch lineage records
        """
        try:
            dt = DeltaTable(str(self.batch_table_path))
            df = dt.to_polars()

            # Filter by pipeline
            df = df.filter(pl.col("pipeline_name") == self.pipeline_name)

            # Apply filters
            if layer:
                df = df.filter(pl.col("layer") == layer)
            if provider:
                df = df.filter(pl.col("provider") == provider)

            # Sort by timestamp descending
            df = df.sort("timestamp", descending=True)

            return df.head(limit)

        except Exception as e:
            logger.error(f"Failed to query batch history: {e}")
            return pl.DataFrame()

    def query_transformation_history(
        self,
        source_layer: str | None = None,
        target_layer: str | None = None,
        transformation: str | None = None,
        limit: int = 100,
    ) -> pl.DataFrame:
        """Query transformation lineage history.

        Args:
            source_layer: Filter by source layer
            target_layer: Filter by target layer
            transformation: Filter by transformation name
            limit: Maximum records to return

        Returns:
            DataFrame with transformation lineage records
        """
        try:
            dt = DeltaTable(str(self.transformation_table_path))
            df = dt.to_polars()

            # Filter by pipeline
            df = df.filter(pl.col("pipeline_name") == self.pipeline_name)

            # Apply filters
            if source_layer:
                df = df.filter(pl.col("source_layer") == source_layer)
            if target_layer:
                df = df.filter(pl.col("target_layer") == target_layer)
            if transformation:
                df = df.filter(pl.col("transformation") == transformation)

            # Sort by timestamp descending
            df = df.sort("timestamp", descending=True)

            return df.head(limit)

        except Exception as e:
            logger.error(f"Failed to query transformation history: {e}")
            return pl.DataFrame()

    def get_entity_lineage(
        self,
        entity_id: str,
    ) -> pl.DataFrame:
        """Get complete lineage for a specific entity.

        Traces entity from bronze ingestion through all transformations.

        Args:
            entity_id: Entity identifier to trace

        Returns:
            DataFrame with lineage chain for entity
        """
        try:
            dt = DeltaTable(str(self.transformation_table_path))
            df = dt.to_polars()

            # Filter by pipeline and entity_id
            df = df.filter(pl.col("pipeline_name") == self.pipeline_name)
            df = df.filter(pl.col("entity_ids").str.contains(entity_id))

            # Sort by timestamp to show chronological flow
            df = df.sort("timestamp")

            return df

        except Exception as e:
            logger.error(f"Failed to get entity lineage: {e}")
            return pl.DataFrame()

    def get_batch_statistics(
        self,
        layer: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get batch statistics for a layer.

        Args:
            layer: Data layer (bronze, silver, gold)
            days: Number of days to analyze

        Returns:
            Dictionary with statistics (total_batches, total_records, avg_batch_size)
        """
        try:
            dt = DeltaTable(str(self.batch_table_path))
            df = dt.to_polars()

            # Filter by pipeline and layer
            df = df.filter(pl.col("pipeline_name") == self.pipeline_name)
            df = df.filter(pl.col("layer") == layer)

            # Filter by date range
            cutoff = datetime.now(UTC).timestamp() - (days * 86400)
            df = df.filter(pl.col("timestamp") >= cutoff)

            if df.height == 0:
                return {
                    "total_batches": 0,
                    "total_records": 0,
                    "avg_batch_size": 0.0,
                }

            total_batches = df.height
            total_records = df["record_count"].sum()
            avg_batch_size = df["record_count"].mean()

            return {
                "total_batches": total_batches,
                "total_records": int(total_records),
                "avg_batch_size": float(avg_batch_size),
            }

        except Exception as e:
            logger.error(f"Failed to get batch statistics: {e}")
            return {
                "total_batches": 0,
                "total_records": 0,
                "avg_batch_size": 0.0,
            }
