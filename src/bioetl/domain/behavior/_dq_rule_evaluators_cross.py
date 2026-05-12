"""Cross-field rule evaluator functions.

Extracted from _dq_rule_evaluators.py to meet file size limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    from bioetl.domain.behavior._dq_rule_evaluators import _is_present

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
    from bioetl.domain.behavior._dq_rule_evaluators import _custom_cross_rule_violated

    del present_count
    return _custom_cross_rule_violated(record, rule.validator)


__all__ = [
    "_all_present_rule_violated",
    "_any_present_rule_violated",
    "_conditional_required_rule_violated",
    "_custom_cross_field_rule_violated",
    "_mutually_exclusive_rule_violated",
]
