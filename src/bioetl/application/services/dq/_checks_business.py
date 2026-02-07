"""Business rules DQ checks for Gold layer.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from bioetl.domain.value_objects.dq_report import (
    BusinessRuleResult,
    BusinessRulesResult,
    DQCheckStatus,
)


def _check_not_null_rule(df: pl.DataFrame, column: str) -> tuple[bool, int | None]:
    """Check not_null rule for a column."""
    violations = df[column].null_count()
    return violations == 0, violations


def _check_range_rule(
    df: pl.DataFrame,
    column: str,
    min_val: Any | None,
    max_val: Any | None,
) -> tuple[bool, int]:
    """Check range rule for a column."""
    violations = 0
    col_data = df[column].drop_nulls()
    if min_val is not None:
        violations += (col_data < min_val).sum()
    if max_val is not None:
        violations += (col_data > max_val).sum()
    return violations == 0, violations


def _check_in_list_rule(
    df: pl.DataFrame, column: str, allowed: list[Any]
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
    df: pl.DataFrame, rule: dict[str, Any]
) -> tuple[bool, int | None]:
    """Evaluate a single business rule."""
    column = rule.get("column")
    condition = rule.get("condition")

    if not column or column not in df.columns:
        return True, 0

    if condition == "not_null":
        return _check_not_null_rule(df, column)
    if condition == "range":
        return _check_range_rule(df, column, rule.get("min"), rule.get("max"))
    if condition == "in_list":
        return _check_in_list_rule(df, column, rule.get("values", []))
    if condition == "regex":
        return _check_regex_rule(df, column, rule.get("pattern", ""))
    return True, 0


def check_business_rules(
    df: pl.DataFrame, rules: list[dict[str, Any]]
) -> BusinessRulesResult:
    """Validate business rules."""
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

    for rule in rules:
        try:
            passed, violations = _evaluate_single_rule(df, rule)
        except Exception:
            passed, violations = False, None

        if passed:
            rules_passed += 1
        else:
            rules_failed += 1

        results.append(
            BusinessRuleResult(
                rule_id=rule.get("rule_id", ""),
                name=rule.get("name", ""),
                description=rule.get("description", ""),
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
