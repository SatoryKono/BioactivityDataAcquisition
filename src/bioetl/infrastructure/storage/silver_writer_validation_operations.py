"""Validation operations extracted from ``SilverWriterValidationMixin``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

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
]


@dataclass(frozen=True, slots=True)
class _PreparedSilverWritePayload:
    """Validated write payload produced before Delta write execution."""

    records: list[BronzeRecord]
    validated_mode: SilverWriteMode
    table_path: str
    arrow_data: pa.Table


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
class _SilverSchemaDriftDiff:
    """Normalized schema drift field sets for one Silver batch."""

    new_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]


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


def _count_null_violations(
    records: list[BronzeRecord],
    rules: dict[tuple[str, Literal["merge", "partition"]], KeyNullabilityRule],
    field: str,
    key_type: Literal["merge", "partition"],
) -> int:
    """Count null values for a non-nullable key field."""
    rule = rules.get((field, key_type))
    if rule is None or rule.nullable:
        return 0
    return sum(1 for record in records if record.get(field) is None)


def _collect_key_violations(
    records: list[BronzeRecord],
    rules: dict[tuple[str, Literal["merge", "partition"]], KeyNullabilityRule],
    primary_keys: list[str],
    partition_cols: list[str] | None,
) -> list[tuple[str, str, int]]:
    """Collect all nullability violations across merge and partition keys."""
    violations: list[tuple[str, str, int]] = []
    for key in primary_keys:
        if count := _count_null_violations(records, rules, key, "merge"):
            violations.append((key, "merge", count))
    for key in partition_cols or []:
        if count := _count_null_violations(records, rules, key, "partition"):
            violations.append((key, "partition", count))
    return violations


def _validate_key_nullability_impl(
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
    violations = _collect_key_violations(records, rules, primary_keys, partition_cols)

    if violations:
        details = [
            f"{key_type}:{field} null_count={count}"
            for field, key_type, count in violations
        ]
        raise ValueError(
            "Key nullability policy violation for table "
            f"'{table_name}': {'; '.join(details)}"
        )


def _diff_schema_fields(
    existing_schema: pa.Schema | None,
    records: list[BronzeRecord],
) -> tuple[set[str], set[str]] | None:
    """Return incoming-only and existing-only fields for one Silver batch."""
    if existing_schema is None or not records:
        return None

    incoming_fields = set(records[0].keys())
    existing_fields = set(existing_schema.names)
    return incoming_fields - existing_fields, existing_fields - incoming_fields


def _build_silver_schema_drift_diff(
    existing_schema: pa.Schema | None,
    records: list[BronzeRecord],
) -> _SilverSchemaDriftDiff | None:
    """Build a normalized Silver schema drift diff from existing and incoming data."""
    diff = _diff_schema_fields(existing_schema, records)
    if diff is None:
        return None

    new_fields, missing_fields = diff
    if not new_fields and not missing_fields:
        return None

    return _SilverSchemaDriftDiff(
        new_fields=tuple(sorted(new_fields)),
        missing_fields=tuple(sorted(missing_fields)),
    )


def _build_schema_drift_info(
    diff: _SilverSchemaDriftDiff,
) -> SchemaDriftInfo:
    """Build SchemaDriftInfo from a normalized field diff."""
    from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo

    critical_missing = [
        field for field in diff.missing_fields if not field.startswith("_")
    ]
    status: Literal["info", "warn", "critical"]
    if critical_missing:
        status = "critical"
    elif len(diff.new_fields) > 3:
        status = "warn"
    else:
        status = "info"

    return SchemaDriftInfo(
        status=status,
        new_fields=diff.new_fields,
        missing_fields=diff.missing_fields,
    )


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
    """Validate records have required metadata fields."""
    if not records:
        raise ValueError("No records to write")

    required_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
    if missing_fields := required_fields - set(records[0].keys()):
        raise ValueError(
            f"Records missing required metadata fields: {missing_fields}"
        )

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
    cleaned_records = [
        {key: value for key, value in record.items() if key != "_state"}
        for record in records
    ]

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
                {"table": table_name},
            )
        raise SchemaViolationError(table_name, result.errors)


async def _check_schema_drift(
    host: _SilverWriterValidationHostProtocol,
    table_name: str,
    records: list[BronzeRecord],
    on_schema_mismatch: Literal["error", "evolve", "ignore"],
) -> None:
    """Check schema drift and handle according to configured policy."""
    existing_schema = await host._get_table_schema(table_name)
    diff = _build_silver_schema_drift_diff(existing_schema, records)
    if diff is None:
        return

    host.logger.warning(
        "Schema drift detected",
        table=table_name,
        new_fields=list(diff.new_fields) if diff.new_fields else None,
        removed_fields=list(diff.missing_fields) if diff.missing_fields else None,
        action=on_schema_mismatch,
    )

    if on_schema_mismatch == "error":
        raise SchemaEvolutionError(
            table=table_name,
            new_fields=set(diff.new_fields),
            removed_fields=set(diff.missing_fields),
        )


async def _detect_schema_drift(
    host: _SilverWriterValidationHostProtocol,
    table_name: str,
    records: list[BronzeRecord],
) -> SchemaDriftInfo | None:
    """Detect schema drift between existing table and incoming records."""
    existing_schema = await host._get_table_schema(table_name)
    diff = _build_silver_schema_drift_diff(existing_schema, records)
    if diff is None:
        return None
    return _build_schema_drift_info(diff)


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
