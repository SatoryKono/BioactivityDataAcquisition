"""Quarterly targets section validator."""

from __future__ import annotations

from itertools import pairwise
from typing import cast

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    QuarterTarget,
    _parse_quarter_label,
    _validate_budget_mapping,
    _validate_non_negative_int,
)


def _validate_quarter_target(
    *,
    index: int,
    target: object,
    group_names: set[str],
    baseline_registry_names: set[str],
    errors: list[str],
) -> (
    tuple[
        tuple[int, int],
        QuarterTarget,
    ]
    | None
):
    prefix = f"quarterly_targets[{index}]"
    if not isinstance(target, dict):
        errors.append(f"{prefix}: expected mapping")
        return None

    quarter = target.get("quarter")
    parsed_quarter = quarter if isinstance(quarter, str) else ""
    quarter_tuple = _parse_quarter_label(parsed_quarter)
    if quarter_tuple is None:
        errors.append(f"{prefix}.quarter: expected 'YYYY-QN' format")
        return None

    max_total = _validate_non_negative_int(
        target.get("max_total_exemptions"),
        field_name=f"{prefix}.max_total_exemptions",
        errors=errors,
    )
    min_score = target.get("min_integral_score")
    if not isinstance(min_score, (int, float)):
        errors.append(f"{prefix}.min_integral_score: expected number")
    elif not (0 <= float(min_score) <= 100):
        errors.append(f"{prefix}.min_integral_score: must be between 0 and 100")

    _validate_budget_mapping(
        target.get("group_budgets"),
        expected_keys=group_names,
        field_name=f"{prefix}.group_budgets",
        errors=errors,
    )
    _validate_budget_mapping(
        target.get("registry_budgets"),
        expected_keys=baseline_registry_names,
        field_name=f"{prefix}.registry_budgets",
        errors=errors,
    )

    if max_total is None or not isinstance(min_score, (int, float)):
        return None
    return quarter_tuple, cast(QuarterTarget, target)


def _validate_quarterly_targets_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    *,
    group_names: set[str],
    baseline_registry_names: set[str],
    errors: list[str],
) -> None:
    quarterly_targets = raw.get("quarterly_targets")
    if not isinstance(quarterly_targets, list) or not quarterly_targets:
        errors.append("quarterly_targets: required non-empty list")
        return

    parsed_targets: list[tuple[tuple[int, int], QuarterTarget]] = []
    seen_quarters: set[str] = set()
    for index, target in enumerate(quarterly_targets):
        parsed = _validate_quarter_target(
            index=index,
            target=target,
            group_names=group_names,
            baseline_registry_names=baseline_registry_names,
            errors=errors,
        )
        if parsed is None:
            continue
        quarter = str(parsed[1]["quarter"])
        if quarter in seen_quarters:
            errors.append(
                f"quarterly_targets[{index}].quarter: duplicate quarter '{quarter}'"
            )
            continue
        seen_quarters.add(quarter)
        parsed_targets.append(parsed)

    ordered_targets = [
        item[1] for item in sorted(parsed_targets, key=lambda item: item[0])
    ]
    for previous, current in pairwise(ordered_targets):
        prev_total = int(previous["max_total_exemptions"])
        curr_total = int(current["max_total_exemptions"])
        if curr_total >= prev_total:
            errors.append(
                "quarterly_targets: max_total_exemptions must strictly decrease each quarter"
            )

        prev_score = float(previous["min_integral_score"])
        curr_score = float(current["min_integral_score"])
        if curr_score <= prev_score:
            errors.append(
                "quarterly_targets: min_integral_score must strictly increase each quarter"
            )
