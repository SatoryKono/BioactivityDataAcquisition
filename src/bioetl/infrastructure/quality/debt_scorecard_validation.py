"""Validation helpers for debt scorecard schema/governance checks.

This module orchestrates section-level validators that live in dedicated
sub-modules (_primitives, _baseline_validation, _governance_validation,
_quarterly_targets_validation, _grace_windows_validation,
_decomposition_validation).  It re-exports the public API so that
existing call-sites continue to work without changes.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._baseline_validation import (
    _validate_baseline_section,
    _validate_historical_baseline_section,
    _validate_registry_groups_section,
)
from bioetl.infrastructure.quality._decomposition_validation import (
    _validate_expiry_decomposition_targets_section,
    _validate_owner_decomposition_targets_section,
    _validate_owner_diversification_policy,
    _validate_priority_registry_burndown,
    _validate_program_done_criteria_section,
)
from bioetl.infrastructure.quality._governance_validation import (
    _validate_governance_section,
)
from bioetl.infrastructure.quality._grace_windows_validation import (
    _validate_grace_windows_section,
)
from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
)
from bioetl.infrastructure.quality._quarterly_targets_validation import (
    _validate_quarterly_targets_section,
)


def validate_debt_scorecard_structure(
    raw: JsonDict,
) -> list[str]:
    """Validate debt scorecard schema and monotonic governance targets.

    Returns:
        List of validation error message strings, empty if the scorecard structure is valid.
    """
    errors: list[str] = []

    schema_version = raw.get("schema_version")
    if schema_version != 1:
        errors.append(f"schema_version must be 1, got {schema_version!r}")

    baseline_result = _validate_baseline_section(raw, errors)
    if baseline_result is None:
        return errors
    baseline_total, normalized_registry_counts = baseline_result

    _validate_historical_baseline_section(
        raw,
        enforceable_total=baseline_total,
        enforceable_registry_counts=normalized_registry_counts,
        errors=errors,
    )

    baseline_registry_names = set(normalized_registry_counts)
    normalized_groups = _validate_registry_groups_section(
        raw,
        baseline_registry_names=baseline_registry_names,
        errors=errors,
    )
    if not normalized_groups:
        return errors

    allow_rf_only_for_rf = _validate_governance_section(
        raw,
        baseline_registry_names=baseline_registry_names,
        group_names=set(normalized_groups),
        errors=errors,
    )

    _validate_quarterly_targets_section(
        raw,
        group_names=set(normalized_groups),
        baseline_registry_names=baseline_registry_names,
        errors=errors,
    )
    quarter_budget_map = {
        str(item["quarter"]): int(item["max_total_exemptions"])
        for item in raw.get("quarterly_targets", [])
        if isinstance(item, dict)
        and isinstance(item.get("quarter"), str)
        and isinstance(item.get("max_total_exemptions"), int)
    }
    owner_div_start, min_distinct_owners = _validate_owner_diversification_policy(
        raw,
        errors,
    )
    _validate_owner_decomposition_targets_section(
        raw,
        quarter_budget_map=quarter_budget_map,
        owner_diversification_start=owner_div_start,
        min_distinct_owners=min_distinct_owners,
        errors=errors,
    )
    _validate_expiry_decomposition_targets_section(raw, errors)
    _validate_priority_registry_burndown(
        raw,
        baseline_registry_names=baseline_registry_names,
        errors=errors,
    )
    _validate_program_done_criteria_section(raw, errors)
    _validate_grace_windows_section(
        raw,
        baseline_registry_names=baseline_registry_names,
        group_names=set(normalized_groups),
        allow_rf_only_for_rf=allow_rf_only_for_rf,
        errors=errors,
    )

    return errors


validate_debt_scorecard_raw = validate_debt_scorecard_structure

# Re-export _parse_iso_date for backward compatibility (used by debt_scorecard.py).
__all__ = [
    "_parse_iso_date",
    "validate_debt_scorecard_raw",
    "validate_debt_scorecard_structure",
]
