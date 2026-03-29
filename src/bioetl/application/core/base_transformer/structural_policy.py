"""Schema-aware structural policy for transformed Silver records.

This stage runs after transformer-specific mapping and before semantic
Silver filters. It enforces generic presence/type expectations inferred from
the Silver schema and pipeline config without relying on hard-coded field
lists in application code.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable, cast

from bioetl.application.core.base_transformer.optionality import (
    ConfigSurfaceOptionalityResolver,
    OptionalitySource,
    is_framework_managed_field,
)
from bioetl.domain.types import JsonDict, SilverRecord

if TYPE_CHECKING:
    import pandera as pa

LogicalType = Literal["string", "integer", "float", "boolean", "unknown"]
_BOOL_TRUE_VALUES = frozenset({"1", "true", "yes", "y"})
_BOOL_FALSE_VALUES = frozenset({"0", "false", "no", "n"})


@dataclass(frozen=True, slots=True)
class StructuralFieldContract:
    """Resolved storage/policy contract for one Silver field."""

    field_name: str
    logical_type: LogicalType
    physical_type: str
    nullable: bool
    optional: bool
    optional_sources: tuple[OptionalitySource, ...]
    is_system_field: bool = False


@dataclass(frozen=True, slots=True)
class StructuralPolicyEvent:
    """Log event emitted by structural policy evaluation."""

    level: Literal["warning", "error"]
    event: str
    details: JsonDict


@dataclass(frozen=True, slots=True)
class StructuralPolicyOutcome:
    """Result of applying structural policy to one transformed record."""

    record: SilverRecord
    quarantine_reason: str | None = None
    details: JsonDict | None = None
    events: tuple[StructuralPolicyEvent, ...] = ()

    @property
    def should_quarantine(self) -> bool:
        """Whether the record must be routed to quarantine before write."""
        return self.quarantine_reason is not None


@runtime_checkable
class StructuralPolicyProtocol(Protocol):
    """Protocol consumed by BaseTransformer for structural policy checks."""

    def apply(self, record: SilverRecord) -> StructuralPolicyOutcome:
        """Return remediated record or quarantine directive."""
        ...


class NoOpStructuralPolicy:
    """Fallback policy used when no schema-aware enforcement is configured."""

    def apply(self, record: SilverRecord) -> StructuralPolicyOutcome:
        """Return the record unchanged."""
        return StructuralPolicyOutcome(record=record)


@dataclass(frozen=True, slots=True)
class SchemaAwareStructuralPolicy:
    """Generic presence/type guard built from schema + config contracts."""

    contracts: tuple[StructuralFieldContract, ...]

    def apply(self, record: SilverRecord) -> StructuralPolicyOutcome:
        """Apply structural presence/type policy to one transformed record."""
        working_record = dict(record)
        events: list[StructuralPolicyEvent] = []

        for contract in self.contracts:
            if contract.is_system_field or contract.logical_type == "unknown":
                continue

            field_present = contract.field_name in working_record
            value = working_record.get(contract.field_name)

            if (
                not contract.optional
                and not contract.nullable
                and _is_missing_value(value, contract.logical_type)
            ):
                details = _build_structural_details(
                    reason_code="required_field_missing",
                    contract=contract,
                    actual_value=value,
                    action_taken="quarantine_original_record",
                )
                return StructuralPolicyOutcome(
                    record=cast("SilverRecord", working_record),
                    quarantine_reason=(
                        f"Required field '{contract.field_name}' is missing"
                    ),
                    details=details,
                    events=tuple(events),
                )

            if contract.logical_type == "string" or not field_present:
                continue

            if value is None:
                if contract.nullable:
                    continue
                if contract.optional:
                    details = _build_structural_details(
                        reason_code="optional_nonnullable_field_type_mismatch",
                        contract=contract,
                        actual_value=value,
                        action_taken="propose_null_warn_error_then_quarantine",
                        proposed_normalized_outcome=None,
                        dq_warn=True,
                        dq_error=True,
                    )
                    events.extend(_build_optional_nonnullable_events(details))
                    return StructuralPolicyOutcome(
                        record=cast("SilverRecord", working_record),
                        quarantine_reason=(
                            f"Optional field '{contract.field_name}' cannot be null"
                        ),
                        details=details,
                        events=tuple(events),
                    )
                continue

            coerced_value = _coerce_value(value, contract.logical_type)
            if coerced_value is not None:
                working_record[contract.field_name] = coerced_value
                continue

            if contract.nullable:
                working_record[contract.field_name] = None
                working_record["_dq_warn"] = True
                details = _build_structural_details(
                    reason_code="nullable_field_type_coerced_to_null",
                    contract=contract,
                    actual_value=value,
                    action_taken="set_null_and_warn",
                    proposed_normalized_outcome=None,
                    dq_warn=True,
                )
                events.append(
                    StructuralPolicyEvent(
                        level="warning",
                        event="silver_structural_type_coerced_to_null",
                        details=details,
                    )
                )
                continue

            if contract.optional:
                details = _build_structural_details(
                    reason_code="optional_nonnullable_field_type_mismatch",
                    contract=contract,
                    actual_value=value,
                    action_taken="propose_null_warn_error_then_quarantine",
                    proposed_normalized_outcome=None,
                    dq_warn=True,
                    dq_error=True,
                )
                events.extend(_build_optional_nonnullable_events(details))
                return StructuralPolicyOutcome(
                    record=cast("SilverRecord", working_record),
                    quarantine_reason=(
                        "Optional non-nullable field "
                        f"'{contract.field_name}' has invalid type"
                    ),
                    details=details,
                    events=tuple(events),
                )

            details = _build_structural_details(
                reason_code="required_field_type_mismatch",
                contract=contract,
                actual_value=value,
                action_taken="quarantine_original_record",
            )
            return StructuralPolicyOutcome(
                record=cast("SilverRecord", working_record),
                quarantine_reason=(
                    f"Required field '{contract.field_name}' has invalid type"
                ),
                details=details,
                events=tuple(events),
            )

        return StructuralPolicyOutcome(
            record=cast("SilverRecord", working_record),
            events=tuple(events),
        )


def build_structural_policy(
    *,
    domain_config: object,
    pandera_silver_schema: object | None,
) -> StructuralPolicyProtocol:
    """Build structural policy from pipeline domain config and Pandera schema."""
    schema = _resolve_pandera_schema(pandera_silver_schema)
    if schema is None:
        return NoOpStructuralPolicy()

    optionality_resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        domain_config
    )
    contracts = tuple(
        _resolve_field_contracts(
            schema=schema,
            optionality_resolver=optionality_resolver,
        )
    )
    if not contracts:
        return NoOpStructuralPolicy()
    return SchemaAwareStructuralPolicy(contracts=contracts)


def _resolve_pandera_schema(schema_builder: object | None) -> pa.DataFrameSchema | None:
    """Resolve runtime Pandera schema from DataFrameModel class or schema object."""
    if schema_builder is None:
        return None
    if hasattr(schema_builder, "columns"):
        return cast("pa.DataFrameSchema", schema_builder)
    to_schema = getattr(schema_builder, "to_schema", None)
    if callable(to_schema):
        return cast("pa.DataFrameSchema", to_schema())
    return None


def _resolve_field_contracts(
    *,
    schema: pa.DataFrameSchema,
    optionality_resolver: ConfigSurfaceOptionalityResolver,
) -> list[StructuralFieldContract]:
    """Resolve effective contracts from Pandera columns and config rules."""
    contracts: list[StructuralFieldContract] = []
    for field_name, column in schema.columns.items():
        physical_type = str(column.dtype)
        logical_type = _resolve_logical_type(physical_type)
        is_system_field = is_framework_managed_field(field_name)
        resolved_optionality = optionality_resolver.resolve(field_name)
        contracts.append(
            StructuralFieldContract(
                field_name=field_name,
                logical_type=logical_type,
                physical_type=physical_type,
                nullable=column.nullable,
                optional=resolved_optionality.optional,
                optional_sources=resolved_optionality.sources,
                is_system_field=is_system_field,
            )
        )
    return contracts


def _resolve_logical_type(physical_type: str) -> LogicalType:
    """Map Pandera dtype text to logical business type."""
    normalized = physical_type.lower()
    if normalized == "str" or "string" in normalized:
        return "string"
    if normalized.startswith("int"):
        return "integer"
    if normalized.startswith("float"):
        return "float"
    if normalized == "bool":
        return "boolean"
    return "unknown"


def _is_missing_value(value: object, logical_type: LogicalType) -> bool:
    """Check missing semantics without treating all empty containers as missing."""
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip()
        if normalized == "":
            return True
        if logical_type == "string":
            return False
    return False


def _coerce_value(value: object, logical_type: LogicalType) -> object | None:
    """Return coerced value when conversion is valid, otherwise None."""
    if logical_type == "integer":
        return _coerce_integer(value)
    if logical_type == "float":
        return _coerce_float(value)
    if logical_type == "boolean":
        return _coerce_boolean(value)
    return value


def _coerce_integer(value: object) -> int | None:
    """Coerce value to integer when semantically valid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not isfinite(value) or not value.is_integer():
            return None
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            decimal_value = Decimal(normalized)
        except InvalidOperation:
            return None
        if decimal_value != decimal_value.to_integral_value():
            return None
        return int(decimal_value)
    return None


def _coerce_float(value: object) -> float | None:
    """Coerce value to float when semantically valid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value if isfinite(value) else None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            float_value = float(normalized)
        except ValueError:
            return None
        return float_value if isfinite(float_value) else None
    return None


def _coerce_boolean(value: object) -> bool | None:
    """Coerce value to boolean when semantically valid."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _BOOL_TRUE_VALUES:
            return True
        if normalized in _BOOL_FALSE_VALUES:
            return False
    return None


def _build_structural_details(
    *,
    reason_code: str,
    contract: StructuralFieldContract,
    actual_value: object,
    action_taken: str,
    proposed_normalized_outcome: object | None = None,
    dq_warn: bool = False,
    dq_error: bool = False,
) -> JsonDict:
    """Build structured structural-policy details for logs/quarantine."""
    details: JsonDict = {
        "reason_code": reason_code,
        "field": contract.field_name,
        "expected_logical_type": contract.logical_type,
        "expected_physical_type": contract.physical_type,
        "nullable": contract.nullable,
        "optional": contract.optional,
        "optional_sources": list(contract.optional_sources),
        "action_taken": action_taken,
        "actual_python_type": type(actual_value).__name__,
        "actual_value_preview": _preview_value(actual_value),
    }
    if proposed_normalized_outcome is not None or dq_warn or dq_error:
        details["proposed_normalized_outcome"] = proposed_normalized_outcome
    if dq_warn:
        details["dq_warn"] = True
    if dq_error:
        details["dq_error"] = True
    return details


def _build_optional_nonnullable_events(
    details: JsonDict,
) -> tuple[StructuralPolicyEvent, StructuralPolicyEvent]:
    """Build warning + error log events for optional/non-nullable mismatch."""
    return (
        StructuralPolicyEvent(
            level="warning",
            event="silver_structural_type_mismatch_warn",
            details=details,
        ),
        StructuralPolicyEvent(
            level="error",
            event="silver_structural_type_mismatch_error",
            details=details,
        ),
    )


def _preview_value(value: object, *, max_length: int = 120) -> str:
    """Create a bounded preview suitable for logs/quarantine metadata."""
    preview = repr(value)
    if len(preview) <= max_length:
        return preview
    return f"{preview[: max_length - 3]}..."


__all__ = [
    "NoOpStructuralPolicy",
    "SchemaAwareStructuralPolicy",
    "StructuralFieldContract",
    "StructuralPolicyEvent",
    "StructuralPolicyOutcome",
    "StructuralPolicyProtocol",
    "build_structural_policy",
]
