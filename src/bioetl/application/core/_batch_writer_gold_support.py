# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Gold-layer prepare/validate helpers for BatchWriter IO paths."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.exceptions import SchemaViolationError

if TYPE_CHECKING:
    from bioetl.domain.types import GoldRecord


@runtime_checkable
class _GoldValidatorRebindProtocol(Protocol):
    """Validators that can rebind to a projected Gold schema."""

    def rebind_schema(self, schema: object) -> object: ...


def prepare_gold_records(
    writer: object,
    records: list[GoldRecord],
    *,
    schema: object | None = None,
) -> tuple[list[GoldRecord], list[str]]:
    """Project records to schema and compute available columns."""
    target_schema = schema if schema is not None else writer._gold_schema
    schema_columns = writer._get_schema_columns(target_schema)
    if not schema_columns:
        return records, writer._collect_record_columns(records)

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


def validate_gold_records(
    writer: object,
    records: list[GoldRecord],
    *,
    schema: object | None = None,
) -> None:
    """Validate Gold records against schema contract."""
    validator = writer._gold_validator
    target_schema = schema if schema is not None else writer._gold_schema
    if schema is not None:
        validator = rebind_gold_validator_schema(validator, target_schema)

    result = validator.validate(records)
    if not result.valid:
        debug_export_service = getattr(writer, "_debug_export_service", None)
        if debug_export_service is not None:
            debug_export_service.record_gold_validation_failure(
                records=records,
                errors=result.errors,
            )
        raise SchemaViolationError("gold", result.errors)


def rebind_gold_validator_schema(
    validator: object,
    schema: object,
) -> object:
    """Rebind schema-aware validators via their owned rebind/clone API."""
    rebind = getattr(validator, "rebind_schema", None)
    if callable(rebind):
        return rebind(schema)
    # Validators without a rebind surface keep their original schema binding.
    return validator


def should_defer_gold_validation_to_storage(writer: object) -> bool:
    """Whether Gold validation/projection must happen per-version in storage."""
    policy = getattr(writer, "_gold_schema_policy_by_version", None)
    return bool(policy is not None and policy.is_multi_version)
