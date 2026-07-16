"""DQ rule evaluator dictionaries and helper functions.

Extracted from dq_rule_evaluator.py to meet file size limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.behavior._dq_condition_matchers import (
    _CONDITIONAL_MATCHERS,
)
from bioetl.domain.behavior._dq_rule_evaluators_cross import (
    _all_present_rule_violated,
    _any_present_rule_violated,
    _conditional_required_rule_violated,
    _custom_cross_field_rule_violated,
    _custom_cross_rule_violated_impl,
    _equality_rule_violated,
    _mutually_exclusive_rule_violated,
)
from bioetl.domain.behavior._dq_rule_evaluators_vocab import (
    _resolve_custom_validation_strategy,
    validate_target_organism_rule_violated,
)
from bioetl.domain.behavior._dq_value_coercion import (
    _coerce_list_like,
    _coerce_numeric_value,
    _is_present,
    _violates_maximum,
    _violates_minimum,
)
from bioetl.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from bioetl.domain.config.validation import (
        CrossFieldValidation,
        FieldValidation,
    )
    from bioetl.domain.types import JsonDict


def _field_rule_violated(record: JsonDict, rule: FieldValidation) -> bool:
    value = record.get(rule.field)
    evaluator = _FIELD_RULE_EVALUATORS.get(rule.validation_type)
    if evaluator is None:
        raise ValidationError(
            f"Unknown field validation type: {rule.validation_type!r}",
            field="validation_type",
        )
    return evaluator(record, rule, value)


def _cross_rule_violated(record: JsonDict, rule: CrossFieldValidation) -> bool:
    values = [record.get(field) for field in rule.fields]
    present_count = sum(1 for value in values if _is_present(value))
    evaluator = _CROSS_RULE_EVALUATORS.get(rule.condition)
    if evaluator is None:
        raise ValidationError(
            f"Unknown cross-field validation condition: {rule.condition!r}",
            field="condition",
        )
    return evaluator(record, rule, present_count)


def _conditional_matches(record: JsonDict, rule: CrossFieldValidation) -> bool:
    value = record.get(rule.condition_field)
    evaluator = _CONDITIONAL_MATCHERS.get(rule.condition_operator)
    if evaluator is None:
        raise ValidationError(
            f"Unknown conditional operator: {rule.condition_operator!r}",
            field="condition_operator",
        )
    return evaluator(value, rule.condition_value)


def _range_rule_violated(value: object, rule: FieldValidation) -> bool:
    numeric_value = _coerce_numeric_value(value)
    if numeric_value is None:
        return True
    return _violates_minimum(numeric_value, rule) or _violates_maximum(
        numeric_value, rule
    )


def _pattern_rule_violated(value: object, rule: FieldValidation) -> bool:
    import re

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


def _smiles_rule_violated(record: JsonDict, value: object) -> bool:
    from bioetl.domain.validation.chemical import validate_smiles

    del record
    return value is not None and not validate_smiles(str(value))


def _target_organism_rule_violated(record: JsonDict, value: object) -> bool:
    return validate_target_organism_rule_violated(record, value)


def _hierarchy_no_self_reference_rule_violated(
    record: JsonDict,
    value: object,
) -> bool:
    del value
    return _custom_cross_rule_violated(record, "validate_hierarchy_no_self_reference")


_SPECIAL_CUSTOM_RULE_EVALUATORS = {
    "smiles_validator": _smiles_rule_violated,
    "validate_target_organism_supported_name": _target_organism_rule_violated,
    "validate_hierarchy_no_self_reference": _hierarchy_no_self_reference_rule_violated,
}


def _custom_rule_violated(
    record: JsonDict,
    value: object,
    validator_name: str | None,
) -> bool:
    special_evaluator = _SPECIAL_CUSTOM_RULE_EVALUATORS.get(validator_name)
    if special_evaluator is not None:
        return special_evaluator(record, value)

    strategy = _resolve_custom_validation_strategy(validator_name)
    if strategy is not None:
        return strategy(value, validator_name)

    raise ValidationError(
        f"Unknown custom validator: {validator_name!r}", field="validator"
    )


def _custom_cross_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation | str | None,
) -> bool:
    if isinstance(rule, str) or rule is None:
        if rule == "validate_hierarchy_no_self_reference":
            protein_class_id = record.get("protein_class_id")
            parent_id = record.get("parent_id")
            return _is_present(protein_class_id) and protein_class_id == parent_id
        return False
    return _custom_cross_rule_violated_impl(record, rule)


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
    "equality": _equality_rule_violated,
    "mutually_exclusive": _mutually_exclusive_rule_violated,
    "conditional_required": _conditional_required_rule_violated,
    "custom": _custom_cross_field_rule_violated,
}


__all__ = [
    "_conditional_matches",
    "_cross_rule_violated",
    "_field_rule_violated",
]
