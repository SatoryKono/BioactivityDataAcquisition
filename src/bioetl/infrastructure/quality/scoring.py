"""Scoring calculation logic for debt scorecard budget evaluation."""

from __future__ import annotations

from collections import Counter

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import _parse_quarter_label


def compute_integral_debt_score(
    *,
    total_exemptions: int,
    expired_entries: int,
    baseline_total: int,
) -> float:
    """Compute integral debt score (0..100), higher is better.

    Returns:
        Float score in range 0..100 representing debt health, higher is better.
    """
    if baseline_total <= 0:
        # Zero baseline with zero exemptions means zero debt — perfect score.
        return 100.0 if total_exemptions <= 0 else 0.0

    debt_reduction_component = max(
        0.0,
        min(100.0, 100.0 - (total_exemptions / baseline_total) * 100.0),
    )
    if total_exemptions <= 0:
        expiry_health_component = 100.0
    else:
        expiry_health_component = max(
            0.0,
            100.0 - (expired_entries / total_exemptions) * 100.0,
        )
    return round((0.7 * expiry_health_component) + (0.3 * debt_reduction_component), 2)


def _compute_group_counts(
    *,
    by_registry: dict[str, int],
    registry_groups: JsonDict,  # Any: YAML values are heterogeneous
) -> dict[str, int]:
    by_group: dict[str, int] = {}
    for group_name, group_cfg in sorted(registry_groups.items()):
        registries = group_cfg["registries"]
        by_group[group_name] = sum(by_registry.get(name, 0) for name in registries)
    return by_group


def _evaluate_registry_budgets(
    *,
    by_registry: dict[str, int],
    target_registry_budgets: dict[str, int],
    allowance_by_registry: Counter[str],
) -> list[str]:
    violations: list[str] = []
    for registry_name, current_count in sorted(by_registry.items()):
        budget = int(
            target_registry_budgets[registry_name]
        ) + allowance_by_registry.get(registry_name, 0)
        if current_count > budget:
            violations.append(
                f"registry '{registry_name}' count {current_count} exceeds budget {budget}"
            )
    return violations


def _evaluate_group_budgets(
    *,
    by_group: dict[str, int],
    target_group_budgets: dict[str, int],
    allowance_by_group: Counter[str],
) -> list[str]:
    violations: list[str] = []
    for group_name, group_count in sorted(by_group.items()):
        group_budget = int(target_group_budgets[group_name]) + allowance_by_group.get(
            group_name, 0
        )
        if group_count > group_budget:
            violations.append(
                f"group '{group_name}' count {group_count} exceeds budget {group_budget}"
            )
    return violations


def _owner_allocations_for_quarter(
    *,
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
    quarter: str,
) -> dict[str, int]:
    targets = scorecard.get("owner_decomposition_targets", [])
    if not isinstance(targets, list):
        return {}
    for item in targets:
        if not isinstance(item, dict) or item.get("quarter") != quarter:
            continue
        allocations = item.get("allocations")
        if not isinstance(allocations, dict):
            return {}
        parsed_allocations: dict[str, int] = {}
        for owner, value in allocations.items():
            if isinstance(owner, str) and isinstance(value, int):
                parsed_allocations[owner] = value
        return parsed_allocations
    return {}


def _evaluate_owner_allocations(
    *,
    by_owner: dict[str, int],
    allocations: dict[str, int],
    quarter: str,
) -> list[str]:
    violations: list[str] = []
    for owner, count in sorted(by_owner.items()):
        if owner == "<missing>":
            continue
        budget = allocations.get(owner, 0)
        if count > budget:
            violations.append(
                f"owner '{owner}' count {count} exceeds allocation {budget} "
                f"for quarter {quarter}"
            )
    return violations


def _extract_diversification_policy(
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
) -> tuple[str, int] | None:
    """Extract starts_quarter and min_distinct_owners from scorecard, or None if invalid."""
    governance = scorecard.get("governance", {})
    if not isinstance(governance, dict):
        return None
    policy = governance.get("owner_diversification", {})
    if not isinstance(policy, dict):
        return None
    starts_quarter = policy.get("starts_quarter")
    min_distinct = policy.get("min_distinct_owners")
    if not isinstance(starts_quarter, str) or not isinstance(min_distinct, int):
        return None
    return (starts_quarter, min_distinct) if min_distinct >= 1 else None


def _evaluate_owner_diversification(
    *,
    by_owner: dict[str, int],
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
    quarter: str,
) -> list[str]:
    """Validate active owner count against diversification policy.

    Returns:
        List of violation message strings, empty if policy is satisfied.
    """
    extracted = _extract_diversification_policy(scorecard)
    if extracted is None:
        return []
    starts_quarter, min_distinct_owners = extracted

    current = _parse_quarter_label(quarter)
    starts_at = _parse_quarter_label(starts_quarter)
    if current is None or starts_at is None or current < starts_at:
        return []

    active_owner_count = sum(
        1 for owner, count in by_owner.items() if owner != "<missing>" and count > 0
    )
    if active_owner_count == 0:
        return []
    if active_owner_count >= min_distinct_owners:
        return []
    return [
        "owner diversification violated: "
        f"active owners {active_owner_count} < required {min_distinct_owners} "
        f"for quarter {quarter} (starts={starts_quarter})"
    ]


def _expiry_cap_for_quarter(
    *,
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
    quarter: str,
) -> int | None:
    targets = scorecard.get("expiry_decomposition_targets", [])
    if not isinstance(targets, list):
        return None
    for item in targets:
        if not isinstance(item, dict) or item.get("quarter") != quarter:
            continue
        cap = item.get("max_entries_expiring_in_quarter")
        if isinstance(cap, int):
            return cap
        return None
    return None


def _evaluate_expiry_cap(
    *,
    by_expiry_quarter: dict[str, int],
    quarter: str,
    cap: int | None,
) -> list[str]:
    if cap is None:
        return []
    expiring_count = by_expiry_quarter.get(quarter, 0)
    if expiring_count <= cap:
        return []
    return [
        f"expiry quarter '{quarter}' count {expiring_count} exceeds cap {cap}",
    ]


def _check_done_threshold(
    criteria: dict[str, object],
    key: str,
    actual: int | float,
    comparator: str,
) -> str | None:
    """Check a single program-done threshold and return violation message or None."""
    threshold = criteria.get(key)
    if comparator == "max" and isinstance(threshold, int) and actual > threshold:
        return f"program done criteria violated: {key} {actual} exceeds {threshold}"
    if (
        comparator == "min"
        and isinstance(threshold, (int, float))
        and actual < float(threshold)
    ):
        return f"program done criteria violated: {key} {actual} is below {float(threshold)}"
    return None


def _evaluate_program_done_criteria(
    *,
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
    current_quarter: str,
    total_exemptions: int,
    integral_score: float,
    expired_entries: int,
) -> list[str]:
    criteria = scorecard.get("program_done_criteria")
    if not isinstance(criteria, dict):
        return []

    current_tuple = _parse_quarter_label(current_quarter)
    deadline_quarter = criteria.get("deadline_quarter")
    deadline_tuple = (
        _parse_quarter_label(deadline_quarter)
        if isinstance(deadline_quarter, str)
        else None
    )
    if (
        current_tuple is None
        or deadline_tuple is None
        or current_tuple < deadline_tuple
    ):
        return []

    checks = [
        _check_done_threshold(
            criteria, "max_total_exemptions", total_exemptions, "max"
        ),
        _check_done_threshold(criteria, "min_integral_score", integral_score, "min"),
        _check_done_threshold(criteria, "max_expired_entries", expired_entries, "max"),
    ]
    return [msg for msg in checks if msg is not None]


__all__ = [
    "_compute_group_counts",
    "_evaluate_expiry_cap",
    "_evaluate_group_budgets",
    "_evaluate_owner_allocations",
    "_evaluate_owner_diversification",
    "_evaluate_program_done_criteria",
    "_evaluate_registry_budgets",
    "_expiry_cap_for_quarter",
    "_owner_allocations_for_quarter",
    "compute_integral_debt_score",
]
