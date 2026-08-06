"""Batch writing facade for Bronze/Silver/Gold layers."""

from __future__ import annotations

__all__ = ["BatchWriter"]

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol, cast

from bioetl.application.core.batch_writer_columns_mixin import BatchWriterColumnsMixin
from bioetl.application.core.batch_writer_io_mixin import BatchWriterIOMixin
from bioetl.application.core.batch_writer_tracing_mixin import (
    BatchWriterLockValidator,
    BatchWriterTracingMixin,
)
from bioetl.domain.composite import DataSchemaConfig

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bioetl.application.composite.column_service import ColumnOrderService
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.application.services.export_lineage.debug_export_service import (
        DebugExportService,
    )
    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import GoldValidatorPort, TracingPort
    from bioetl.domain.types import (
        ArrowSchema,
        BatchID,
        BronzeRecord,
        GoldRecord,
        RunID,
        RunType,
        ScdConfig,
    )
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


class BatchWriteStorageProtocol(Protocol):
    """Minimal write-only storage contract for BatchWriter."""

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
        """Persist one Bronze batch and return write metadata."""
        ...

    async def write_silver(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
        key_nullability_rules: list[KeyNullabilityRule] | None = None,
    ) -> SilverWriteResult | None:
        """Persist transformed records into Silver storage."""
        ...

    async def write_gold(
        self,
        table_name: str,
        records: list[GoldRecord],
        schema: object,
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        scd_config: ScdConfig | None = None,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[object] | None = None,
    ) -> None:
        """Persist validated records into Gold storage."""
        ...


@dataclass(frozen=True, slots=True)
class BatchWriterOptions:
    """Optional writer collaborators grouped to reduce constructor width."""

    tracer: TracingPort | None = None
    lock_validator: BatchWriterLockValidator | None = None
    data_schema_config: DataSchemaConfig | None = None
    column_orderer: ColumnOrderService | None = None
    debug_export_service: DebugExportService | None = None


class BatchWriter(BatchWriterTracingMixin, BatchWriterColumnsMixin, BatchWriterIOMixin):
    """Writes records to medallion layers via narrow write-only port.
    MRO order: tracing/columns collaborators before IO write methods so
    cross-mixin helpers resolve to real implementations.
    """

    def __init__(
        self,
        storage: BatchWriteStorageProtocol,
        context: PipelineContext,
        config: RecordProcessorConfig,
        gold_validator: GoldValidatorPort,
        error_classifier: ErrorClassifier,
        batch_metrics: BatchMetricsRecorderService,
        options: BatchWriterOptions | None = None,
    ) -> None:
        """Initialize writer dependencies and static write configuration.
        Args:
            storage: Write-only storage port for Bronze, Silver, and Gold layers.
            context: Pipeline execution context carrying run ID, run type, and logger.
            config: Per-pipeline record processor configuration including schemas and table settings.
            gold_validator: Validator that enforces Gold schema contracts before writes.
            error_classifier: Classifies write exceptions into structured error categories.
            batch_metrics: Metrics recorder for tracking write-layer events and errors.
            options: Optional grouped collaborators (tracer, lock validator, schema/column helpers).
        """
        self._storage = storage
        self._context = context
        self._config = config
        self._gold_validator = gold_validator
        self._error_classifier = error_classifier
        opts = options or BatchWriterOptions()
        self._batch_metrics = batch_metrics
        self._tracer = opts.tracer
        self._lock_validator = opts.lock_validator
        self._debug_export_service = opts.debug_export_service
        self._provider = config.provider
        self._entity_type = config.entity_type
        self._silver_schema = config.silver_schema
        self._table_config = config.table_config
        self._gold_schema = config.gold_schema
        self._gold_schema_policy_by_version = config.gold_schema_policy_by_version
        self._column_groups = config.column_groups
        self._data_schema = (
            opts.data_schema_config
            if opts.data_schema_config is not None
            else config.data_schema
        )
        self._column_orderer = opts.column_orderer
        self._silver_table_name = (
            self._table_config.silver_table or f"{self._provider}.{self._entity_type}"
        )
        self._gold_table_name = (
            self._table_config.gold_table or f"{self._provider}.{self._entity_type}"
        )
        silver_mode_val = self._table_config.silver_write_mode
        self._silver_mode = cast(
            Literal["merge", "append", "delete"],
            silver_mode_val.value
            if hasattr(silver_mode_val, "value")
            else silver_mode_val,
        )
        gold_mode_val = self._table_config.gold_write_mode
        self._gold_mode = cast(
            Literal["overwrite", "append", "scd2"],
            gold_mode_val.value if hasattr(gold_mode_val, "value") else gold_mode_val,
        )

    def track_batch_written(self, *, stage: str, count: int) -> None:
        """Public metrics hook for successful layer writes."""
        self._batch_metrics.track_batch_written(stage=stage, count=count)

    def track_batch_failed(self, *, stage: str, count: int) -> None:
        """Public metrics hook for failed layer writes."""
        self._batch_metrics.track_batch_failed(stage=stage, count=count)
