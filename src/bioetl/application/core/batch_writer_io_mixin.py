# mypy: disable-error-code=attr-defined
"""Write-path methods for BatchWriter (bronze/silver/gold)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Literal, cast

import orjson

from bioetl.application.core._batch_writer_gold_support import (
    prepare_gold_records,
    should_defer_gold_validation_to_storage,
    validate_gold_records,
)
from bioetl.application.core.batch_processing_runtime import (
    OPERATION_ERRORS as SHARED_OPERATION_ERRORS,
)
from bioetl.domain.ports.storage import SilverWriteRequest

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriteStorageProtocol
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.domain.config import TableConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import GoldValidatorPort
    from bioetl.domain.types import (
        ArrowSchema,
        BatchID,
        BronzeRecord,
        GoldRecord,
        GoldSchemaPolicyByVersion,
        GoldSchemaType,
    )
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
_WRITE_SPAN_ERRORS = SHARED_OPERATION_ERRORS


class BatchWriterIOMixin:
    """Layer write orchestration extracted from BatchWriter."""

    # Host attributes from BatchWriter MRO (runtime-typed by concrete class).
    _context: PipelineContext
    _storage: BatchWriteStorageProtocol
    _config: RecordProcessorConfig
    _provider = _entity_type = _silver_table_name = _gold_table_name = ""
    _silver_schema: ArrowSchema | None
    _gold_schema: GoldSchemaType
    _gold_schema_policy_by_version: GoldSchemaPolicyByVersion | None
    _gold_validator: GoldValidatorPort
    _table_config: TableConfig
    _silver_mode: Literal["merge", "append", "delete"]
    _gold_mode: Literal["overwrite", "append", "scd2"]
    _validate_lock: Callable[[str], Awaitable[None]]
    _start_span: Callable[..., object | None]
    _end_span: Callable[..., None]
    _collect_record_columns: Callable[[list[GoldRecord]], list[str]]
    _resolve_layer_columns: Callable[
        [Literal["silver", "gold"], Sequence[str]],
        tuple[list[str] | None, dict[str, str]],
    ]
    _project_schema_for_layer: Callable[
        [Literal["silver", "gold"], object, Sequence[str] | None],
        object,
    ]
    _apply_renames_to_records: Callable[
        [list[GoldRecord], dict[str, str]], list[GoldRecord]
    ]
    _get_schema_columns: Callable[[object], set[str] | None]

    def _resolve_gold_ingestion_ts(self) -> datetime:
        """Return the deterministic timestamp anchor for Gold write side effects."""
        replay_timestamp_anchor = self._context.replay_timestamp_anchor
        if replay_timestamp_anchor is not None:
            return replay_timestamp_anchor
        return self._context.started_at

    async def write_bronze(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write deterministic, key-sorted JSONL records to Bronze."""
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
        except BaseException:
            # asyncio.CancelledError (Ba
            self._end_span(span)
            raise

    async def write_silver(
        self,
        records: list[GoldRecord],
        batch_id: BatchID,
        ingestion_ts: datetime,
        bronze_refs: list[BronzeWriteResult] | None = None,
    ) -> SilverWriteResult | None:
        """Write transformed records and explicit provenance to Silver."""
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

            request = SilverWriteRequest(
                table_name=self._silver_table_name,
                records=records,
                primary_keys=list(self._table_config.primary_keys),
                schema=cast("ArrowSchema", silver_schema),
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
            silver_result = await self._storage.write_silver(request)
            self._end_span(span)
            persisted_silver_result: SilverWriteResult | None = silver_result
            return persisted_silver_result
        except _WRITE_SPAN_ERRORS as error:
            self._end_span(span, error)
            raise
        except BaseException:
            self._end_span(span)
            raise

    async def write_gold(
        self,
        records: list[GoldRecord],
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Validate and write schema-projected records to Gold."""
        await self._validate_lock("write_gold")
        span = self._start_span("write_gold", "gold", len(records))

        try:
            if should_defer_gold_validation_to_storage(self):
                available_cols = self._collect_record_columns(records)
                schema_payload: object = self._gold_schema_policy_by_version
            else:
                records, available_cols = prepare_gold_records(self, records)
                validate_gold_records(self, records)
                column_order_preview, _rename_preview = self._resolve_layer_columns(
                    "gold", available_cols
                )
                schema_payload = self._project_schema_for_layer(
                    "gold",
                    self._gold_schema,
                    column_order_preview,
                )
                # Re-project/validate ag
                if (
                    schema_payload is not None
                    and schema_payload is not self._gold_schema
                ):
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
        except BaseException:
            self._end_span(span)
            raise

    def _prepare_gold_records(
        self,
        records: list[GoldRecord],
        *,
        schema: object | None = None,
    ) -> tuple[list[GoldRecord], list[str]]:
        """Project records to schema and compute available columns."""
        return prepare_gold_records(self, records, schema=schema)
