"""Sub-service for debt scorecard budget and governance evaluation."""

from __future__ import annotations

from collections import Counter
from datetime import date

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    _parse_quarter_label,
    _quarter_label,
)
from bioetl.infrastructure.quality.inventory import ExemptionInventorySummary
from bioetl.infrastructure.quality.report_formatter import (
    _collect_allowances,
    _is_active_grace_window,
)
from bioetl.infrastructure.quality.scoring import (
    _compute_group_counts,
    _evaluate_expiry_cap,
    _evaluate_group_budgets,
    _evaluate_owner_allocations,
    _evaluate_owner_diversification,
    _evaluate_program_done_criteria,
    _evaluate_registry_budgets,
    _expiry_cap_for_quarter,
    _owner_allocations_for_quarter,
    compute_integral_debt_score,
)

__all__ = [
    "current_quarter_target",
    "evaluate_budget_violations",
    "evaluate_governance_violations",
    "resolve_grace_allowances",
]


def current_quarter_target(
    scorecard: JsonDict,
    *,
    today: date,
) -> JsonDict | None:
    """Return scorecard target entry for current quarter."""
    quarter = _quarter_label(today)
    for item in scorecard.get("quarterly_targets", []):
        if isinstance(item, dict) and item.get("quarter") == quarter:
            return item
    return None


def _is_owner_decomposition_active(
    *,
    scorecard: JsonDict,
    quarter: str,
) -> bool:
    """Enable owner-allocation enforcement from owner_diversification.starts_quarter."""
    governance = scorecard.get("governance", {})
    if not isinstance(governance, dict):
        return True

    diversification = governance.get("owner_diversification", {})
    if not isinstance(diversification, dict):
        return True

    starts_quarter = diversification.get("starts_quarter")
    if not isinstance(starts_quarter, str):
        return True

    current = _parse_quarter_label(quarter)
    starts = _parse_quarter_label(starts_quarter)
    if current is None or starts is None:
        return True
    return current >= starts


def resolve_grace_allowances(
    scorecard: JsonDict,
    today: date,
) -> tuple[list[JsonDict], int, dict[str, int], dict[str, int]]:
    """Resolve active grace windows and aggregate allowances."""
    active_windows: list[JsonDict] = [
        window
        for window in scorecard.get("grace_windows", [])
        if _is_active_grace_window(window, today=today)
    ]
    typed_active_windows = [
        window for window in active_windows if isinstance(window, dict)
    ]
    allowance_total, allowance_by_registry, allowance_by_group = _collect_allowances(
        typed_active_windows
    )
    return (
        active_windows,
        allowance_total,
        dict(allowance_by_registry),
        dict(allowance_by_group),
    )


def evaluate_budget_violations(
    *,
    inventory: ExemptionInventorySummary,
    scorecard: JsonDict,
    target: JsonDict,
    baseline_total: int,
    allowance_total: int,
    allowance_by_registry: dict[str, int],
    allowance_by_group: dict[str, int],
) -> tuple[list[str], dict[str, int], float]:
    """Evaluate budget-related violations and return (violations, by_group, score)."""
    by_group = _compute_group_counts(
        by_registry=inventory.by_registry,
        registry_groups=scorecard["registry_groups"],
    )
    violations = _evaluate_registry_budgets(
        by_registry=inventory.by_registry,
        target_registry_budgets=target["registry_budgets"],
        allowance_by_registry=Counter(allowance_by_registry),
    )
    violations.extend(
        _evaluate_group_budgets(
            by_group=by_group,
            target_group_budgets=target["group_budgets"],
            allowance_by_group=Counter(allowance_by_group),
        )
    )

    total_budget = int(target["max_total_exemptions"]) + allowance_total
    if inventory.total_exemptions > total_budget:
        violations.append(
            f"total exemptions {inventory.total_exemptions} exceeds budget {total_budget}"
        )

    score = compute_integral_debt_score(
        total_exemptions=inventory.total_exemptions,
        expired_entries=inventory.expired_entries,
        baseline_total=baseline_total,
    )
    min_score = float(target["min_integral_score"])
    if score < min_score:
        violations.append(f"integral debt score {score} is below target {min_score}")

    return violations, by_group, score


def evaluate_governance_violations(
    *,
    inventory: ExemptionInventorySummary,
    scorecard: JsonDict,
    quarter: str,
    integral_score: float,
) -> list[str]:
    """Evaluate governance-policy violations for owner/expiry/program criteria."""
    violations: list[str] = []

    owner_allocations = _owner_allocations_for_quarter(
        scorecard=scorecard,
        quarter=quarter,
    )
    if _is_owner_decomposition_active(scorecard=scorecard, quarter=quarter):
        violations.extend(
            _evaluate_owner_allocations(
                by_owner=inventory.by_owner,
                allocations=owner_allocations,
                quarter=quarter,
            )
        )
    violations.extend(
        _evaluate_owner_diversification(
            by_owner=inventory.by_owner,
            scorecard=scorecard,
            quarter=quarter,
        )
    )

    expiry_cap = _expiry_cap_for_quarter(
        scorecard=scorecard,
        quarter=quarter,
    )
    violations.extend(
        _evaluate_expiry_cap(
            by_expiry_quarter=inventory.by_expiry_quarter,
            quarter=quarter,
            cap=expiry_cap,
        )
    )
    violations.extend(
        _evaluate_program_done_criteria(
            scorecard=scorecard,
            current_quarter=quarter,
            total_exemptions=inventory.total_exemptions,
            integral_score=integral_score,
            expired_entries=inventory.expired_entries,
        )
    )

    return violations
