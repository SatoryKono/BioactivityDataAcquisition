# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Structural policy event and detail builders."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
    StructuralPolicyOutcome,
    StructuralPolicySignal,
)
from bioetl.domain.types import JsonDict, SilverRecord

if TYPE_CHECKING:
    from bioetl.domain.filtering import FilterDecision

_STRUCTURAL_ACTION_BY_REASON_CODE: dict[str, str] = {
    "required_field_missing": "presence_quarantine",
    "structural_policy_type_mismatch": "required_type_quarantine",
    "structural_policy_null_optional_forbidden": "optional_nonnullable_quarantine",
}
_STRUCTURAL_ACTION_BY_EVENT: dict[str, str] = {
    "silver_structural_type_coerced_to_null": "nullable_type_to_null",
}


def classify_structural_action(
    details: dict[str, object] | None,
    event_names: set[str],
) -> str | None:
    """Map structural details/events to a bounded telemetry action label."""
    if details is not None:
        reason_code = details.get("reason_code")
        if isinstance(reason_code, str):
            mapped = _STRUCTURAL_ACTION_BY_REASON_CODE.get(reason_code)
            if mapped is not None:
                return mapped
    for event_name in event_names:
        mapped = _STRUCTURAL_ACTION_BY_EVENT.get(event_name)
        if mapped is not None:
            return mapped
    return None


def classify_structural_shadow_comparison(
    *,
    structural_rejected: bool,
    silver_filter_decision: FilterDecision | None,
) -> str | None:
    """Build a bounded comparison label for structural vs Silver filtering."""
    if silver_filter_decision is None:
        return None
    silver_state = "reject" if not silver_filter_decision.include else "pass"
    structural_state = "reject" if structural_rejected else "pass"
    return f"structural_{structural_state}_silver_filter_{silver_state}"


_SENSITIVE_FIELD_NAME_TOKENS = frozenset(
    {"api_key", "apikey", "authorization", "password", "secret", "token"}
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


def optional_sources_for_field(
    policy: object,
    field_name: str | None,
) -> list[str]:
    """Return resolved optionality metadata for one policy field."""
    if not field_name:
        return []
    for contract in getattr(policy, "contracts", ()):
        if getattr(contract, "field_name", None) == field_name:
            return list(getattr(contract, "optional_sources", ()))
    return []


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
    "classify_structural_action",
    "classify_structural_shadow_comparison",
    "optional_sources_for_field",
    "preview_value",
]
