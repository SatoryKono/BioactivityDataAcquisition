"""Cross-field rule evaluator functions.

Extracted from _dq_rule_evaluators.py to meet file size limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.behavior._dq_value_coercion import _is_present
from bioetl.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from bioetl.domain.config.validation import CrossFieldValidation
    from bioetl.domain.types import JsonDict


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


def _alias_equality_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
) -> bool:
    present_values = [
        record.get(field) for field in rule.fields if _is_present(record.get(field))
    ]
    if len(present_values) <= 1:
        return False

    first_value = present_values[0]
    return any(value != first_value for value in present_values[1:])


def _equality_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
    present_count: int,
) -> bool:
    del present_count
    return _alias_equality_rule_violated(record, rule)


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


def _custom_cross_rule_violated_impl(
    record: JsonDict,
    rule: CrossFieldValidation,
) -> bool:
    if rule.validator == "validate_hierarchy_no_self_reference":
        protein_class_id = record.get("protein_class_id")
        parent_id = record.get("parent_id")
        return _is_present(protein_class_id) and protein_class_id == parent_id
    if rule.validator == "validate_alias_equality":
        return _alias_equality_rule_violated(record, rule)
    raise ValidationError(
        f"Unknown custom cross-field validator: {rule.validator!r}",
        field="validator",
    )


def _custom_cross_field_rule_violated(
    record: JsonDict,
    rule: CrossFieldValidation,
    present_count: int,
) -> bool:
    del present_count
    return _custom_cross_rule_violated_impl(record, rule)


__all__ = [
    "_all_present_rule_violated",
    "_any_present_rule_violated",
    "_conditional_required_rule_violated",
    "_custom_cross_field_rule_violated",
    "_custom_cross_rule_violated_impl",
    "_equality_rule_violated",
    "_mutually_exclusive_rule_violated",
]
