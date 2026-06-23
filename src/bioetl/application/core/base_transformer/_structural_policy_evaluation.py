"""Structural policy contract evaluation helpers."""

from __future__ import annotations

from bioetl.application.core.base_transformer._structural_policy_coercion import (
    coerce_value,
)
from bioetl.application.core.base_transformer._structural_policy_contracts import (
    is_missing_value,
)
from bioetl.application.core.base_transformer._structural_policy_events import (
    build_optional_nonnullable_events,
    build_quarantine_outcome,
    build_structural_details,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
    StructuralPolicyOutcome,
    StructuralPolicySignal,
)


def evaluate_contract(
    contract: StructuralFieldSpec,
    working_record: dict[str, object],
    events: list[StructuralPolicySignal],
) -> StructuralPolicyOutcome | None:
    """Evaluate one contract against the working record."""
    if contract.is_system_field or contract.logical_type == "unknown":
        return None

    field_present = contract.field_name in working_record
    value = working_record.get(contract.field_name)

    missing_outcome = evaluate_missing_required(
        contract=contract,
        value=value,
        working_record=working_record,
        events=events,
    )
    if missing_outcome is not None:
        return missing_outcome

    if contract.logical_type == "string" or not field_present:
        return None
    if value is None:
        return evaluate_null_value(
            contract=contract,
            working_record=working_record,
            events=events,
        )

    coerced_value = coerce_value(value, contract)
    if coerced_value is not None:
        working_record[contract.field_name] = coerced_value
        return None

    return evaluate_invalid_value(
        contract=contract,
        value=value,
        working_record=working_record,
        events=events,
    )


def evaluate_missing_required(
    *,
    contract: StructuralFieldSpec,
    value: object,
    working_record: dict[str, object],
    events: list[StructuralPolicySignal],
) -> StructuralPolicyOutcome | None:
    """Return quarantine outcome when a required field is missing."""
    if contract.optional or contract.nullable:
        return None
    if not is_missing_value(
        value,
        logical_type=contract.logical_type,
        empty_as_missing=contract.empty_as_missing,
    ):
        return None
    details = build_structural_details(
        reason_code="required_field_missing",
        contract=contract,
        actual_value=value,
        action_taken="quarantine_original_record",
    )
    return build_quarantine_outcome(
        working_record=working_record,
        events=events,
        quarantine_reason=f"Required field '{contract.field_name}' is missing",
        details=details,
    )


def evaluate_null_value(
    *,
    contract: StructuralFieldSpec,
    working_record: dict[str, object],
    events: list[StructuralPolicySignal],
) -> StructuralPolicyOutcome | None:
    """Evaluate explicit nulls for non-string fields."""
    if contract.nullable:
        return None
    if not contract.optional:
        return None
    details = build_structural_details(
        reason_code="optional_nonnullable_field_type_mismatch",
        contract=contract,
        actual_value=None,
        action_taken="propose_null_warn_error_then_quarantine",
        proposed_normalized_outcome=None,
        dq_warn=True,
        dq_error=True,
    )
    events.extend(build_optional_nonnullable_events(details))
    return build_quarantine_outcome(
        working_record=working_record,
        events=events,
        quarantine_reason=f"Optional field '{contract.field_name}' cannot be null",
        details=details,
    )


def evaluate_invalid_value(
    *,
    contract: StructuralFieldSpec,
    value: object,
    working_record: dict[str, object],
    events: list[StructuralPolicySignal],
) -> StructuralPolicyOutcome | None:
    """Handle values that cannot be coerced into the contract type."""
    if contract.nullable:
        coerce_invalid_nullable_value(
            contract=contract,
            value=value,
            working_record=working_record,
            events=events,
        )
        return None

    details = build_structural_details(
        reason_code=(
            "optional_nonnullable_field_type_mismatch"
            if contract.optional
            else "required_field_type_mismatch"
        ),
        contract=contract,
        actual_value=value,
        action_taken=(
            "propose_null_warn_error_then_quarantine"
            if contract.optional
            else "quarantine_original_record"
        ),
        proposed_normalized_outcome=None,
        dq_warn=contract.optional,
        dq_error=contract.optional,
    )
    if contract.optional:
        events.extend(build_optional_nonnullable_events(details))
        reason = f"Optional non-nullable field '{contract.field_name}' has invalid type"
    else:
        reason = f"Required field '{contract.field_name}' has invalid type"
    return build_quarantine_outcome(
        working_record=working_record,
        events=events,
        quarantine_reason=reason,
        details=details,
    )


def coerce_invalid_nullable_value(
    *,
    contract: StructuralFieldSpec,
    value: object,
    working_record: dict[str, object],
    events: list[StructuralPolicySignal],
) -> None:
    """Normalize invalid nullable values to null and emit a warning."""
    working_record[contract.field_name] = None
    working_record["_dq_warn"] = True
    details = build_structural_details(
        reason_code="nullable_field_type_coerced_to_null",
        contract=contract,
        actual_value=value,
        action_taken="set_null_and_warn",
        proposed_normalized_outcome=None,
        dq_warn=True,
    )
    events.append(
        StructuralPolicySignal(
            level="warning",
            event="silver_structural_type_coerced_to_null",
            details=details,
        )
    )


__all__ = ["evaluate_contract"]
