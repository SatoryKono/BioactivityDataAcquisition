"""Batch writing facade for Bronze/Silver/Gold layers."""

from __future__ import annotations

__all__ = ["BatchWriter"]

from typing import TYPE_CHECKING, Literal, cast

from bioetl.application.composite.column_orderer import ColumnOrdererService
from bioetl.application.core.batch_writer_columns_mixin import BatchWriterColumnsMixin
from bioetl.application.core.batch_writer_io_mixin import BatchWriterIOMixin
from bioetl.application.core.batch_writer_tracing_mixin import (
    BatchWriterLockValidator,
    BatchWriterTracingMixin,
)
from bioetl.domain.composite.config import DataSchemaConfig

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort, StoragePort, TracingPort


class BatchWriter(BatchWriterIOMixin, BatchWriterColumnsMixin, BatchWriterTracingMixin):
    """Writes records to medallion layers via StoragePort."""

    def __init__(
        self,
        storage: StoragePort,
        context: PipelineContext,
        config: RecordProcessorConfig,
        gold_validator: GoldValidatorPort,
        error_classifier: ErrorClassifier,
        batch_metrics: BatchMetricsRecorderService,
        tracer: TracingPort | None = None,
        lock_validator: BatchWriterLockValidator = None,
        data_schema_config: DataSchemaConfig | None = None,
    ) -> None:
        """Initialize writer dependencies and static write configuration.

        Args:
            storage: Port for writing to Bronze, Silver, and Gold layers.
            context: Pipeline execution context carrying run ID, run type, and logger.
            config: Per-pipeline record processor configuration including schemas and table settings.
            gold_validator: Validator that enforces Gold schema contracts before writes.
            error_classifier: Classifies write exceptions into structured error categories.
            batch_metrics: Metrics recorder for tracking write-layer events and errors.
            tracer: Optional distributed tracing port. If None, tracing is disabled.
            lock_validator: Optional callable that checks whether the distributed lock is
                still held before each write. If None, lock validation is skipped.
            data_schema_config: Optional override for composite data-schema configuration.
                Falls back to ``config.data_schema`` when None.
        """
        self._storage = storage
        self._context = context
        self._config = config
        self._gold_validator = gold_validator
        self._error_classifier = error_classifier
        self._batch_metrics = batch_metrics
        self._tracer = tracer
        self._lock_validator = lock_validator

        self._provider = config.provider
        self._entity_type = config.entity_type
        self._silver_schema = config.silver_schema
        self._table_config = config.table_config
        self._gold_schema = config.gold_schema
        self._column_groups = config.column_groups
        self._data_schema = (
            data_schema_config if data_schema_config is not None else config.data_schema
        )
        self._column_orderer = (
            ColumnOrdererService(
                self._context.logger, column_groups=self._column_groups
            )
            if self._column_groups
            else None
        )

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
