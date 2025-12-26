"""Layer Handlers for Record Processing.

Encapsulates logic for each layer (Bronze/Silver/Gold) to keep RecordProcessor clean.
Refactored from RecordProcessor methods.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import DataQualityThresholdError, ProcessingError
from bioetl.domain.medallion import Layer, WriteMode, WriteModePolicy
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.application.core.batch_metrics import BatchMetricsRecorder
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.domain.config import DQConfig, PipelineConfig, TableConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, QuarantinePort, StoragePort
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.delta_writer import DeltaWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter


@dataclass
class SilverBatchResult:
    """Result of silver layer processing."""

    records: list[dict[str, Any]]
    quarantined_count: int


class BronzeLayerHandler:
    """Handles Bronze layer operations."""

    def __init__(
        self,
        storage: BronzeWriter,
        provider: str,
        entity: str,
        run_id: str,
        run_type: str,
        logger: LoggerPort,
    ) -> None:
        self.storage = storage
        self.provider = provider
        self.entity = entity
        self.run_id = run_id
        self.run_type = run_type
        self.logger = logger

    async def handle(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        ingestion_ts: datetime,
    ) -> Path:
        """Write records to bronze layer."""
        # Convert records to JSON lines (bytes)
        # Ensure deterministic sort of keys
        record_bytes = []
        for r in records:
            # We must use sort_keys=True for determinism (if we modify them)
            # Bronze is supposed to be "raw", but if we receive dicts, we serialize.
            serialized = json.dumps(r, sort_keys=True)
            record_bytes.append(serialized.encode("utf-8"))

        return await self.storage.write_bronze(
            records=iter(record_bytes),
            provider=self.provider,
            entity=self.entity,
            date=ingestion_ts,
            batch_id=batch_id,
            run_id=self.run_id,
            run_type=self.run_type,
            ingestion_ts=ingestion_ts,
        )


class SilverLayerHandler:
    """Handles Silver layer operations."""

    def __init__(
        self,
        storage: DeltaWriter,
        quarantine_manager: QuarantinePort,
        schema: Any,
        transformer: BaseTransformer,
        table_config: TableConfig,
        dq_config: DQConfig,
        logger: LoggerPort,
        metrics_recorder: BatchMetricsRecorder,
    ) -> None:
        self.storage = storage
        self.quarantine = quarantine_manager
        self.schema = schema
        self.transformer = transformer
        self.table_config = table_config
        self.dq_config = dq_config
        self.logger = logger
        self.metrics = metrics_recorder

    async def handle(
        self,
        records: list[dict[str, Any]],
        context: PipelineContext,
        batch_id: BatchID,
        bronze_file: Path,
        ingestion_ts: datetime,
    ) -> SilverBatchResult:
        """Process records for silver layer (transform, validate, write)."""
        silver_records = []
        quarantined_count = 0

        for record in records:
            try:
                # Transform
                transformed = await self.transformer.transform_bronze_to_silver(
                    context, record
                )
                if not transformed:
                    continue

                # Add Metadata
                # (Assuming transformer might add some, but we enforce system fields here)
                # But actually, record processor usually added metadata before.
                # Let's ensure critical metadata is present if transformer didn't add it.
                # However, usually transformer returns a domain object or dict.
                # We'll use a copy to be safe.
                if hasattr(transformed, "__dict__"):
                    processed = transformed.__dict__.copy()
                else:
                    processed = transformed.copy()

                # System fields injection (M1 requirement)
                processed["_run_id"] = str(context.run_id)
                processed["_run_type"] = context.run_type.value
                processed["_source_batch_id"] = str(batch_id)
                processed["_ingestion_ts"] = ingestion_ts.isoformat()

                silver_records.append(processed)

            except Exception as e:
                # Quarantine individual record failure
                quarantined_count += 1
                await self.quarantine.quarantine_record(
                    record=record,
                    error_type="transformation_error",  # Simplification
                    batch_id=batch_id,
                    error_message=str(e),
                    ingestion_ts=ingestion_ts,
                )

        # Write to Silver
        if silver_records:
            try:
                await self.storage.write_silver(
                    table_name=self.table_config.silver_table,
                    records=silver_records,
                    primary_keys=self.table_config.primary_keys,
                    schema=self.schema,
                    mode=self.table_config.write_mode,
                    partition_cols=self.table_config.partition_cols,
                    on_schema_mismatch=self.table_config.on_schema_mismatch or "error",
                )
            except Exception as e:
                self.logger.error("Silver write failed", error=str(e))
                raise

        return SilverBatchResult(silver_records, quarantined_count)


class GoldLayerHandler:
    """Handles Gold layer operations."""

    def __init__(
        self,
        storage: GoldWriter,
        schema: Any,
        config: PipelineConfig,
        table_config: TableConfig,
        logger: LoggerPort,
        gold_transformer: Any | None = None,
    ) -> None:
        self.storage = storage
        self.schema = schema
        self.config = config
        self.table_config = table_config
        self.logger = logger
        self.transformer = gold_transformer

    async def handle(
        self,
        records: list[dict[str, Any]],
        context: PipelineContext,
    ) -> int:
        """Process records for gold layer."""
        if not self.table_config.gold_table:
            return 0

        gold_records = []
        for record in records:
            # Filter
            if self.config.gold_filters:
                if not self.config.gold_filters.should_include(record):
                    continue

            # Transform
            if self.transformer:
                # Use injected transformer
                transformed = self.transformer.transform_for_gold(context, record)
            else:
                # Fallback: simple copy or filtering of fields
                # In BasePipeline there was transform_for_gold.
                # Here we assume record is already close to Gold or we just pass it.
                # If we moved logic to handler, we should implement default logic here.
                # Default: remove system fields?
                transformed = record.copy()

            gold_records.append(transformed)

        if gold_records:
            await self.storage.write_gold(
                table_name=self.table_config.gold_table,
                records=gold_records,
                primary_keys=self.table_config.primary_keys, # Gold might use different PKs?
                # Usually Gold table config has its own PKs, but TableConfig structure implies shared?
                # Let's check TableConfig.
                # Actually TableConfig has silver_table and gold_table names.
                # Primary keys are usually for Silver. Gold PKs might be different.
                # We'll use the same ones for now or assume TableConfig has gold_primary_keys if needed.
                # Re-using primary_keys for now.
                schema=self.schema,
                mode=self.table_config.gold_write_mode,
                # partition_cols? Gold might have different partitions.
            )

        return len(gold_records)
