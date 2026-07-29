# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Private support helpers for schema-aware structural policy."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer._structural_policy_evaluation import (
    evaluate_contract,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
    StructuralPolicyOutcome,
    StructuralPolicySignal,
)
from bioetl.domain.types import SilverRecord

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer._structural_policy_types import (
        StructuralPolicyProtocol,
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
            outcome = evaluate_contract(contract, working_record, events)
            if outcome is not None:
                return outcome

        return StructuralPolicyOutcome(
            record=cast("SilverRecord", working_record),  # pyright: ignore[reportInvalidCast]
            events=tuple(events),
        )


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
