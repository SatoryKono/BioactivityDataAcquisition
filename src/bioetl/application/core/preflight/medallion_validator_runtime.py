"""Pure validation helpers for medallion preflight rules."""

from __future__ import annotations

from bioetl.application.core.preflight.medallion_validator_idempotency import (
    validate_idempotency_contracts,
)
from bioetl.domain.exceptions import PolicyViolationError
from bioetl.domain.medallion import Layer, MedallionPolicy, WriteMode, WriteModePolicy
from bioetl.domain.types import ConfigValidationError, RunType

_LAYER_PATHS_FIELD = "storage.paths"
_UNIQUE_LAYER_PATHS_EXPECTED = "unique paths for each layer"
_DISTINCT_LAYER_PATHS_RULE = "Medallion Architecture: layers MUST have distinct paths"


def validate_single_write_mode(
    *,
    write_mode_policy: WriteModePolicy,
    layer: Layer,
    mode_value: str,
    field: str,
    rule: str,
    actual_mode: str | None = None,
    expected_suffix: str = "",
) -> list[ConfigValidationError]:
    """Validate one configured write mode against policy."""
    try:
        write_mode_policy.validate(layer, WriteMode(mode_value))
    except (PolicyViolationError, ValueError):
        allowed = WriteModePolicy.ALLOWED_MODES[layer]
        allowed_names = ", ".join(
            mode.value for mode in sorted(allowed, key=lambda item: item.value)
        )
        return [
            ConfigValidationError(
                field=field,
                expected=f"one of: {allowed_names}{expected_suffix}",
                actual=actual_mode or mode_value,
                rule=rule,
            )
        ]
    return []


def validate_layer_formats(
    *,
    silver_format: str | None,
    gold_format: str | None,
) -> list[ConfigValidationError]:
    """Validate medallion sink formats."""
    errors: list[ConfigValidationError] = []
    if silver_format is not None and silver_format != "delta":
        errors.append(
            ConfigValidationError(
                field="sink.silver.format",
                expected="delta",
                actual=silver_format,
                rule="RULES §2.1: Silver MUST use Delta Lake",
            )
        )
    if gold_format is not None and gold_format != "delta":
        errors.append(
            ConfigValidationError(
                field="sink.gold.format",
                expected="delta",
                actual=gold_format,
                rule="RULES §2.1: Gold MUST use Delta Lake",
            )
        )
    return errors


def validate_path_uniqueness(
    *,
    bronze_path: str,
    silver_path: str,
    gold_path: str,
) -> list[ConfigValidationError]:
    """Validate that bronze/silver/gold use distinct paths."""
    errors: list[ConfigValidationError] = []
    paths = {bronze_path, silver_path, gold_path}
    if len(paths) >= 3:
        return errors
    if bronze_path == silver_path:
        errors.append(
            ConfigValidationError(
                field=_LAYER_PATHS_FIELD,
                expected=_UNIQUE_LAYER_PATHS_EXPECTED,
                actual=f"bronze_path == silver_path ({bronze_path})",
                rule=_DISTINCT_LAYER_PATHS_RULE,
            )
        )
    if silver_path == gold_path:
        errors.append(
            ConfigValidationError(
                field=_LAYER_PATHS_FIELD,
                expected=_UNIQUE_LAYER_PATHS_EXPECTED,
                actual=f"silver_path == gold_path ({silver_path})",
                rule=_DISTINCT_LAYER_PATHS_RULE,
            )
        )
    if bronze_path == gold_path:
        errors.append(
            ConfigValidationError(
                field=_LAYER_PATHS_FIELD,
                expected=_UNIQUE_LAYER_PATHS_EXPECTED,
                actual=f"bronze_path == gold_path ({bronze_path})",
                rule=_DISTINCT_LAYER_PATHS_RULE,
            )
        )
    return errors


def validate_medallion_policy_consistency(
    *,
    run_type: RunType,
    policy: MedallionPolicy,
) -> list[ConfigValidationError]:
    """Validate clear/no-clear invariants implied by run type."""
    errors: list[ConfigValidationError] = []
    if run_type in (RunType.REBUILD, RunType.BACKFILL):
        if not policy.should_clear_silver:
            errors.append(
                ConfigValidationError(
                    field="medallion_policy.should_clear_silver",
                    expected="True",
                    actual="False",
                    rule=f"RULES §2.1: {run_type.value} MUST clear Silver layer",
                )
            )
        if not policy.should_clear_gold:
            errors.append(
                ConfigValidationError(
                    field="medallion_policy.should_clear_gold",
                    expected="True",
                    actual="False",
                    rule=f"RULES §2.1: {run_type.value} MUST clear Gold layer",
                )
            )
        return errors
    if run_type == RunType.INCREMENTAL:
        if policy.should_clear_silver:
            errors.append(
                ConfigValidationError(
                    field="medallion_policy.should_clear_silver",
                    expected="False",
                    actual="True",
                    rule="RULES §2.1: INCREMENTAL MUST NOT clear Silver layer",
                )
            )
        if policy.should_clear_gold:
            errors.append(
                ConfigValidationError(
                    field="medallion_policy.should_clear_gold",
                    expected="False",
                    actual="True",
                    rule="RULES §2.1: INCREMENTAL MUST NOT clear Gold layer",
                )
            )
    return errors


def validate_key_nullability_policies(
    *,
    primary_keys: list[str],
    partition_cols: list[str],
    key_nullability_rules: list[object],
) -> list[ConfigValidationError]:
    """Validate that DQ key-nullability rules reference merge/partition keys only."""
    errors: list[ConfigValidationError] = []
    valid_keys = set(primary_keys) | set(partition_cols)
    for rule in key_nullability_rules:
        field = getattr(rule, "field", None)
        if field in valid_keys:
            continue
        errors.append(
            ConfigValidationError(
                field="dq.key_nullability",
                expected="rule field must be present in primary_keys or partition_cols",
                actual=str(field),
                rule="DQ key policy: key_nullability rules apply only to merge/partition keys",
            )
        )
    return errors


__all__ = [
    "validate_idempotency_contracts",
    "validate_key_nullability_policies",
    "validate_layer_formats",
    "validate_medallion_policy_consistency",
    "validate_path_uniqueness",
    "validate_single_write_mode",
]
