"""Owner-allocation policy helpers for debt scorecard decomposition checks."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    _parse_quarter_label,
    _validate_non_negative_int,
)


def _collect_quarterly_registry_budgets(
    raw: JsonDict,  # Any: YAML values are heterogeneous
) -> dict[str, dict[str, int]]:
    """Collect validated-looking quarterly registry budgets for monotonic checks."""
    quarterly_targets = raw.get("quarterly_targets", [])
    if not isinstance(quarterly_targets, list):
        return {}

    collected: dict[str, dict[str, int]] = {}
    for item in quarterly_targets:
        if not isinstance(item, dict):
            continue
        quarter = item.get("quarter")
        budgets = item.get("registry_budgets")
        if not isinstance(quarter, str) or not isinstance(budgets, dict):
            continue
        parsed_budgets: dict[str, int] = {}
        for registry_name, value in budgets.items():
            if isinstance(registry_name, str) and isinstance(value, int):
                parsed_budgets[registry_name] = value
        collected[quarter] = parsed_budgets
    return collected


def _validate_owner_diversification_policy(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    errors: list[str],
) -> tuple[tuple[int, int] | None, int]:
    """Validate governance.owner_diversification and return normalized settings."""
    governance = raw.get("governance", {})
    if not isinstance(governance, dict):
        return None, 1

    policy = governance.get("owner_diversification", {})
    if not isinstance(policy, dict):
        errors.append("governance.owner_diversification: expected mapping")
        return None, 1

    starts_quarter = policy.get("starts_quarter")
    parsed_starts = None
    if not isinstance(starts_quarter, str):
        errors.append(
            "governance.owner_diversification.starts_quarter: expected quarter label"
        )
    else:
        parsed_starts = _parse_quarter_label(starts_quarter)
        if parsed_starts is None:
            errors.append(
                "governance.owner_diversification.starts_quarter: expected 'YYYY-QN' format"
            )

    min_distinct = _validate_non_negative_int(
        policy.get("min_distinct_owners"),
        field_name="governance.owner_diversification.min_distinct_owners",
        errors=errors,
    )
    if min_distinct is None:
        min_distinct = 1
    if min_distinct < 1:
        errors.append(
            "governance.owner_diversification.min_distinct_owners: must be >= 1"
        )
        min_distinct = 1

    return parsed_starts, min_distinct


def _validate_target_quarter(
    item: JsonDict,  # Any: YAML values are heterogeneous
    prefix: str,
    seen_quarters: set[str],
    quarter_budget_map: dict[str, int],
    errors: list[str],
) -> tuple[str, tuple[int, int]] | None:
    """Validate quarter field of a single target entry."""
    quarter = item.get("quarter")
    if not isinstance(quarter, str):
        errors.append(f"{prefix}.quarter: expected string")
        return None
    parsed_quarter = _parse_quarter_label(quarter)
    if parsed_quarter is None:
        errors.append(f"{prefix}.quarter: expected 'YYYY-QN' format")
        return None
    if quarter in seen_quarters:
        errors.append(f"{prefix}.quarter: duplicate quarter '{quarter}'")
        return None
    if quarter not in quarter_budget_map:
        errors.append(
            f"{prefix}.quarter: unknown quarter '{quarter}' (not in quarterly_targets)"
        )
        return None
    seen_quarters.add(quarter)
    return quarter, parsed_quarter


def _parse_owner_allocations(
    item: JsonDict,  # Any: YAML values are heterogeneous
    prefix: str,
    errors: list[str],
) -> dict[str, int] | None:
    """Parse and validate allocations mapping from a target entry."""
    allocations = item.get("allocations")
    if not isinstance(allocations, dict) or not allocations:
        errors.append(f"{prefix}.allocations: expected non-empty mapping")
        return None

    parsed: dict[str, int] = {}
    for owner, value in allocations.items():
        if not isinstance(owner, str) or not owner.strip():
            errors.append(f"{prefix}.allocations: owner must be non-empty string")
            continue
        parsed_value = _validate_non_negative_int(
            value,
            field_name=f"{prefix}.allocations.{owner}",
            errors=errors,
        )
        if parsed_value is not None:
            parsed[owner] = parsed_value
    return parsed


def _validate_allocation_constraints(
    *,
    prefix: str,
    parsed_quarter: tuple[int, int],
    parsed_allocations: dict[str, int],
    quarter: str,
    quarter_budget_map: dict[str, int],
    owner_diversification_start: tuple[int, int] | None,
    min_distinct_owners: int,
    errors: list[str],
) -> None:
    """Validate allocation sum and owner diversification for a single quarter."""
    if sum(parsed_allocations.values()) != quarter_budget_map[quarter]:
        errors.append(
            f"{prefix}.allocations: sum {sum(parsed_allocations.values())} "
            f"must equal quarterly_targets[{quarter}].max_total_exemptions "
            f"{quarter_budget_map[quarter]}"
        )
    if (
        owner_diversification_start is not None
        and parsed_quarter >= owner_diversification_start
        and len(parsed_allocations) < min_distinct_owners
    ):
        errors.append(
            f"{prefix}.allocations: expected at least {min_distinct_owners} owners "
            f"starting from quarter "
            f"{owner_diversification_start[0]}-Q{owner_diversification_start[1]}"
        )


def _validate_owner_decomposition_targets_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    *,
    quarter_budget_map: dict[str, int],
    owner_diversification_start: tuple[int, int] | None,
    min_distinct_owners: int,
    errors: list[str],
) -> None:
    """Validate owner decomposition targets against quarterly max budgets."""
    targets = raw.get("owner_decomposition_targets")
    if not isinstance(targets, list) or not targets:
        errors.append("owner_decomposition_targets: required non-empty list")
        return

    seen_quarters: set[str] = set()
    for index, item in enumerate(targets):
        prefix = f"owner_decomposition_targets[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: expected mapping")
            continue

        result = _validate_target_quarter(
            item, prefix, seen_quarters, quarter_budget_map, errors
        )
        if result is None:
            continue
        quarter, parsed_quarter = result

        parsed_allocations = _parse_owner_allocations(item, prefix, errors)
        if parsed_allocations is None:
            continue

        _validate_allocation_constraints(
            prefix=prefix,
            parsed_quarter=parsed_quarter,
            parsed_allocations=parsed_allocations,
            quarter=quarter,
            quarter_budget_map=quarter_budget_map,
            owner_diversification_start=owner_diversification_start,
            min_distinct_owners=min_distinct_owners,
            errors=errors,
        )


__all__ = [
    "_collect_quarterly_registry_budgets",
    "_parse_owner_allocations",
    "_validate_owner_decomposition_targets_section",
    "_validate_owner_diversification_policy",
    "_validate_target_quarter",
]
