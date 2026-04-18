"""Validation and policy helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterValidationMixin", "_PreparedSilverWritePayload"]

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.medallion import SilverWriteMode, WriteMode, WriteModePolicy
from bioetl.domain.ports import LoggerPort, MetricsPort, SilverValidatorPort
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _prepare_silver_write_payload_impl,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _check_schema_drift,
    _deduplicate_by_primary_keys_impl,
    _detect_schema_drift,
    _enforce_write_policy,
    _finalize_silver_write_payload,
    _PreparedSilverWritePayload,
    _SilverSchemaPolicyRequest,
    _SilverWritePreparationRequest,
    _sync_validate_and_build_arrow,
    _to_policy_write_mode_impl,
    _validate_key_nullability_impl,
    _validate_records,
    _validate_silver_pandera,
    _validate_write_mode_impl,
    _ValidatedSilverWriteContext,
)


class SilverWriterValidationMixin:
    """Mixin with write policy and schema validation logic."""

    logger: LoggerPort
    _write_policy: WriteModePolicy
    _metrics: MetricsPort | None
    _silver_validator: SilverValidatorPort
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]
    _resolve_table_path: Callable[[str], str]
    _prepare_arrow_data: Callable[..., pa.Table]
    _validate_write_mode: Callable[[str], SilverWriteMode]
    _deduplicate_by_primary_keys: Callable[
        [list[BronzeRecord], list[str]],
        list[BronzeRecord],
    ]
    _to_policy_write_mode: Callable[[SilverWriteMode], WriteMode]
    _validate_key_nullability: Callable[
        [
            list[BronzeRecord],
            list[str],
            list[str] | None,
            list[KeyNullabilityRule] | None,
            str,
        ],
        None,
    ]

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _ValidatedSilverWriteContext:
        """Run synchronous Silver validation steps and build Arrow payload."""
        return _sync_validate_and_build_arrow(self, request)

    def _enforce_write_policy(
        self,
        mode: SilverWriteMode,
        table_name: str,
    ) -> None:
        """Enforce write mode policy for Silver layer."""
        _enforce_write_policy(self, mode, table_name)

    def _validate_records(
        self,
        records: list[BronzeRecord],
        table_name: str,
        schema: pa.Schema,
    ) -> None:
        """Validate records have required metadata fields."""
        _validate_records(self, records, table_name, schema)

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Validate records using Pandera schema before writing to Silver."""
        _validate_silver_pandera(self, records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Check schema drift and handle according to configured policy."""
        await _check_schema_drift(self, table_name, records, on_schema_mismatch)

    async def _detect_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
    ) -> SchemaDriftInfo | None:
        """Detect schema drift between existing table and incoming records."""
        return await _detect_schema_drift(self, table_name, records)

    async def _finalize_silver_write_payload(
        self,
        schema_request: _SilverSchemaPolicyRequest,
    ) -> _PreparedSilverWritePayload:
        """Run schema policy checks and build the final Silver payload."""
        return await _finalize_silver_write_payload(self, schema_request)

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
    ) -> _PreparedSilverWritePayload:
        """Run full validation chain and prepare Arrow data for write."""
        return await _prepare_silver_write_payload_impl(
            self,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            partition_cols=partition_cols,
            key_nullability_rules=key_nullability_rules,
        )


SilverWriterValidationMixin._validate_write_mode = staticmethod(
    _validate_write_mode_impl
)
SilverWriterValidationMixin._deduplicate_by_primary_keys = staticmethod(
    _deduplicate_by_primary_keys_impl
)
SilverWriterValidationMixin._to_policy_write_mode = staticmethod(
    _to_policy_write_mode_impl
)
SilverWriterValidationMixin._validate_key_nullability = staticmethod(
    _validate_key_nullability_impl
)
