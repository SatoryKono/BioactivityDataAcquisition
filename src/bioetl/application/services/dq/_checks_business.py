"""Business rules DQ checks for Gold layer.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

__all__ = ["check_business_rules"]


from collections.abc import Mapping, Sequence

import polars as pl

from bioetl.domain.types import GOLD_CONTRACT_VERSION_UNKNOWN, GoldBusinessRuleSpec
from bioetl.domain.value_objects.dq_report import (
    BusinessRuleResult,
    BusinessRulesResult,
    DQCheckStatus,
)

_BUSINESS_RULE_EVALUATION_ERRORS = (
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
)


def _check_not_null_rule(df: pl.DataFrame, column: str) -> tuple[bool, int | None]:
    """Check not_null rule for a column."""
    violations = df[column].null_count()
    return violations == 0, violations


def _check_range_rule(
    df: pl.DataFrame,
    column: str,
    min_val: object | None,
    max_val: object | None,
) -> tuple[bool, int]:
    """Check range rule for a column."""
    violations = 0
    col_data = df[column].drop_nulls()
    if min_val is not None:
        violations += int((col_data < min_val).sum())
    if max_val is not None:
        violations += int((col_data > max_val).sum())
    return violations == 0, violations


def _check_in_list_rule(
    df: pl.DataFrame,
    column: str,
    allowed: tuple[object, ...],
) -> tuple[bool, int | None]:
    """Check in_list rule for a column."""
    if not allowed:
        return True, 0
    violations = int((~df[column].is_in(allowed)).sum())
    return violations == 0, violations


def _check_regex_rule(
    df: pl.DataFrame, column: str, pattern: str
) -> tuple[bool, int | None]:
    """Check regex rule for a column."""
    if not pattern:
        return True, 0
    violations = int((~df[column].str.contains(pattern, literal=False)).sum())
    return violations == 0, violations


def _evaluate_single_rule(
    df: pl.DataFrame,
    rule: GoldBusinessRuleSpec,
) -> tuple[bool, int | None]:
    """Evaluate a single business rule."""
    column = rule.column
    condition = rule.condition

    if not column or column not in df.columns:
        return True, 0

    if condition == "not_null":
        return _check_not_null_rule(df, column)
    if condition == "range":
        return _check_range_rule(df, column, rule.minimum, rule.maximum)
    if condition == "in_list":
        return _check_in_list_rule(df, column, rule.allowed_values)
    if condition == "regex":
        return _check_regex_rule(df, column, rule.pattern or "")
    return True, 0


def _normalize_business_rule(
    raw_rule: GoldBusinessRuleSpec | Mapping[str, object],
    *,
    contract_version: str | None,
) -> GoldBusinessRuleSpec:
    if isinstance(raw_rule, GoldBusinessRuleSpec):
        return raw_rule
    return GoldBusinessRuleSpec.from_mapping(
        raw_rule,
        default_contract_version=contract_version,
    )


def _evaluate_rule_outcome(
    df: pl.DataFrame,
    rule: GoldBusinessRuleSpec,
) -> tuple[bool, int | None]:
    try:
        return _evaluate_single_rule(df, rule)
    except _BUSINESS_RULE_EVALUATION_ERRORS:
        # Catch all: rule evaluation may fail due to missing columns, type errors,
        # or malformed rule expressions. Treat as rule failure for DQ reporting.
        return False, None


def _rule_decision_for_result(
    rule: GoldBusinessRuleSpec,
    *,
    passed: bool,
) -> str:
    return rule.decision or ("pass" if passed else "fail")


def _build_rule_result(
    rule: GoldBusinessRuleSpec,
    *,
    column: str,
    passed: bool,
    violations: int | None,
) -> BusinessRuleResult:
    decision = _rule_decision_for_result(rule, passed=passed)
    reject_reason = (
        None
        if passed or decision in {"pass", "warn"}
        else rule.build_reject_reason(violations=violations)
    )
    return BusinessRuleResult(
        rule_id=rule.rule_id,
        name=rule.name,
        description=rule.description,
        passed=passed,
        violations=violations,
        config_path=rule.config_path,
        layer=rule.layer,
        field=rule.field or column,
        severity=rule.severity,
        decision=decision,
        reject_reason=reject_reason,
    )


def check_business_rules(
    df: pl.DataFrame,
    rules: Sequence[GoldBusinessRuleSpec | Mapping[str, object]],
    *,
    contract_version: str | None = GOLD_CONTRACT_VERSION_UNKNOWN,
) -> BusinessRulesResult:
    """Validate business rules.

    Args:
        df: Input DataFrame.
        rules: Rules.
        contract_version: Gold contract version used for default reject payloads.

    Returns:
        Check result as BusinessRulesResult.
    """
    if not rules:
        return BusinessRulesResult(
            rules_evaluated=0,
            rules_passed=0,
            rules_failed=0,
            rules=(),
            status=DQCheckStatus.PASS,
        )

    results = []
    rules_passed = 0
    rules_failed = 0

    for raw_rule in rules:
        rule = _normalize_business_rule(
            raw_rule,
            contract_version=contract_version,
        )
        column = rule.column
        passed, violations = _evaluate_rule_outcome(df, rule)

        if passed:
            rules_passed += 1
        else:
            rules_failed += 1

        results.append(
            _build_rule_result(
                rule,
                column=column,
                passed=passed,
                violations=violations,
            )
        )

    status = DQCheckStatus.PASS if rules_failed == 0 else DQCheckStatus.FAIL

    return BusinessRulesResult(
        rules_evaluated=len(rules),
        rules_passed=rules_passed,
        rules_failed=rules_failed,
        rules=tuple(results),
        status=status,
    )
