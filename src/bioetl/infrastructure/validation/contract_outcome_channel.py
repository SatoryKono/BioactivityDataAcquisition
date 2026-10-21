"""Sync outcome channel for contract-aware validators.

Validators stay synchronous. This module turns Pandera failures and the
loaded contract-rule bundle into attributed ``DQRuleOutcome`` values.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.behavior.dq_contract_rule_source import (
    load_executable_contract_rules,
)
from bioetl.domain.behavior.dq_rule_evaluator import evaluate_dq_rules_for_record
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.domain.types.dq_record_attribution import (
    AttributedDQViolation,
    DQOutcomeChannel,
    DQRecordIdentity,
    record_identity,
    sort_attributed_violations,
)

if TYPE_CHECKING:
    from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
    from bioetl.domain.config.dq import DQConfig
    from bioetl.domain.types import JsonDict

__all__ = [
    "attribute_contract_rules",
    "build_outcome_channel",
    "schema_error_field_name",
    "schema_error_severity",
    "schema_violations_from_error",
]


def schema_error_severity(error: Exception) -> str:
    """Map a Pandera error message onto the resolver severity scale."""
    text = str(error).lower()
    if "null" in text or "type" in text:
        return "high"
    if "regex" in text or any(marker in text for marker in ("range", "min", "max")):
        return "medium"
    return "high"


def schema_error_field_name(error: Exception) -> str | None:
    """Best-effort field name from a Pandera error. Not a row identity."""
    column_name = getattr(error, "column_name", None)
    if isinstance(column_name, str) and column_name:
        return column_name
    failure_cases = getattr(error, "failure_cases", None)
    if isinstance(failure_cases, str) and failure_cases:
        return failure_cases
    loc = getattr(error, "loc", None)
    if loc:
        if isinstance(loc, str):
            return loc
        return ".".join(str(item) for item in loc)
    message = str(error)
    marker = "column '"
    if marker in message:
        _, _, tail = message.partition(marker)
        column_name, _, _ = tail.partition("'")
        if column_name:
            return column_name
    return None


def attribute_contract_rules(
    records: list[JsonDict],
    dq_config: DQConfig | None,
) -> tuple[AttributedDQViolation, ...]:
    """Evaluate the loaded contract-rule bundle once per normalized record."""
    rules = load_executable_contract_rules(dq_config)
    if dq_config is None or rules.is_empty:
        return ()
    violations: list[AttributedDQViolation] = []
    for source_index, record in enumerate(records):
        identity = record_identity(record, source_index)
        for outcome in evaluate_dq_rules_for_record(record, dq_config):
            violations.append(AttributedDQViolation(outcome=outcome, record=identity))
    return sort_attributed_violations(violations)


def schema_violations_from_error(
    error: Exception,
    *,
    records: list[JsonDict],
    resolver: DQPolicyResolver,
    config_path: str | None,
) -> list[AttributedDQViolation]:
    """Convert one Pandera failure into attributed schema outcomes."""
    from pandera.errors import SchemaErrors

    if isinstance(error, SchemaErrors):
        violations: list[AttributedDQViolation] = []
        for schema_error in error.schema_errors:
            violations.extend(
                _violations_for_schema_error(
                    schema_error,
                    records=records,
                    resolver=resolver,
                    config_path=config_path,
                )
            )
        return violations
    return [
        _unscoped_schema_violation(
            error,
            resolver=resolver,
            config_path=config_path,
        )
    ]


def build_outcome_channel(
    *,
    records: list[JsonDict],
    schema: object | None,
    strict: bool,
    dq_config: DQConfig | None,
    resolver: DQPolicyResolver | None,
    config_path: str | None,
    prepare_frame: Callable[[object], object],
    rule_records: list[JsonDict] | None = None,
) -> DQOutcomeChannel:
    """Run schema and contract rules and return a sorted outcome channel."""
    if resolver is None or dq_config is None:
        return DQOutcomeChannel(is_valid=True, outcomes=(), violations=())
    if not records:
        return DQOutcomeChannel(is_valid=True, outcomes=(), violations=())
    if schema is None:
        if not strict:
            return DQOutcomeChannel(is_valid=True, outcomes=(), violations=())
        missing = _schema_missing_violation(
            resolver=resolver,
            config_path=config_path,
        )
        return _channel_from_violations((missing,))

    import pandas as pd

    if rule_records is not None and len(rule_records) != len(records):
        raise ValueError("Gold rule inputs must retain projected row alignment")
    frame = pd.DataFrame(records)
    prepared = prepare_frame(frame)
    violations = list(
        attribute_contract_rules(
            records if rule_records is None else rule_records, dq_config
        )
    )
    schema_error = _collect_schema_error(schema, prepared)
    if schema_error is not None:
        violations.extend(
            schema_violations_from_error(
                schema_error,
                records=records,
                resolver=resolver,
                config_path=config_path,
            )
        )
    return _channel_from_violations(sort_attributed_violations(violations))


def _channel_from_violations(
    violations: tuple[AttributedDQViolation, ...],
) -> DQOutcomeChannel:
    outcomes = tuple(item.outcome for item in violations)
    blocked = any(
        outcome.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
        for outcome in outcomes
    )
    return DQOutcomeChannel(
        is_valid=not blocked,
        outcomes=outcomes,
        violations=violations,
    )


def _schema_missing_violation(
    *,
    resolver: DQPolicyResolver,
    config_path: str | None,
) -> AttributedDQViolation:
    outcome = resolver.create_rule_outcome(
        rule_id="schema.missing",
        violation_kind=DQViolationKind.SCHEMA_VIOLATION,
        severity="high",
        affected_fields=None,
        config_path=config_path,
        threshold_breach=False,
        anomaly_signal=False,
    )
    return AttributedDQViolation(outcome=outcome, record=None)


def _collect_schema_error(schema: object, frame: object) -> Exception | None:
    from pandera.errors import SchemaError, SchemaErrors

    validate = getattr(schema, "validate", None)
    if not callable(validate):
        return TypeError("schema does not provide validate()")
    try:
        validate(frame, lazy=True)
    except (SchemaError, SchemaErrors, KeyError, TypeError, ValueError) as error:
        return error
    return None


def _violations_for_schema_error(
    error: Exception,
    *,
    records: list[JsonDict],
    resolver: DQPolicyResolver,
    config_path: str | None,
) -> list[AttributedDQViolation]:
    indexes = _failure_row_indexes(getattr(error, "failure_cases", None))
    if not indexes:
        return [
            _unscoped_schema_violation(
                error,
                resolver=resolver,
                config_path=config_path,
            )
        ]
    field_name = schema_error_field_name(error)
    severity = schema_error_severity(error)
    violations: list[AttributedDQViolation] = []
    for source_index in indexes:
        outcome = _schema_outcome(
            resolver=resolver,
            field_name=field_name,
            severity=severity,
            config_path=config_path,
        )
        violations.append(
            AttributedDQViolation(
                outcome=outcome,
                record=_identity_for_index(records, source_index),
            )
        )
    return violations


def _unscoped_schema_violation(
    error: Exception,
    *,
    resolver: DQPolicyResolver,
    config_path: str | None,
) -> AttributedDQViolation:
    outcome = _schema_outcome(
        resolver=resolver,
        field_name=schema_error_field_name(error),
        severity=schema_error_severity(error),
        config_path=config_path,
    )
    return AttributedDQViolation(outcome=outcome, record=None)


def _schema_outcome(
    *,
    resolver: DQPolicyResolver,
    field_name: str | None,
    severity: str,
    config_path: str | None,
) -> DQRuleOutcome:
    return resolver.create_rule_outcome(
        rule_id=f"schema.{field_name or 'unknown'}",
        violation_kind=DQViolationKind.SCHEMA_VIOLATION,
        severity=severity,
        affected_fields=[field_name] if field_name else None,
        config_path=config_path,
        threshold_breach=False,
        anomaly_signal=False,
    )


def _identity_for_index(
    records: list[JsonDict],
    source_index: int | None,
) -> DQRecordIdentity | None:
    if source_index is None or source_index >= len(records):
        return None
    return record_identity(records[source_index], source_index)


def _failure_row_indexes(failure_cases: object) -> list[int | None] | None:
    columns = getattr(failure_cases, "columns", None)
    iterrows = getattr(failure_cases, "iterrows", None)
    if columns is None or not callable(iterrows):
        return None
    if "index" not in list(columns):
        return []
    indexes: list[int | None] = []
    for _, row in iterrows():
        indexes.append(_coerce_row_index(row["index"]))
    return indexes


def _coerce_row_index(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or not value.is_integer():
            return None
        return int(value)
    item = getattr(value, "item", None)
    if not callable(item):
        return None
    try:
        return _coerce_row_index(item())
    except (TypeError, ValueError):
        return None
