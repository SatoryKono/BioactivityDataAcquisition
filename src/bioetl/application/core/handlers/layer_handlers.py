"""Layer Handlers for RecordProcessor.

Decomposes the logic for preparing and handling records for each layer (Bronze, Silver, Gold).
Adheres to SRP by separating preparation logic from orchestration/writing.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, TypeVar

from bioetl.domain.exceptions import SchemaViolationError

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.application.core.batch_metrics import BatchMetricsRecorder
    from bioetl.application.core.protocols import GoldFilterCallback, TransformCallback
    from bioetl.application.core.quarantine_manager import QuarantineManager
    from bioetl.domain.config import TableConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort
    from bioetl.domain.types import BatchID

# Define generic types for strict typing later
T_Bronze = TypeVar("T_Bronze", bound=dict[str, Any])
T_Silver = TypeVar("T_Silver", bound=dict[str, Any])
T_Gold = TypeVar("T_Gold", bound=dict[str, Any])


class BronzeLayerHandler:
    """Handles preparation of records for Bronze layer."""

    def prepare_batch(
        self, records: list[dict[str, Any]]
    ) -> tuple[int, list[bytes]]:
        """Serialize and sort records for deterministic Bronze storage.

        Args:
            records: Raw records.

        Returns:
            Tuple of (count, list of serialized bytes).
        """
        if not records:
            return 0, []

        # 1. Serialize all records to JSON strings with deterministic key ordering
        json_strings = [json.dumps(r, sort_keys=True) for r in records]

        # 2. Sort the JSON strings to ensure deterministic file content
        json_strings.sort()

        # 3. Encode to bytes
        record_bytes = [(s + "\n").encode("utf-8") for s in json_strings]

        return len(records), record_bytes


class SilverLayerHandler:
    """Handles transformation and metadata enrichment for Silver layer."""

    def __init__(
        self,
        transform_callback: TransformCallback,
        table_config: TableConfig,
        quarantine_manager: QuarantineManager,
        error_classifier: ErrorClassifier,
        metrics: BatchMetricsRecorder,
    ):
        self._transform = transform_callback
        self._table_config = table_config
        self._quarantine_manager = quarantine_manager
        self._error_classifier = error_classifier
        self._metrics = metrics

    async def prepare_batch(
        self,
        context: PipelineContext,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        ingestion_ts: datetime,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """Transform records and add metadata.

        Args:
            context: Pipeline context.
            records: Raw records to transform.
            batch_id: Batch ID.
            ingestion_ts: Ingestion timestamp.

        Returns:
            Tuple of:
            - List of transformed records (clean, for Gold processing)
            - List of enriched records (with metadata, for Silver storage)
            - Number of quarantined records
        """
        clean_records: list[dict[str, Any]] = []
        enriched_records: list[dict[str, Any]] = []
        quarantined_count = 0

        for raw_record in records:
            # Create a child context for the record (for logging)
            record_context = context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),  # Fallback ID logging
            )

            try:
                # Execute transformation callback
                transformed = await self._transform(record_context, raw_record)

                if transformed:
                    clean_records.append(transformed)
                    # Create a copy for Silver enrichment to avoid polluting Gold input
                    enriched = transformed.copy()
                    enriched["_run_id"] = str(context.run_id)
                    enriched["_run_type"] = context.run_type.value
                    enriched["_source_batch_id"] = str(batch_id)
                    enriched["_ingestion_ts"] = ingestion_ts.isoformat()
                    enriched_records.append(enriched)
            except Exception as e:
                error_type = self._error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self._quarantine_manager.quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    quarantined_count += 1
                    self._metrics.track_error("transform", error_type)
                else:
                    raise

        return clean_records, enriched_records, quarantined_count

    def get_write_mode(self) -> str:
        """Get effective write mode (handling overwrite->append logic)."""
        mode = self._table_config.silver_write_mode
        # For "overwrite" mode, use "append" for batch writes since table is cleared at run start
        if mode == "overwrite":
            return "append"
        return mode


class GoldLayerHandler:
    """Handles validation and filtering for Gold layer."""

    def __init__(
        self,
        validator: GoldValidatorPort,
        filter_callback: GoldFilterCallback,
        table_config: TableConfig,
    ):
        self._validator = validator
        self._filter = filter_callback
        self._table_config = table_config

    def prepare_batch(
        self,
        context: PipelineContext,
        silver_records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> list[dict[str, Any]]:
        """Filter and validate Silver records for Gold layer.

        Args:
            context: Pipeline context.
            silver_records: Transformed Silver records.
            batch_id: Batch ID (for logging).

        Returns:
            List of validated Gold records.
        """
        if not silver_records:
            return []

        # 1. Filter
        gold_candidates = []
        for record in silver_records:
             # Bind context for logging inside filter if needed
            record_context = context.bind_logger(batch_id=str(batch_id))
            if self._filter(record_context, record):
                gold_candidates.append(record)

        if not gold_candidates:
            return []

        # 2. Validate using dedicated validator (SRP)
        result = self._validator.validate(gold_candidates)
        if not result.valid:
            # Raise typed exception for handling upstream
            raise SchemaViolationError("gold", result.errors)

        return gold_candidates

    def get_write_mode(self) -> str:
        """Get effective write mode."""
        mode = self._table_config.gold_write_mode
        if mode == "overwrite":
            return "append"
        return mode
