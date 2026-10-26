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
    "evaluate_hotspot_budget_violations",
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
    owner_counts: dict[str, int] | None = None,
) -> list[str]:
    """Evaluate governance-policy violations for owner/expiry/program criteria."""
    violations: list[str] = []
    effective_owner_counts = (
        inventory.by_owner if owner_counts is None else owner_counts
    )

    owner_allocations = _owner_allocations_for_quarter(
        scorecard=scorecard,
        quarter=quarter,
    )
    if _is_owner_decomposition_active(scorecard=scorecard, quarter=quarter):
        violations.extend(
            _evaluate_owner_allocations(
                by_owner=effective_owner_counts,
                allocations=owner_allocations,
                quarter=quarter,
            )
        )
    violations.extend(
        _evaluate_owner_diversification(
            by_owner=effective_owner_counts,
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


def _get_typed_prefixes(path_prefixes: object) -> tuple[str, ...] | None:
    if not isinstance(path_prefixes, list):
        return None
    typed = tuple(p for p in path_prefixes if isinstance(p, str) and p)
    return typed if typed else None


def _get_typed_budgets(registry_budgets: object) -> dict[str, int] | None:
    if not isinstance(registry_budgets, dict):
        return None
    return {
        k: v
        for k, v in registry_budgets.items()
        if isinstance(k, str) and isinstance(v, int)
    }


def _parse_hotspot_entry(
    entry: dict[str, object],
) -> tuple[str, tuple[str, ...], dict[str, int]] | None:
    hotspot_name = entry.get("name")
    if not isinstance(hotspot_name, str):
        return None

    typed_prefixes = _get_typed_prefixes(entry.get("path_prefixes"))
    if typed_prefixes is None:
        return None

    typed_budgets = _get_typed_budgets(entry.get("registry_budgets"))
    if typed_budgets is None:
        return None

    return (hotspot_name, typed_prefixes, typed_budgets)


def _iter_hotspot_budget_entries(
    hotspot_budgets: object,
) -> list[tuple[str, tuple[str, ...], dict[str, int]]]:
    """Normalize valid hotspot budget entries into typed tuples."""
    if not isinstance(hotspot_budgets, list):
        return []

    typed_entries: list[tuple[str, tuple[str, ...], dict[str, int]]] = []
    for entry in hotspot_budgets:
        if not isinstance(entry, dict):
            continue
        parsed = _parse_hotspot_entry(entry)
        if parsed is not None:
            typed_entries.append(parsed)
    return typed_entries


def _count_hotspot_registry_entries(
    *,
    registries: dict[str, object],
    typed_prefixes: tuple[str, ...],
    registry_budgets: dict[str, int],
) -> Counter[str]:
    """Count exemption entries that fall under hotspot path prefixes."""
    counts: Counter[str] = Counter()
    for registry_name, entries in registries.items():
        if registry_name not in registry_budgets or not isinstance(entries, dict):
            continue
        for entry_key, entry_value in entries.items():
            if not isinstance(entry_key, str) or not isinstance(entry_value, dict):
                continue
            source_path = entry_key.split("::", 1)[0]
            if any(source_path.startswith(prefix) for prefix in typed_prefixes):
                counts[registry_name] += 1
    return counts


def _collect_hotspot_budget_violations(
    *,
    hotspot_name: str,
    hotspot_counts: dict[str, int],
    registry_budgets: dict[str, int],
) -> list[str]:
    """Format budget violations for one hotspot."""
    violations: list[str] = []
    for registry_name, current_count in hotspot_counts.items():
        budget = registry_budgets[registry_name]
        if current_count > budget:
            violations.append(
                "hotspot "
                f"'{hotspot_name}' registry '{registry_name}' count "
                f"{current_count} exceeds budget {budget}"
            )
    return violations


def evaluate_hotspot_budget_violations(
    *,
    raw_registry: JsonDict,
    scorecard: JsonDict,
) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Evaluate hotspot budgets against concrete exemption entry path prefixes."""
    typed_hotspot_entries = _iter_hotspot_budget_entries(
        scorecard.get("hotspot_budgets", [])
    )
    if not typed_hotspot_entries:
        return [], {}

    registries = raw_registry.get("registries", {})
    if not isinstance(registries, dict):
        return ["exemptions.registries: expected mapping"], {}

    violations: list[str] = []
    by_hotspot: dict[str, dict[str, int]] = {}

    for hotspot_name, typed_prefixes, registry_budgets in typed_hotspot_entries:
        counts = _count_hotspot_registry_entries(
            registries=registries,
            typed_prefixes=typed_prefixes,
            registry_budgets=registry_budgets,
        )
        hotspot_counts = {
            registry_name: counts.get(registry_name, 0)
            for registry_name in sorted(registry_budgets)
        }
        by_hotspot[hotspot_name] = hotspot_counts
        violations.extend(
            _collect_hotspot_budget_violations(
                hotspot_name=hotspot_name,
                hotspot_counts=hotspot_counts,
                registry_budgets=registry_budgets,
            )
        )

    return violations, by_hotspot
