"""Contract resolution helpers for schema-aware structural policy."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer.field_policy import FieldPolicyResolver
from bioetl.application.core.base_transformer.optionality import (
    is_framework_managed_field,
)

from ._structural_policy_types import LogicalType, StructuralFieldSpec

if TYPE_CHECKING:
    import pandera as pa


def resolve_pandera_schema(schema_builder: object | None) -> pa.DataFrameSchema | None:
    """Resolve runtime Pandera schema from DataFrameModel class or schema object."""
    if schema_builder is None:
        return None
    if hasattr(schema_builder, "columns"):
        return cast("pa.DataFrameSchema", schema_builder)
    to_schema = getattr(schema_builder, "to_schema", None)
    if callable(to_schema):
        return cast("pa.DataFrameSchema", to_schema())
    return None


def resolve_field_contracts(
    *,
    schema: pa.DataFrameSchema,
    field_policy_resolver: FieldPolicyResolver,
) -> list[StructuralFieldSpec]:
    """Resolve effective contracts from Pandera columns and config rules."""
    contracts: list[StructuralFieldSpec] = []
    for field_name, column in schema.columns.items():
        physical_type = str(column.dtype)
        resolved_field_policy = field_policy_resolver.resolve(field_name)
        contracts.append(
            StructuralFieldSpec(
                field_name=field_name,
                logical_type=resolve_logical_type(physical_type),
                physical_type=physical_type,
                nullable=column.nullable,
                optional=resolved_field_policy.optional,
                optional_sources=resolved_field_policy.optional_sources,
                empty_as_missing=resolved_field_policy.empty_as_missing,
                coercion_policy=resolved_field_policy.coercion_policy,
                boolean_true_values=resolved_field_policy.boolean_true_values,
                boolean_false_values=resolved_field_policy.boolean_false_values,
                is_system_field=is_framework_managed_field(field_name),
            )
        )
    return contracts


def resolve_logical_type(physical_type: str) -> LogicalType:
    """Map Pandera dtype text to logical business type."""
    normalized = physical_type.lower()
    if normalized == "str" or "string" in normalized:
        return "string"
    if normalized.startswith("int"):
        return "integer"
    if normalized.startswith("float"):
        return "float"
    if normalized == "bool" or "boolean" in normalized or normalized.startswith("bool"):
        return "boolean"
    return "unknown"


def is_missing_value(
    value: object,
    *,
    logical_type: LogicalType,
    empty_as_missing: bool | None,
) -> bool:
    """Check missing semantics without treating all empty containers as missing."""
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip()
        if normalized == "":
            return empty_as_missing is not False
        if logical_type == "string":
            return False
    if empty_as_missing is True and isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
