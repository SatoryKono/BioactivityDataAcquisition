"""Key nullability validation operations for Silver layer.

Extracted from ``silver_writer_validation_operations`` to localise the
key-nullability enforcement axis: null counting, violation collection,
and policy error raising are isolated here so that changes to nullability
rules do not ripple through the wider validation / Arrow-preparation
pipeline.

Mirrors the established pattern of ``silver_writer_schema_drift_operations``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.types import BronzeRecord

__all__ = [
    "_collect_key_violations",
    "_count_null_violations",
    "_validate_key_nullability_impl",
]


def _count_null_violations(
    records: list[BronzeRecord],
    rules: dict[tuple[str, Literal["merge", "partition"]], KeyNullabilityRule],
    field: str,
    key_type: Literal["merge", "partition"],
) -> int:
    """Count null values for a non-nullable key field."""
    rule = rules.get((field, key_type))
    if rule is None or rule.nullable:
        return 0
    return sum(1 for record in records if record.get(field) is None)


def _collect_key_violations(
    records: list[BronzeRecord],
    rules: dict[tuple[str, Literal["merge", "partition"]], KeyNullabilityRule],
    primary_keys: list[str],
    partition_cols: list[str] | None,
) -> list[tuple[str, str, int]]:
    """Collect all nullability violations across merge and partition keys."""
    violations: list[tuple[str, str, int]] = []
    for key in primary_keys:
        if count := _count_null_violations(records, rules, key, "merge"):
            violations.append((key, "merge", count))
    for key in partition_cols or []:
        if count := _count_null_violations(records, rules, key, "partition"):
            violations.append((key, "partition", count))
    return violations


def _validate_key_nullability_impl(
    records: list[BronzeRecord],
    primary_keys: list[str],
    partition_cols: list[str] | None,
    key_nullability_rules: list[KeyNullabilityRule] | None,
    table_name: str,
) -> None:
    """Validate nullability policy for merge and partition keys."""
    if not records or not key_nullability_rules:
        return

    rules = {(rule.field, rule.key_type): rule for rule in key_nullability_rules}
    violations = _collect_key_violations(records, rules, primary_keys, partition_cols)

    if violations:
        details = [
            f"{key_type}:{field} null_count={count}"
            for field, key_type, count in violations
        ]
        raise ValueError(
            "Key nullability policy violation for table "
            f"'{table_name}': {'; '.join(details)}"
        )
