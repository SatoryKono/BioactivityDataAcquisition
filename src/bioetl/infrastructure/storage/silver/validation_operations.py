"""Validation operations extracted from ``SilverWriterValidationMixin``."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

import pyarrow as pa

from bioetl.domain.exceptions import (
    PolicyViolationError,
    SchemaViolationError,
)
from bioetl.domain.medallion import Layer, SilverWriteMode, WriteMode
from bioetl.infrastructure.storage.silver.key_nullability_operations import (
    _collect_key_violations as _collect_key_violations,
)
from bioetl.infrastructure.storage.silver.key_nullability_operations import (
    _count_null_violations as _count_null_violations,
)
from bioetl.infrastructure.storage.silver.key_nullability_operations import (
    _validate_key_nullability_impl as _validate_key_nullability_impl,
)
from bioetl.infrastructure.storage.silver.schema_drift_operations import (
    _build_schema_drift_info,
    _build_silver_schema_drift_diff,
    _check_schema_drift,
    _detect_schema_drift,
)

if TYPE_CHECKING:
    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.medallion import WriteModePolicy
    from bioetl.domain.ports import LoggerPort, MetricsPort, SilverValidatorPort
    from bioetl.domain.types import BronzeRecord

__all__ = [
    "_PreparedSilverWritePayload",
    "_SilverSchemaPolicyRequest",
    "_SilverWritePreparationRequest",
    "_ValidatedSilverWriteContext",
    "_build_schema_drift_info",
    "_build_silver_schema_drift_diff",
    "_check_schema_drift",
    "_deduplicate_by_primary_keys_impl",
    "_detect_schema_drift",
    "_enforce_write_policy",
    "_finalize_silver_write_payload",
    "_sync_validate_and_build_arrow",
    "_to_policy_write_mode_impl",
    "_validate_key_nullability_impl",
    "_validate_records",
    "_validate_silver_pandera",
    "_validate_write_mode_impl",
]  # NOTE: _check_schema_drift, _detect_schema_drift, _build_* re-exported from schema_drift_operations

_VERSIONED_TABLE_SUFFIX_RE = re.compile(r"__v\d+_\d+_\d+$")


@dataclass(frozen=True, slots=True)
class _PreparedSilverWritePayload:
    """Validated write payload produced before Delta write execution."""

    records: list[BronzeRecord]
    validated_mode: SilverWriteMode
    table_path: str
    arrow_data: pa.Table
    schema_mode: str | None
    merge_schema: bool


@dataclass(frozen=True, slots=True)
class _ValidatedSilverWriteContext:
    """Validated pre-write state before path resolution and Delta dispatch."""

    records: list[BronzeRecord]
    validated_mode: SilverWriteMode
    arrow_data: pa.Table


@dataclass(frozen=True, slots=True)
class _SilverSchemaPolicyRequest:
    """Schema drift policy input after synchronous validation completes."""

    table_name: str
    records: list[BronzeRecord]
    on_schema_mismatch: Literal["error", "evolve", "ignore"]
    validated_mode: SilverWriteMode
    arrow_data: pa.Table


@dataclass(frozen=True, slots=True)
class _SilverWritePreparationRequest:
    """Normalized request payload for Silver validation and Arrow preparation."""

    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    schema: pa.Schema
    mode: str
    column_order: list[str] | None
    partition_cols: list[str] | None
    key_nullability_rules: list[KeyNullabilityRule] | None


class _SilverWriterValidationHostProtocol(Protocol):
    """Typed host contract for validation and schema-drift helpers."""

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

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None: ...


def _pipeline_name_from_table_name(table_name: str) -> str:
    """Derive the canonical pipeline label from a logical or versioned table name."""
    normalized_table = _VERSIONED_TABLE_SUFFIX_RE.sub("", table_name.strip())
    return normalized_table.replace(".", "_").replace("/", "_")


def _validate_write_mode_impl(mode: str) -> SilverWriteMode:
    """Validate and convert write mode string to enum."""
    try:
        return SilverWriteMode(mode)
    except ValueError:
        valid_modes = [item.value for item in SilverWriteMode]
        raise ValueError(
            f"Invalid Silver write mode '{mode}'. Allowed: {valid_modes}"
        ) from None


def _deduplicate_by_primary_keys_impl(
    records: list[BronzeRecord],
    primary_keys: list[str],
) -> list[BronzeRecord]:
    """Deduplicate records based on primary keys in the current batch."""
    if not primary_keys or not records:
        return records

    # Any: primary key values are heterogeneous (str | int | None)
    unique_records: dict[tuple[Any, ...], BronzeRecord] = {}
    for record in records:
        key = tuple(record.get(primary_key) for primary_key in primary_keys)
        unique_records[key] = record
    return list(unique_records.values())


def _to_policy_write_mode_impl(mode: SilverWriteMode) -> WriteMode:
    """Map SilverWriteMode to WriteMode for policy validation."""
    mapping = {
        SilverWriteMode.MERGE: WriteMode.MERGE,
        SilverWriteMode.APPEND: WriteMode.APPEND,
        SilverWriteMode.DELETE: WriteMode.OVERWRITE,
    }
    return mapping[mode]


def _build_prepared_silver_write_payload(
    *,
    table_path: str,
    schema_request: _SilverSchemaPolicyRequest,
) -> _PreparedSilverWritePayload:
    """Build the final Silver write payload after schema policy checks."""
    return _PreparedSilverWritePayload(
        records=schema_request.records,
        validated_mode=schema_request.validated_mode,
        table_path=table_path,
        arrow_data=schema_request.arrow_data,
        schema_mode=(
            "merge"
            if (
                schema_request.on_schema_mismatch == "evolve"
                and schema_request.validated_mode == SilverWriteMode.APPEND
            )
            else None
        ),
        merge_schema=(
            schema_request.on_schema_mismatch == "evolve"
            and schema_request.validated_mode == SilverWriteMode.MERGE
        ),
    )


def _sync_validate_and_build_arrow(
    host: _SilverWriterValidationHostProtocol,
    request: _SilverWritePreparationRequest,
) -> _ValidatedSilverWriteContext:
    """Run synchronous Silver validation steps and build Arrow payload."""
    records = host._deduplicate_by_primary_keys(
        request.records,
        request.primary_keys,
    )
    validated_mode = host._validate_write_mode(request.mode)
    _enforce_write_policy(host, validated_mode, request.table_name)
    _validate_records(host, records, request.table_name, request.schema)
    host._validate_key_nullability(
        records,
        request.primary_keys,
        request.partition_cols,
        request.key_nullability_rules,
        request.table_name,
    )
    _validate_silver_pandera(host, records, request.table_name)
    arrow_data = host._prepare_arrow_data(
        records,
        request.schema,
        request.primary_keys,
        column_order=request.column_order,
    )
    return _ValidatedSilverWriteContext(
        records=records,
        validated_mode=validated_mode,
        arrow_data=arrow_data,
    )


def _enforce_write_policy(
    host: _SilverWriterValidationHostProtocol,
    mode: SilverWriteMode,
    table_name: str,
) -> None:
    """Enforce write mode policy for Silver layer."""
    policy_mode = host._to_policy_write_mode(mode)
    try:
        host._write_policy.validate(Layer.SILVER, policy_mode)
    except PolicyViolationError:
        host.logger.error(
            "Write mode policy violation",
            layer="silver",
            mode=mode.value,
            policy_mode=policy_mode.value,
            table=table_name,
        )
        if host._metrics:
            host._metrics.increment_counter(
                "policy_violations_total",
                1,
                {"layer": "silver", "mode": policy_mode.value},
            )
        raise


def _validate_records(
    host: _SilverWriterValidationHostProtocol,
    records: list[BronzeRecord],
    table_name: str,
    schema: pa.Schema,
) -> None:
    """Validate core Silver write payload shape before persistence."""
    if not records:
        raise ValueError("No records to write")

    keys = set(records[0].keys())
    optional_missing = [key for key in schema.names if key not in keys]
    if optional_missing:
        host.logger.debug(
            "Optional fields missing in batch",
            table=table_name,
            missing=optional_missing,
        )


def _validate_silver_pandera(
    host: _SilverWriterValidationHostProtocol,
    records: list[BronzeRecord],
    table_name: str,
) -> None:
    """Validate records using Pandera schema before writing to Silver."""
    schema = getattr(host._silver_validator, "_schema", None)
    schema_columns = getattr(schema, "columns", {})
    preserve_state = "_state" in schema_columns
    cleaned_records = (
        records
        if preserve_state
        else [
            {key: value for key, value in record.items() if key != "_state"}
            for record in records
        ]
    )

    result = host._silver_validator.validate(cleaned_records)
    if not result.valid:
        host.logger.error(
            "Silver Pandera validation failed",
            table=table_name,
            errors=result.errors,
        )
        if host._metrics:
            host._metrics.increment_counter(
                "silver_validation_failures_total",
                1,
                {
                    "table": table_name,
                    "pipeline": _pipeline_name_from_table_name(table_name),
                },
            )
        raise SchemaViolationError(table_name, result.errors)


async def _finalize_silver_write_payload(
    host: _SilverWriterValidationHostProtocol,
    schema_request: _SilverSchemaPolicyRequest,
) -> _PreparedSilverWritePayload:
    """Run schema policy checks and build the final Silver payload."""
    await host._check_schema_drift(
        schema_request.table_name,
        schema_request.records,
        schema_request.on_schema_mismatch,
    )
    return _build_prepared_silver_write_payload(
        table_path=host._resolve_table_path(schema_request.table_name),
        schema_request=schema_request,
    )
