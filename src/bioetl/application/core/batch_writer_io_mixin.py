# mypy: disable-error-code=attr-defined
"""Write-path methods for BatchWriter (bronze/silver/gold)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

import orjson

from bioetl.application.core._batch_writer_gold_support import (
    prepare_gold_records,
    should_defer_gold_validation_to_storage,
    validate_gold_records,
)
from bioetl.application.core.batch_processing_runtime import (
    OPERATION_ERRORS as SHARED_OPERATION_ERRORS,
)

if TYPE_CHECKING:
    from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
_WRITE_SPAN_ERRORS = SHARED_OPERATION_ERRORS


class BatchWriterIOMixin:
    """Layer write orchestration extracted from BatchWriter."""

    # Host attributes from BatchWriter + sibling mixins (PD3 structural host; Any:
    # concrete MRO supplies runtime types without NotImplementedError stubs).
    _context: Any = cast(Any, None)  # Any: BatchWriter MRO host attribute
    _storage: Any = cast(Any, None)  # Any: BatchWriter MRO host attribute
    _config: Any = cast(Any, None)  # Any: BatchWriter MRO host attribute
    _provider: str = ""
    _entity_type: str = ""
    _silver_schema: Any = cast(Any, None)  # Any: provider-specific schema type
    _gold_schema: Any = cast(Any, None)  # Any: provider-specific schema type
    _gold_schema_policy_by_version: Any = cast(Any, None)  # Any: schema policy host
    _gold_validator: Any = cast(Any, None)  # Any: provider-specific validator
    _silver_table_name: str = ""
    _gold_table_name: str = ""
    _table_config: Any = cast(Any, None)  # Any: BatchWriter MRO host attribute
    _silver_mode: Any = cast(Any, None)  # Any: storage-specific write mode
    _gold_mode: Any = cast(Any, None)  # Any: storage-specific write mode
    _validate_lock: Any = cast(Any, None)  # Any: sibling mixin host method
    _start_span: Any = cast(Any, None)  # Any: sibling mixin host method
    _end_span: Any = cast(Any, None)  # Any: sibling mixin host method
    _collect_record_columns: Any = cast(Any, None)  # Any: sibling mixin host method
    _resolve_layer_columns: Any = cast(Any, None)  # Any: sibling mixin host method
    _project_schema_for_layer: Any = cast(Any, None)  # Any: sibling mixin host method
    _apply_renames_to_records: Any = cast(Any, None)  # Any: sibling mixin host method
    _get_schema_columns: Any = cast(Any, None)  # Any: sibling mixin host method

    def _resolve_gold_ingestion_ts(self) -> datetime:
        """Return the deterministic timestamp anchor for Gold write side effects."""
        replay_timestamp_anchor = getattr(
            self._context, "replay_timestamp_anchor", None
        )
        if replay_timestamp_anchor is not None:
            return cast(datetime, replay_timestamp_anchor)
        return cast(datetime, self._context.started_at)

    async def write_bronze(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        ingestion_ts: datetime,
        source_metadata: object | None = None,
    ) -> BronzeWriteResult:
        """Write deterministic JSONL batch to Bronze.

        Args:
            records: Raw Bronze records to be serialized and written.
            batch_id: Unique identifier for this batch, used for deterministic naming.
            ingestion_ts: Timestamp marking when the batch was ingested.
            source_metadata: Optional provider-specific metadata to attach to the batch.

        Returns:
            BronzeWriteResult with path and record count for the written batch.
        """
        await self._validate_lock("write_bronze")
        span = self._start_span("write_bronze", "bronze", len(records), batch_id)
        try:
            json_bytes_list = [
                orjson.dumps(r, option=orjson.OPT_SORT_KEYS) for r in records
            ]
            json_bytes_list.sort()
            record_bytes = (b + b"\n" for b in json_bytes_list)
            bronze_result = await self._storage.write_bronze(
                records=record_bytes,
                provider=self._provider,
                entity=self._entity_type,
                date=ingestion_ts,
                batch_id=batch_id,
                run_id=self._context.run_id,
                run_type=self._context.run_type,
                ingestion_ts=ingestion_ts,
                source_metadata=source_metadata,
            )
            self._end_span(span)
            persisted_bronze_result: BronzeWriteResult = bronze_result
            return persisted_bronze_result
        except _WRITE_SPAN_ERRORS as error:
            self._end_span(span, error)
            raise

    async def write_silver(
        self,
        records: list[GoldRecord],
        batch_id: BatchID,
        ingestion_ts: datetime,
        bronze_refs: list[BronzeWriteResult] | None = None,
    ) -> SilverWriteResult | None:
        """Write transformed records to Silver with metadata enrichment.

        Args:
            records: Transformed records ready for Silver layer storage.
            batch_id: Batch identifier forwarded as explicit write provenance.
            ingestion_ts: Ingestion timestamp forwarded to storage/audit metadata.
            bronze_refs: Optional Bronze write results used for lineage linking.

        Returns:
            SilverWriteResult with Delta table version and row counts, or None if skipped.
        """
        await self._validate_lock("write_silver")
        span = self._start_span("write_silver", "silver", len(records), batch_id)

        try:
            silver_schema = self._silver_schema
            available_cols = (
                list(silver_schema.names)
                if silver_schema is not None
                else self._collect_record_columns(records)
            )
            column_order, rename_map = self._resolve_layer_columns(
                "silver", available_cols
            )
            silver_schema = self._project_schema_for_layer(
                "silver", silver_schema, column_order
            )
            if rename_map:
                records = self._apply_renames_to_records(records, rename_map)

            silver_result = await self._storage.write_silver(
                table_name=self._silver_table_name,
                records=records,
                primary_keys=list(self._table_config.primary_keys),
                schema=silver_schema,
                mode=self._silver_mode,
                partition_cols=list(self._table_config.partition_cols),
                on_schema_mismatch=self._table_config.on_schema_mismatch,
                column_order=column_order,
                bronze_refs=bronze_refs,
                key_nullability_rules=(
                    list(self._config.dq_config.key_nullability_rules)
                    if self._config.dq_config is not None
                    else None
                ),
                run_id=self._context.run_id,
                run_type=self._context.run_type,
                source_batch_id=batch_id,
                ingestion_ts=ingestion_ts,
            )
            self._end_span(span)
            persisted_silver_result: SilverWriteResult | None = silver_result
            return persisted_silver_result
        except _WRITE_SPAN_ERRORS as error:
            self._end_span(span, error)
            raise

    async def write_gold(
        self,
        records: list[GoldRecord],
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Write validated records to Gold.

        Args:
            records: Validated Gold-layer records projected to schema columns.
            silver_refs: Optional Silver write results used for lineage linking.
        """
        await self._validate_lock("write_gold")
        span = self._start_span("write_gold", "gold", len(records))

        try:
            schema_payload: object = self._gold_schema
            if should_defer_gold_validation_to_storage(self):
                available_cols = self._collect_record_columns(records)
                schema_payload = self._gold_schema_policy_by_version
            else:
                available_cols = list(
                    self._get_schema_columns(self._gold_schema) or ()
                ) or self._collect_record_columns(records)
                column_order, rename_map = self._resolve_layer_columns(
                    "gold", available_cols
                )
                schema_payload = self._project_schema_for_layer(
                    "gold",
                    self._gold_schema,
                    column_order,
                )
                records, available_cols = prepare_gold_records(
                    self,
                    records,
                    schema=schema_payload,
                )
                validate_gold_records(self, records, schema=schema_payload)

            column_order, rename_map = self._resolve_layer_columns(
                "gold", available_cols
            )
            if rename_map:
                records = self._apply_renames_to_records(records, rename_map)

            await self._storage.write_gold(
                table_name=self._gold_table_name,
                records=records,
                schema=schema_payload,
                primary_keys=list(self._table_config.primary_keys),
                mode=self._gold_mode,
                scd_config=self._config.scd_config,
                column_order=column_order,
                ingestion_ts=self._resolve_gold_ingestion_ts(),
                run_id=self._context.run_id,
                silver_refs=silver_refs,
            )
            self._end_span(span)
        except _WRITE_SPAN_ERRORS as error:
            self._end_span(span, error)
            raise

    def _prepare_gold_records(
        self,
        records: list[GoldRecord],
        *,
        schema: object | None = None,
    ) -> tuple[list[GoldRecord], list[str]]:
        """Project records to schema and compute available columns."""
        return prepare_gold_records(self, records, schema=schema)

    def _validate_gold_records(
        self,
        records: list[GoldRecord],
        *,
        schema: object | None = None,
    ) -> None:
        """Validate Gold records against schema contract."""
        validate_gold_records(self, records, schema=schema)
