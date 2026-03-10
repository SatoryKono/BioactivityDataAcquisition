"""Validation and policy helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterValidationMixin"]

import asyncio
from collections.abc import Awaitable, Callable
from functools import partial
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa

from bioetl.domain.exceptions import (
    PolicyViolationError,
    SchemaEvolutionError,
    SchemaViolationError,
)
from bioetl.domain.medallion import Layer, SilverWriteMode, WriteMode

if TYPE_CHECKING:
    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.medallion import WriteModePolicy
    from bioetl.domain.ports import LoggerPort, MetricsPort, SilverValidatorPort
    from bioetl.domain.types import BronzeRecord
    from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo


def _sync_validate_and_build_arrow(
    mixin: SilverWriterValidationMixin,
    *,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str],
    schema: pa.Schema,
    mode: str,
    column_order: list[str] | None,
    partition_cols: list[str] | None,
    key_nullability_rules: list[KeyNullabilityRule] | None,
) -> tuple[list[BronzeRecord], SilverWriteMode, pa.Table]:
    """Run synchronous Silver validation steps and build Arrow payload."""
    records = mixin._deduplicate_by_primary_keys(records, primary_keys)
    validated_mode = mixin._validate_write_mode(mode)
    mixin._enforce_write_policy(validated_mode, table_name)
    mixin._validate_records(records, table_name, schema)
    mixin._validate_key_nullability(
        records,
        primary_keys,
        partition_cols,
        key_nullability_rules,
        table_name,
    )
    mixin._validate_silver_pandera(records, table_name)
    arrow_data = mixin._prepare_arrow_data(
        records,
        schema,
        primary_keys,
        column_order=column_order,
    )
    return records, validated_mode, arrow_data


class SilverWriterValidationMixin:
    """Mixin with write policy and schema validation logic."""

    logger: LoggerPort
    _write_policy: WriteModePolicy
    _metrics: MetricsPort | None
    _silver_validator: SilverValidatorPort
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]
    _resolve_table_path: Callable[[str], str]
    _prepare_arrow_data: Callable[..., pa.Table]

    def _validate_write_mode(self, mode: str) -> SilverWriteMode:
        """Validate and convert write mode string to enum."""
        try:
            return SilverWriteMode(mode)
        except ValueError:
            valid_modes = [item.value for item in SilverWriteMode]
            raise ValueError(
                f"Invalid Silver write mode '{mode}'. Allowed: {valid_modes}"
            ) from None

    def _deduplicate_by_primary_keys(
        self,
        records: list[BronzeRecord],
        primary_keys: list[str],
    ) -> list[BronzeRecord]:
        """Deduplicate records based on primary keys in the current batch."""
        if not primary_keys or not records:
            return records

        unique_records: dict[tuple[Any, ...], BronzeRecord] = {}
        for record in records:
            key = tuple(record.get(primary_key) for primary_key in primary_keys)
            unique_records[key] = record
        return list(unique_records.values())

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        """Map SilverWriteMode to WriteMode for policy validation."""
        mapping = {
            SilverWriteMode.MERGE: WriteMode.MERGE,
            SilverWriteMode.APPEND: WriteMode.APPEND,
            SilverWriteMode.DELETE: WriteMode.OVERWRITE,
        }
        return mapping[mode]

    def _enforce_write_policy(
        self,
        mode: SilverWriteMode,
        table_name: str,
    ) -> None:
        """Enforce write mode policy for Silver layer."""
        policy_mode = self._to_policy_write_mode(mode)
        try:
            self._write_policy.validate(Layer.SILVER, policy_mode)
        except PolicyViolationError:
            self.logger.error(
                "Write mode policy violation",
                layer="silver",
                mode=mode.value,
                policy_mode=policy_mode.value,
                table=table_name,
            )
            if self._metrics:
                self._metrics.increment_counter(
                    "policy_violations_total",
                    1,
                    {"layer": "silver", "mode": policy_mode.value},
                )
            raise

    def _validate_records(
        self,
        records: list[BronzeRecord],
        table_name: str,
        schema: pa.Schema,
    ) -> None:
        """Validate records have required metadata fields."""
        if not records:
            raise ValueError("No records to write")

        required_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        if missing_fields := required_fields - set(records[0].keys()):
            raise ValueError(
                f"Records missing required metadata fields: {missing_fields}"
            )

        if self.logger:
            keys = set(records[0].keys())
            optional_missing = [key for key in schema.names if key not in keys]
            if optional_missing:
                self.logger.debug(
                    "Optional fields missing in batch",
                    table=table_name,
                    missing=optional_missing,
                )

    def _validate_key_nullability(
        self,
        records: list[BronzeRecord],
        primary_keys: list[str],
        partition_cols: list[str] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
        table_name: str,
    ) -> None:
        """Validate nullability policy for merge and partition keys."""
        if not records or not key_nullability_rules:
            return

        rules = {(rule.field, rule.key_type): rule for rule in key_nullability_rules}

        def collect_violations(
            field: str, key_type: Literal["merge", "partition"]
        ) -> int:
            """Count null values for a non-nullable key field."""
            rule = rules.get((field, key_type))
            if rule is None or rule.nullable:
                return 0
            return sum(1 for record in records if record.get(field) is None)

        violations: list[tuple[str, str, int]] = []

        for key in primary_keys:
            if count := collect_violations(key, "merge"):
                violations.append((key, "merge", count))

        for key in partition_cols or []:
            if count := collect_violations(key, "partition"):
                violations.append((key, "partition", count))

        if violations:
            details = [
                f"{key_type}:{field} null_count={count}"
                for field, key_type, count in violations
            ]
            raise ValueError(
                "Key nullability policy violation for table "
                f"'{table_name}': {'; '.join(details)}"
            )

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Validate records using Pandera schema before writing to Silver."""
        cleaned_records = [
            {key: value for key, value in record.items() if key != "_state"}
            for record in records
        ]

        result = self._silver_validator.validate(cleaned_records)
        if not result.valid:
            self.logger.error(
                "Silver Pandera validation failed",
                table=table_name,
                errors=result.errors,
            )
            if self._metrics:
                self._metrics.increment_counter(
                    "silver_validation_failures_total",
                    1,
                    {"table": table_name},
                )
            raise SchemaViolationError(table_name, result.errors)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Check schema drift and handle according to configured policy."""
        existing_schema = await self._get_table_schema(table_name)
        if existing_schema is None or not records:
            return

        incoming_fields = set(records[0].keys())
        existing_fields = set(existing_schema.names)

        new_fields = incoming_fields - existing_fields
        removed_fields = existing_fields - incoming_fields

        if not new_fields and not removed_fields:
            return

        self.logger.warning(
            "Schema drift detected",
            table=table_name,
            new_fields=sorted(new_fields) if new_fields else None,
            removed_fields=sorted(removed_fields) if removed_fields else None,
            action=on_schema_mismatch,
        )

        if on_schema_mismatch == "error":
            raise SchemaEvolutionError(
                table=table_name,
                new_fields=new_fields,
                removed_fields=removed_fields,
            )

    async def _detect_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
    ) -> SchemaDriftInfo | None:
        """Detect schema drift between existing table and incoming records."""
        from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo

        existing_schema = await self._get_table_schema(table_name)
        if existing_schema is None or not records:
            return None

        incoming_fields = set(records[0].keys())
        existing_fields = set(existing_schema.names)

        new_fields = incoming_fields - existing_fields
        missing_fields = existing_fields - incoming_fields

        if not new_fields and not missing_fields:
            return None

        critical_missing = [
            field for field in missing_fields if not field.startswith("_")
        ]
        status: Literal["info", "warn", "critical"]
        if critical_missing:
            status = "critical"
        elif len(new_fields) > 3:
            status = "warn"
        else:
            status = "info"

        return SchemaDriftInfo(
            status=status,
            new_fields=tuple(sorted(new_fields)),
            missing_fields=tuple(sorted(missing_fields)),
        )

    async def _prepare_silver_write_payload(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        column_order: list[str] | None,
        partition_cols: list[str] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
    ) -> tuple[list[BronzeRecord], SilverWriteMode, str, pa.Table]:
        """Run full validation chain and prepare Arrow data for write."""
        loop = asyncio.get_running_loop()
        records, validated_mode, arrow_data = await loop.run_in_executor(
            None,
            partial(
                _sync_validate_and_build_arrow,
                mixin=self,
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                schema=schema,
                mode=mode,
                column_order=column_order,
                partition_cols=partition_cols,
                key_nullability_rules=key_nullability_rules,
            ),
        )
        await self._check_schema_drift(table_name, records, on_schema_mismatch)
        table_path = self._resolve_table_path(table_name)
        return records, validated_mode, table_path, arrow_data
