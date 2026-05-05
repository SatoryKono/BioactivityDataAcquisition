"""Private support helpers for schema-aware structural policy."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer._structural_policy_coercion import (
    coerce_value,
)
from bioetl.application.core.base_transformer._structural_policy_contracts import (
    is_missing_value,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
    StructuralPolicyOutcome,
    StructuralPolicySignal,
)
from bioetl.domain.types import JsonDict, SilverRecord

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer._structural_policy_types import (
        StructuralPolicyProtocol,
    )

_SENSITIVE_FIELD_NAME_TOKENS = frozenset(
    {"api_key", "authorization", "password", "secret", "token"}
)


class NoOpStructuralPolicy:
    """Fallback policy used when no schema-aware enforcement is configured."""

    def apply(self, record: SilverRecord) -> StructuralPolicyOutcome:
        """Return the record unchanged."""
        return StructuralPolicyOutcome(record=record)


class SchemaAwareStructuralPolicy:
    """Generic presence/type guard built from schema + config contracts."""

    def __init__(self, contracts: tuple[StructuralFieldSpec, ...]) -> None:
        self.contracts = contracts

    def apply(self, record: SilverRecord) -> StructuralPolicyOutcome:
        """Apply structural presence/type policy to one transformed record."""
        working_record = dict(record)
        events: list[StructuralPolicySignal] = []

        for contract in self.contracts:
            outcome = self._evaluate_contract(contract, working_record, events)
            if outcome is not None:
                return outcome

        return StructuralPolicyOutcome(
            record=cast("SilverRecord", working_record),
            events=tuple(events),
        )

    def _evaluate_contract(
        self,
        contract: StructuralFieldSpec,
        working_record: dict[str, object],
        events: list[StructuralPolicySignal],
    ) -> StructuralPolicyOutcome | None:
        """Evaluate one contract against the working record."""
        if contract.is_system_field or contract.logical_type == "unknown":
            return None

        field_present = contract.field_name in working_record
        value = working_record.get(contract.field_name)

        missing_outcome = self._evaluate_missing_required(
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
            return self._evaluate_null_value(
                contract=contract,
                working_record=working_record,
                events=events,
            )

        coerced_value = coerce_value(value, contract)
        if coerced_value is not None:
            working_record[contract.field_name] = coerced_value
            return None

        return self._evaluate_invalid_value(
            contract=contract,
            value=value,
            working_record=working_record,
            events=events,
        )

    def _evaluate_missing_required(
        self,
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

    def _evaluate_null_value(
        self,
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

    def _evaluate_invalid_value(
        self,
        *,
        contract: StructuralFieldSpec,
        value: object,
        working_record: dict[str, object],
        events: list[StructuralPolicySignal],
    ) -> StructuralPolicyOutcome | None:
        """Handle values that cannot be coerced into the contract type."""
        if contract.nullable:
            self._coerce_invalid_nullable_value(
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
            reason = (
                f"Optional non-nullable field '{contract.field_name}' has invalid type"
            )
        else:
            reason = f"Required field '{contract.field_name}' has invalid type"
        return build_quarantine_outcome(
            working_record=working_record,
            events=events,
            quarantine_reason=reason,
            details=details,
        )

    def _coerce_invalid_nullable_value(
        self,
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


def build_quarantine_outcome(
    *,
    working_record: dict[str, object],
    events: list[StructuralPolicySignal],
    quarantine_reason: str,
    details: JsonDict,
) -> StructuralPolicyOutcome:
    """Build a quarantine outcome with the current record snapshot."""
    return StructuralPolicyOutcome(
        record=cast("SilverRecord", working_record),
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


def build_structural_policy(
    *,
    domain_config: object,
    pandera_silver_schema: object | None,
) -> StructuralPolicyProtocol:
    """Build structural policy from pipeline domain config and Pandera schema."""
    from bioetl.application.core.base_transformer._structural_policy_contracts import (
        resolve_field_contracts,
        resolve_pandera_schema,
    )
    from bioetl.application.core.base_transformer.field_policy import (
        FieldPolicyResolver,
    )

    schema = resolve_pandera_schema(pandera_silver_schema)
    if schema is None:
        return NoOpStructuralPolicy()

    field_policy_resolver = FieldPolicyResolver.from_domain_config(domain_config)
    contracts = tuple(
        resolve_field_contracts(
            schema=schema,
            field_policy_resolver=field_policy_resolver,
        )
    )
    if not contracts:
        return NoOpStructuralPolicy()
    return SchemaAwareStructuralPolicy(contracts=contracts)
