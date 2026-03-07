"""Scorecard governance for architecture metric exemptions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    _parse_quarter_label,
    _quarter_label,
)
from bioetl.infrastructure.quality.debt_scorecard_validation import (
    validate_debt_scorecard_raw,
)
from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry
from bioetl.infrastructure.quality.inventory import (
    ExemptionInventory,
    build_exemption_inventory,
)
from bioetl.infrastructure.quality.report_formatter import (
    _collect_allowances,
    _is_active_grace_window,
    split_growth_violations_by_severity,
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

_DEFAULT_SCORECARD_PATH = Path("configs/quality/debt_scorecard.yaml")


@dataclass(frozen=True)
class DebtScorecardEvaluation:
    """Result of scorecard budget evaluation."""

    quarter: str
    integral_score: float
    total_exemptions: int
    total_budget: int
    active_grace_windows: tuple[str, ...]
    by_registry: dict[str, int]
    by_group: dict[str, int]
    by_owner: dict[str, int]
    by_expiry_quarter: dict[str, int]
    expired_entries: int


def _is_owner_decomposition_active(
    *,
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
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


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_scorecard_path(path: Path | str | None = None) -> Path:
    candidate = _DEFAULT_SCORECARD_PATH if path is None else Path(path)
    if candidate.is_absolute():
        return candidate
    return _project_root() / candidate


def _current_quarter_target(
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
    *,
    today: date,
) -> JsonDict | None:  # Any: YAML scorecard sections are heterogeneous
    quarter = _quarter_label(today)
    for item in scorecard.get("quarterly_targets", []):
        if isinstance(item, dict) and item.get("quarter") == quarter:
            return item
    return None


def load_debt_scorecard(
    path: Path | str | None = None,
) -> JsonDict:  # Any: scorecard sections are heterogeneous
    """Load debt scorecard YAML as dictionary.

    Returns:
        Dictionary with the parsed debt scorecard YAML content.
    """
    scorecard_path = _resolve_scorecard_path(path)
    if not scorecard_path.exists():
        raise FileNotFoundError(f"Debt scorecard not found: {scorecard_path}")

    raw = yaml.safe_load(scorecard_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Debt scorecard must be a mapping: {scorecard_path}")
    return raw


def validate_debt_scorecard(
    path: Path | str | None = None,
) -> list[str]:
    """Validate debt scorecard schema and monotonic governance targets.

    Returns:
        List of validation error message strings, empty if scorecard is valid.
    """
    raw = load_debt_scorecard(path)
    return validate_debt_scorecard_raw(raw)


def validate_scorecard_registry_sync(
    *,
    registry_path: Path | str | None = None,
    scorecard_path: Path | str | None = None,
    today: date | None = None,
) -> list[str]:
    """Validate that scorecard baseline is synchronized with exemption registry.

    This check is intentionally conservative:
    - scorecard must declare every live registry from exemptions YAML
    - no live registry count may exceed baseline.by_registry budget
    - total live exemptions may not exceed baseline.total_exemptions

    The check prevents silent drift where scorecard budgets lag behind the real
    exemption registry and CI gates become misleading.

    Returns:
        List of sync error message strings, empty if scorecard and registry are consistent.
    """
    now = today or date.today()
    inventory = build_exemption_inventory(registry_path, today=now)
    raw_registry = load_exemptions_registry(registry_path)
    raw_registries = raw_registry.get("registries", {})
    if not isinstance(raw_registries, dict):
        return ["exemptions.registries: expected mapping"]

    scorecard = load_debt_scorecard(scorecard_path)

    baseline = scorecard.get("baseline", {})
    if not isinstance(baseline, dict):
        return ["scorecard.baseline: expected mapping"]

    baseline_by_registry = baseline.get("by_registry", {})
    if not isinstance(baseline_by_registry, dict):
        return ["scorecard.baseline.by_registry: expected mapping"]

    errors: list[str] = []
    # Include empty registries (e.g. god_object: {}) so sync checks don't
    # falsely treat them as missing when baseline budgets explicitly track them.
    inventory_registry_names = set(raw_registries)
    baseline_registry_names = set(baseline_by_registry)

    missing_in_scorecard = sorted(inventory_registry_names - baseline_registry_names)
    if missing_in_scorecard:
        errors.append(
            "scorecard.baseline.by_registry missing live registries: "
            f"{missing_in_scorecard}"
        )

    stale_in_scorecard = sorted(baseline_registry_names - inventory_registry_names)
    if stale_in_scorecard:
        errors.append(
            "scorecard.baseline.by_registry has stale registries not present in "
            f"exemptions YAML: {stale_in_scorecard}"
        )

    comparable_registries = sorted(inventory_registry_names & baseline_registry_names)
    for registry_name in comparable_registries:
        baseline_value = baseline_by_registry.get(registry_name)
        if not isinstance(baseline_value, int):
            errors.append(
                "scorecard.baseline.by_registry."
                f"{registry_name}: expected int, got {type(baseline_value).__name__}"
            )
            continue
        live_count = inventory.by_registry.get(registry_name, 0)
        if live_count > baseline_value:
            errors.append(
                f"registry '{registry_name}' live count {live_count} exceeds "
                f"scorecard baseline {baseline_value}"
            )

    baseline_total = baseline.get("total_exemptions")
    if not isinstance(baseline_total, int):
        errors.append(
            "scorecard.baseline.total_exemptions: expected int, "
            f"got {type(baseline_total).__name__}"
        )
    elif inventory.total_exemptions > baseline_total:
        errors.append(
            f"live total_exemptions {inventory.total_exemptions} exceeds "
            f"scorecard baseline {baseline_total}"
        )

    return errors


def _resolve_grace_allowances(
    scorecard: JsonDict,
    today: date,
) -> tuple[list[JsonDict], int, dict[str, int], dict[str, int]]:
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


def _evaluate_budget_violations(
    inventory: ExemptionInventory,
    scorecard: JsonDict,
    target: JsonDict,
    baseline_total: int,
    allowance_total: int,
    allowance_by_registry: dict[str, int],
    allowance_by_group: dict[str, int],
) -> tuple[list[str], dict[str, int], float]:
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


def _evaluate_governance_violations(
    inventory: ExemptionInventory,
    scorecard: JsonDict,
    quarter: str,
    integral_score: float,
) -> list[str]:
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


def evaluate_debt_scorecard(
    *,
    registry_path: Path | str | None = None,
    scorecard_path: Path | str | None = None,
    today: date | None = None,
) -> tuple[list[str], DebtScorecardEvaluation | None]:
    """Evaluate scorecard budgets and return (violations, summary).

    Returns:
        Tuple of (violation message list, DebtScorecardEvaluation summary or None if validation failed).
    """
    now = today or date.today()
    inventory = build_exemption_inventory(registry_path, today=now)
    scorecard = load_debt_scorecard(scorecard_path)

    validation_errors = validate_debt_scorecard(scorecard_path)
    if validation_errors:
        return validation_errors, None

    baseline_total = int(scorecard["baseline"]["total_exemptions"])

    target = _current_quarter_target(scorecard, today=now)
    if target is None:
        return [
            f"Missing quarterly target for current quarter '{_quarter_label(now)}'"
        ], None

    active_windows, allowance_total, allowance_by_registry, allowance_by_group = (
        _resolve_grace_allowances(scorecard, now)
    )

    violations, by_group, score = _evaluate_budget_violations(
        inventory,
        scorecard,
        target,
        baseline_total,
        allowance_total,
        allowance_by_registry,
        allowance_by_group,
    )

    quarter = str(target["quarter"])
    violations.extend(
        _evaluate_governance_violations(inventory, scorecard, quarter, score)
    )

    total_budget = int(target["max_total_exemptions"]) + allowance_total
    summary = DebtScorecardEvaluation(
        quarter=quarter,
        integral_score=score,
        total_exemptions=inventory.total_exemptions,
        total_budget=total_budget,
        active_grace_windows=tuple(
            str(window.get("rf_id", "<unknown>")) for window in active_windows
        ),
        by_registry=dict(inventory.by_registry),
        by_group=by_group,
        by_owner=dict(inventory.by_owner),
        by_expiry_quarter=dict(inventory.by_expiry_quarter),
        expired_entries=inventory.expired_entries,
    )
    return violations, summary


__all__ = [
    "DebtScorecardEvaluation",
    "ExemptionInventory",
    "build_exemption_inventory",
    "compute_integral_debt_score",
    "evaluate_debt_scorecard",
    "load_debt_scorecard",
    "split_growth_violations_by_severity",
    "validate_debt_scorecard",
    "validate_scorecard_registry_sync",
]
