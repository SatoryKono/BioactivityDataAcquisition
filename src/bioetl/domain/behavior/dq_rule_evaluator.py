"""Pure DQ rule evaluation helpers for runtime record validation.

Executes field, cross-field, and conditional validations against normalized
records without performing any I/O. The resulting rule outcomes carry
contract-aware dispositions resolved from the effective DQ configuration.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import TYPE_CHECKING

from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.domain.validation.chemical import validate_smiles

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


def _field_rule_violated(record: JsonDict, rule: FieldValidation) -> bool:
    value = record.get(rule.field)
    evaluator = _FIELD_RULE_EVALUATORS.get(rule.validation_type)
    if evaluator is None:
        return False
    return evaluator(record, rule, value)


def _cross_rule_violated(record: JsonDict, rule: CrossFieldValidation) -> bool:
    values = [record.get(field) for field in rule.fields]
    present_count = sum(1 for value in values if _is_present(value))
    evaluator = _CROSS_RULE_EVALUATORS.get(rule.condition)
    if evaluator is None:
        return False
    return evaluator(record, rule, present_count)


def _conditional_matches(record: JsonDict, rule: ConditionalValidation) -> bool:
    value = record.get(rule.condition_field)
    evaluator = _CONDITIONAL_MATCHERS.get(rule.condition_operator)
    if evaluator is None:
        return False
    return evaluator(value, rule.condition_value)


def _range_rule_violated(value: object, rule: FieldValidation) -> bool:
    numeric_value = _coerce_numeric_value(value)
    if numeric_value is None:
        return True
    return _violates_minimum(numeric_value, rule) or _violates_maximum(
        numeric_value, rule
    )


def _pattern_rule_violated(value: object, rule: FieldValidation) -> bool:
    if not isinstance(value, str) or rule.pattern is None:
        return True
    return re.search(rule.pattern, value) is None


def _max_length_rule_violated(value: object, rule: FieldValidation) -> bool:
    if not isinstance(value, str) or rule.max_length is None:
        return True
    return len(value) > rule.max_length


def _not_empty_list_rule_violated(value: object) -> bool:
    list_like = _coerce_list_like(value)
    if list_like is None:
        return True
    return len(list_like) == 0


def _custom_rule_violated(
    record: JsonDict,
    value: object,
    validator_name: str | None,
) -> bool:
    if validator_name == "smiles_validator":
        return value is not None and not validate_smiles(str(value))
    if validator_name == "validate_hierarchy_no_self_reference":
        return _custom_cross_rule_violated(
            record,
            validator_name,
        )
    return False


def _custom_cross_rule_violated(
    record: JsonDict,
    validator_name: str | None,
) -> bool:
    if validator_name == "validate_hierarchy_no_self_reference":
        protein_class_id = record.get("protein_class_id")
        parent_id = record.get("parent_id")
        return _is_present(protein_class_id) and protein_class_id == parent_id
    return False


def _is_present(value: object) -> bool:
    return value is not None


def _coerce_list_like(value: object) -> list[object] | None:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple | set):
        return list(value)
    if not isinstance(value, str):
        return None
    return _coerce_string_list_like(value)


def _required_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    return rule.field not in record or value is None


def _not_null_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record, rule
    return value is None


def _range_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else _range_rule_violated(value, rule)


def _pattern_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else _pattern_rule_violated(value, rule)


def _enum_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else value not in set(rule.allowed)


def _max_length_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else _max_length_rule_violated(value, rule)


def _not_empty_list_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record, rule
    return False if value is None else _not_empty_list_rule_violated(value)


def _custom_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    if value is None:
        return False
    return _custom_rule_violated(record, value, rule.validator)


def _all_present_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
    present_count: int,
) -> bool:
    del record
    return present_count != len(rule.fields)


def _any_present_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
    present_count: int,
) -> bool:
    del record, rule
    return present_count == 0


def _mutually_exclusive_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
    present_count: int,
) -> bool:
    del record, rule
    return present_count > 1


def _conditional_required_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
    present_count: int,
) -> bool:
    del present_count
    if rule.trigger_field is None or rule.required_field is None:
        return True
    if not _is_present(record.get(rule.trigger_field)):
        return False
    return not _is_present(record.get(rule.required_field))


def _custom_cross_field_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
    present_count: int,
) -> bool:
    del present_count
    return _custom_cross_rule_violated(record, rule.validator)


def _eq_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value == condition_value


def _ne_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value != condition_value


def _in_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value in _condition_options(condition_value)


def _not_in_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value not in _condition_options(condition_value)


def _condition_options(condition_value: str | tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(condition_value, tuple):
        return condition_value
    return (condition_value,)


def _coerce_numeric_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _violates_minimum(numeric_value: float, rule: FieldValidation) -> bool:
    return rule.min_value is not None and numeric_value < rule.min_value


def _violates_maximum(numeric_value: float, rule: FieldValidation) -> bool:
    return rule.max_value is not None and numeric_value > rule.max_value


def _coerce_string_list_like(value: str) -> list[object] | None:
    stripped = value.strip()
    if not stripped:
        return []
    if not _looks_like_json_list(stripped):
        return None
    return _decode_json_list_like(stripped)


def _looks_like_json_list(value: str) -> bool:
    return value.startswith("[") and value.endswith("]")


def _decode_json_list_like(value: str) -> list[object] | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


_FIELD_RULE_EVALUATORS = {
    "required": _required_rule_violated,
    "not_null": _not_null_rule_violated,
    "range": _range_field_rule_violated,
    "pattern": _pattern_field_rule_violated,
    "enum": _enum_field_rule_violated,
    "max_length": _max_length_field_rule_violated,
    "not_empty_list": _not_empty_list_field_rule_violated,
    "custom": _custom_field_rule_violated,
}


_CROSS_RULE_EVALUATORS = {
    "all_present": _all_present_rule_violated,
    "any_present": _any_present_rule_violated,
    "mutually_exclusive": _mutually_exclusive_rule_violated,
    "conditional_required": _conditional_required_rule_violated,
    "custom": _custom_cross_field_rule_violated,
}


_CONDITIONAL_MATCHERS = {
    "eq": _eq_condition_matches,
    "ne": _ne_condition_matches,
    "in": _in_condition_matches,
    "not_in": _not_in_condition_matches,
}
