# mypy: disable-error-code=attr-defined
"""Write-path methods for BatchWriter (bronze/silver/gold)."""

from __future__ import annotations

from datetime import datetime
from inspect import signature
from typing import TYPE_CHECKING
from unittest.mock import Mock

import orjson

from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS
from bioetl.domain.exceptions import SchemaViolationError

if TYPE_CHECKING:
    from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


_WRITE_SPAN_ERRORS = OPERATION_ERRORS


class BatchWriterIOMixin:
    """Layer write orchestration extracted from BatchWriter."""

    def _resolve_gold_ingestion_ts(self) -> datetime:
        """Return the deterministic timestamp anchor for Gold write side effects."""
        replay_timestamp_anchor = getattr(
            self._context, "replay_timestamp_anchor", None
        )
        return (
            replay_timestamp_anchor
            if replay_timestamp_anchor is not None
            else self._context.started_at
        )

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
            if self._should_defer_gold_validation_to_storage():
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
                records, available_cols = self._prepare_gold_records(
                    records,
                    schema=schema_payload,
                )
                self._validate_gold_records(records, schema=schema_payload)

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
        target_schema = schema if schema is not None else self._gold_schema
        schema_columns = self._get_schema_columns(target_schema)
        if not schema_columns:
            return records, self._collect_record_columns(records)

        dq_defaults = {"_dq_warn": False, "_dq_error": False}
        projected = [
            {
                key: record.get(key, dq_defaults.get(key))
                for key in schema_columns
                if key in record or key in dq_defaults
            }
            for record in records
        ]
        return projected, list(schema_columns)

    def _validate_gold_records(
        self,
        records: list[GoldRecord],
        *,
        schema: object | None = None,
    ) -> None:
        """Validate Gold records against schema contract."""
        validator = self._gold_validator
        target_schema = schema if schema is not None else self._gold_schema
        if schema is not None and hasattr(target_schema, "columns"):
            validator = self._rebind_gold_validator_schema(validator, target_schema)

        result = validator.validate(records)
        if not result.valid:
            debug_export_service = getattr(self, "_debug_export_service", None)
            if debug_export_service is not None:
                debug_export_service.record_gold_validation_failure(
                    records=records,
                    errors=result.errors,
                )
            raise SchemaViolationError("gold", result.errors)

    def _rebind_gold_validator_schema(
        self,
        validator: object,
        schema: object,
    ) -> object:
        """Clone schema-aware validators for projected Gold schemas when supported."""
        if isinstance(validator, Mock):
            return validator

        validator_cls = type(validator)
        try:
            init_params = signature(validator_cls).parameters
        except (TypeError, ValueError):
            return validator

        if "schema" not in init_params:
            return validator

        validator_kwargs: dict[str, object] = {"schema": schema}
        if "strict" in init_params:
            validator_kwargs["strict"] = getattr(validator, "_strict", True)

        dq_config = getattr(validator, "_dq_config", None)
        if "dq_config" in init_params and dq_config is not None:
            validator_kwargs["dq_config"] = dq_config

        try:
            return validator_cls(**validator_kwargs)
        except TypeError:
            return validator

    def _should_defer_gold_validation_to_storage(self) -> bool:
        """Whether Gold validation/projection must happen per-version in storage."""
        policy = getattr(self, "_gold_schema_policy_by_version", None)
        return bool(policy is not None and policy.is_multi_version)
