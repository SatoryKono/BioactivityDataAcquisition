# mypy: disable-error-code=attr-defined
"""Gold-layer prepare/validate helpers for BatchWriter IO paths."""

from __future__ import annotations

from inspect import signature
from typing import TYPE_CHECKING
from unittest.mock import Mock

from bioetl.domain.exceptions import SchemaViolationError

if TYPE_CHECKING:
    from bioetl.domain.types import GoldRecord


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
    if schema is not None and hasattr(target_schema, "columns"):
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


def should_defer_gold_validation_to_storage(writer: object) -> bool:
    """Whether Gold validation/projection must happen per-version in storage."""
    policy = getattr(writer, "_gold_schema_policy_by_version", None)
    return bool(policy is not None and policy.is_multi_version)
