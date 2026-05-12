"""Pure DQ rule evaluation helpers for runtime record validation.

Executes field, cross-field, and conditional validations against normalized
records without performing any I/O. The resulting rule outcomes carry
contract-aware dispositions resolved from the effective DQ configuration.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from bioetl.domain.behavior._dq_rule_evaluators import (
    _conditional_matches,
    _cross_rule_violated,
    _field_rule_violated,
)
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
    DQViolationKind,
)

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig
    from bioetl.domain.config.validation import (
        ConditionalValidation,
        CrossFieldValidation,
        FieldValidation,
    )
    from bioetl.domain.types import JsonDict

__all__ = [
    "evaluate_dq_rules_for_record",
    "select_highest_priority_disposition",
]


_DISPOSITION_PRIORITY: dict[DQDisposition, int] = {
    DQDisposition.FAIL: 5,
    DQDisposition.QUARANTINE: 4,
    DQDisposition.SKIP: 3,
    DQDisposition.WARN: 2,
    DQDisposition.PASS: 1,
}


def evaluate_dq_rules_for_record(
    record: JsonDict,
    dq_config: DQConfig | None,
    *,
    is_enricher: bool = False,
) -> list[DQRuleOutcome]:
    """Evaluate runtime DQ rules for one normalized record."""
    if dq_config is None:
        return []

    resolver = DQPolicyResolver(dq_config)
    return [
        *_evaluate_field_rules(
            record,
            dq_config=dq_config,
            resolver=resolver,
            is_enricher=is_enricher,
        ),
        *_evaluate_cross_rules(record, dq_config=dq_config, resolver=resolver),
        *_evaluate_conditional_rules(
            record,
            dq_config=dq_config,
            resolver=resolver,
            is_enricher=is_enricher,
        ),
    ]


def select_highest_priority_disposition(
    outcomes: list[DQRuleOutcome],
) -> DQDisposition:
    """Return the strongest disposition across rule outcomes."""
    if not outcomes:
        return DQDisposition.PASS
    return max(
        (outcome.disposition for outcome in outcomes),
        key=lambda disposition: _DISPOSITION_PRIORITY.get(disposition, 0),
    )


def _build_field_outcome(
    rule: FieldValidation,
    *,
    resolver: DQPolicyResolver,
    dq_config: DQConfig,
    is_enricher: bool,
) -> DQRuleOutcome:
    severity = rule.effective_severity(is_enricher=is_enricher)
    outcome = resolver.create_rule_outcome(
        rule_id=f"field.{rule.field}.{rule.validation_type}",
        violation_kind=DQViolationKind.BUSINESS_RULE_VIOLATION,
        severity=severity,
        affected_fields=[rule.field],
        config_path=_config_path(resolver),
    )
    return _apply_invalid_record_policy(outcome, dq_config=dq_config, severity=severity)


def _build_cross_outcome(
    rule: CrossFieldValidation,
    *,
    resolver: DQPolicyResolver,
) -> DQRuleOutcome:
    return resolver.create_rule_outcome(
        rule_id=f"cross.{rule.name}",
        violation_kind=DQViolationKind.BUSINESS_RULE_VIOLATION,
        severity=rule.severity,
        affected_fields=list(rule.fields),
        config_path=_config_path(resolver),
    )


def _build_conditional_outcome(
    condition: ConditionalValidation,
    nested_rule: FieldValidation,
    *,
    resolver: DQPolicyResolver,
    dq_config: DQConfig,
    is_enricher: bool,
) -> DQRuleOutcome:
    severity = nested_rule.effective_severity(is_enricher=is_enricher)
    outcome = resolver.create_rule_outcome(
        rule_id=(
            f"conditional.{condition.name}."
            f"{nested_rule.field}.{nested_rule.validation_type}"
        ),
        violation_kind=DQViolationKind.BUSINESS_RULE_VIOLATION,
        severity=severity,
        affected_fields=[nested_rule.field],
        config_path=_config_path(resolver),
    )
    return _apply_invalid_record_policy(outcome, dq_config=dq_config, severity=severity)


def _apply_invalid_record_policy(
    outcome: DQRuleOutcome,
    *,
    dq_config: DQConfig,
    severity: str,
) -> DQRuleOutcome:
    """Map error-severity rule outcomes onto runtime invalid-record policy."""
    if severity != "error":
        return outcome
    if outcome.disposition not in (DQDisposition.PASS, DQDisposition.WARN):
        return outcome

    policy_disposition = {
        "quarantine": DQDisposition.QUARANTINE,
        "skip": DQDisposition.SKIP,
        "fail": DQDisposition.FAIL,
    }[dq_config.invalid_record_policy]
    return replace(
        outcome,
        disposition=policy_disposition,
        disposition_reason=(f"invalid_record_policy={dq_config.invalid_record_policy}"),
    )


def _config_path(resolver: DQPolicyResolver) -> str | None:
    policy_ref = resolver.build_policy_ref()
    return f"contracts/{policy_ref.contract_ref}/dq_rules.yaml"


def _evaluate_field_rules(
    record: JsonDict,
    *,
    dq_config: DQConfig,
    resolver: DQPolicyResolver,
    is_enricher: bool,
) -> list[DQRuleOutcome]:
    outcomes: list[DQRuleOutcome] = []
    for rule in dq_config.field_validations:
        if _field_rule_violated(record, rule):
            outcomes.append(
                _build_field_outcome(
                    rule,
                    resolver=resolver,
                    dq_config=dq_config,
                    is_enricher=is_enricher,
                )
            )
    return outcomes


def _evaluate_cross_rules(
    record: JsonDict,
    *,
    dq_config: DQConfig,
    resolver: DQPolicyResolver,
) -> list[DQRuleOutcome]:
    outcomes: list[DQRuleOutcome] = []
    for rule in dq_config.cross_field_validations:
        if _cross_rule_violated(record, rule):
            outcomes.append(_build_cross_outcome(rule, resolver=resolver))
    return outcomes


def _evaluate_conditional_rules(
    record: JsonDict,
    *,
    dq_config: DQConfig,
    resolver: DQPolicyResolver,
    is_enricher: bool,
) -> list[DQRuleOutcome]:
    outcomes: list[DQRuleOutcome] = []
    for rule in dq_config.conditional_validations:
        if not _conditional_matches(record, rule):
            continue
        outcomes.extend(
            _evaluate_nested_conditional_rules(
                record,
                rule,
                dq_config=dq_config,
                resolver=resolver,
                is_enricher=is_enricher,
            )
        )
    return outcomes


def _evaluate_nested_conditional_rules(
    record: JsonDict,
    rule: ConditionalValidation,
    *,
    dq_config: DQConfig,
    resolver: DQPolicyResolver,
    is_enricher: bool,
) -> list[DQRuleOutcome]:
    outcomes: list[DQRuleOutcome] = []
    for nested_rule in rule.then_validations:
        if _field_rule_violated(record, nested_rule):
            outcomes.append(
                _build_conditional_outcome(
                    rule,
                    nested_rule,
                    resolver=resolver,
                    dq_config=dq_config,
                    is_enricher=is_enricher,
                )
            )
    return outcomes
