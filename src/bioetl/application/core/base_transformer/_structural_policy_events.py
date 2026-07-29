# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Structural policy event and detail builders."""

from __future__ import annotations

from typing import cast

from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
    StructuralPolicyOutcome,
    StructuralPolicySignal,
)
from bioetl.domain.types import JsonDict, SilverRecord

_SENSITIVE_FIELD_NAME_TOKENS = frozenset(
    {"api_key", "authorization", "password", "secret", "token"}
)


def build_quarantine_outcome(
    *,
    working_record: dict[str, object],
    events: list[StructuralPolicySignal],
    quarantine_reason: str,
    details: JsonDict,
) -> StructuralPolicyOutcome:
    """Build a quarantine outcome with the current record snapshot."""
    return StructuralPolicyOutcome(
        record=cast("SilverRecord", working_record),  # pyright: ignore[reportInvalidCast]
        quarantine_reason=quarantine_reason,
        details=details,
        events=tuple(events),
    )


def build_structural_details(
    *,
    reason_code: str,
    contract: StructuralFieldSpec,
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
        "empty_as_missing": contract.empty_as_missing,
        "coercion_policy": contract.coercion_policy,
        "action_taken": action_taken,
        "actual_python_type": type(actual_value).__name__,
        "actual_value_preview": preview_value(
            actual_value,
            field_name=contract.field_name,
        ),
    }
    if contract.boolean_true_values:
        details["boolean_true_values"] = list(contract.boolean_true_values)
    if contract.boolean_false_values:
        details["boolean_false_values"] = list(contract.boolean_false_values)
    if proposed_normalized_outcome is not None or dq_warn or dq_error:
        details["proposed_normalized_outcome"] = proposed_normalized_outcome
    if dq_warn:
        details["dq_warn"] = True
    if dq_error:
        details["dq_error"] = True
    return details


def build_optional_nonnullable_events(
    details: JsonDict,
) -> tuple[StructuralPolicySignal, StructuralPolicySignal]:
    """Build warning + error log events for optional/non-nullable mismatch."""
    return (
        StructuralPolicySignal(
            level="warning",
            event="silver_structural_type_mismatch_warn",
            details=details,
        ),
        StructuralPolicySignal(
            level="error",
            event="silver_structural_type_mismatch_error",
            details=details,
        ),
    )


def preview_value(
    value: object,
    *,
    field_name: str,
    max_length: int = 120,
) -> str:
    """Create a bounded preview suitable for logs/quarantine metadata."""
    normalized_field_name = field_name.strip().lower()
    if any(token in normalized_field_name for token in _SENSITIVE_FIELD_NAME_TOKENS):
        return "<redacted>"
    preview = repr(value)
    if len(preview) <= max_length:
        return preview
    return f"{preview[: max_length - 3]}..."


__all__ = [
    "build_optional_nonnullable_events",
    "build_quarantine_outcome",
    "build_structural_details",
    "preview_value",
]
