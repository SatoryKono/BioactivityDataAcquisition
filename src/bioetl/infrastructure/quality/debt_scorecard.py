"""Scorecard governance for architecture metric exemptions."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.quality.debt_scorecard_validation import (
    _parse_iso_date,
    validate_debt_scorecard_raw,
)
from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry

_DEFAULT_SCORECARD_PATH = Path("configs/quality/debt_scorecard.yaml")


@dataclass(frozen=True)
class ExemptionInventory:
    """Aggregated exemption inventory for governance calculations."""

    total_exemptions: int
    by_registry: dict[str, int]
    by_owner: dict[str, int]
    by_expiry_quarter: dict[str, int]
    expired_entries: int


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


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_scorecard_path(path: Path | str | None = None) -> Path:
    candidate = _DEFAULT_SCORECARD_PATH if path is None else Path(path)
    if candidate.is_absolute():
        return candidate
    return _project_root() / candidate


def _quarter_label(target_date: date) -> str:
    quarter = ((target_date.month - 1) // 3) + 1
    return f"{target_date.year}-Q{quarter}"


_REGISTRY_VIOLATION_RE = re.compile(
    r"^registry '([^']+)' count \d+ exceeds budget \d+$"
)
_GROUP_VIOLATION_RE = re.compile(r"^group '([^']+)' count \d+ exceeds budget \d+$")
_TOTAL_VIOLATION_RE = re.compile(r"^total exemptions \d+ exceeds budget \d+$")
_INTEGRAL_SCORE_VIOLATION_RE = re.compile(
    r"^integral debt score [\d.]+ is below target [\d.]+$"
)


def load_debt_scorecard(
    path: Path | str | None = None,
) -> dict[str, Any]:  # Any: scorecard sections are heterogeneous
    """Load debt scorecard YAML as dictionary."""
    scorecard_path = _resolve_scorecard_path(path)
    if not scorecard_path.exists():
        raise FileNotFoundError(f"Debt scorecard not found: {scorecard_path}")

    raw = yaml.safe_load(scorecard_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Debt scorecard must be a mapping: {scorecard_path}")
    return raw


def build_exemption_inventory(
    registry_path: Path | str | None = None,
    *,
    today: date | None = None,
) -> ExemptionInventory:
    """Build aggregated inventory from the exemptions registry."""
    now = today or date.today()
    raw = load_exemptions_registry(registry_path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        raise ValueError("Invalid exemptions registry: 'registries' must be a mapping")

    by_registry: Counter[str] = Counter()
    by_owner: Counter[str] = Counter()
    by_expiry_quarter: Counter[str] = Counter()
    expired_entries = 0

    for registry_name, entries in registries.items():
        if not isinstance(entries, dict):
            continue

        for entry in entries.values():
            if not isinstance(entry, dict):
                continue

            by_registry[registry_name] += 1
            owner = entry.get("owner")
            owner_name = (
                owner.strip()
                if isinstance(owner, str) and owner.strip()
                else "<missing>"
            )
            by_owner[owner_name] += 1

            expiry_date = _parse_iso_date(entry.get("expires_on"))
            if expiry_date is None:
                by_expiry_quarter["unknown"] += 1
            else:
                by_expiry_quarter[_quarter_label(expiry_date)] += 1
                if expiry_date < now:
                    expired_entries += 1

    return ExemptionInventory(
        total_exemptions=sum(by_registry.values()),
        by_registry=dict(sorted(by_registry.items())),
        by_owner=dict(sorted(by_owner.items())),
        by_expiry_quarter=dict(sorted(by_expiry_quarter.items())),
        expired_entries=expired_entries,
    )


def validate_debt_scorecard(
    path: Path | str | None = None,
) -> list[str]:
    """Validate debt scorecard schema and monotonic governance targets."""
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
    """
    now = today or date.today()
    inventory = build_exemption_inventory(registry_path, today=now)
    scorecard = load_debt_scorecard(scorecard_path)

    baseline = scorecard.get("baseline", {})
    if not isinstance(baseline, dict):
        return ["scorecard.baseline: expected mapping"]

    baseline_by_registry = baseline.get("by_registry", {})
    if not isinstance(baseline_by_registry, dict):
        return ["scorecard.baseline.by_registry: expected mapping"]

    errors: list[str] = []
    inventory_registry_names = set(inventory.by_registry)
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


def compute_integral_debt_score(
    *,
    total_exemptions: int,
    expired_entries: int,
    baseline_total: int,
) -> float:
    """Compute integral debt score (0..100), higher is better."""
    if baseline_total <= 0:
        return 0.0

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


def _current_quarter_target(
    scorecard: dict[str, Any],  # Any: YAML scorecard sections are heterogeneous
    *,
    today: date,
) -> dict[str, Any] | None:  # Any: YAML scorecard sections are heterogeneous
    quarter = _quarter_label(today)
    for item in scorecard.get("quarterly_targets", []):
        if isinstance(item, dict) and item.get("quarter") == quarter:
            return item
    return None


def _is_active_grace_window(
    window: object,
    *,
    today: date,
) -> bool:
    if not isinstance(window, dict) or not window.get("approved"):
        return False
    starts_on = _parse_iso_date(window.get("starts_on"))
    ends_on = _parse_iso_date(window.get("ends_on"))
    if starts_on is None or ends_on is None:
        return False
    return starts_on <= today <= ends_on


def _collect_allowances(
    active_windows: list[dict[str, Any]],  # Any: YAML values are heterogeneous
) -> tuple[int, Counter[str], Counter[str]]:
    allowance_total = 0
    allowance_by_registry: Counter[str] = Counter()
    allowance_by_group: Counter[str] = Counter()

    for window in active_windows:
        allowances = window.get("allowances", {})
        if not isinstance(allowances, dict):
            continue

        allowance_total += int(allowances.get("total_exemptions", 0))

        reg_allowances = allowances.get("registry_budgets", {})
        if isinstance(reg_allowances, dict):
            for registry_name, value in reg_allowances.items():
                if isinstance(value, int):
                    allowance_by_registry[registry_name] += value

        group_allowances = allowances.get("group_budgets", {})
        if isinstance(group_allowances, dict):
            for group_name, value in group_allowances.items():
                if isinstance(value, int):
                    allowance_by_group[group_name] += value

    return allowance_total, allowance_by_registry, allowance_by_group


def _extract_growth_violation_section(violation: str) -> str:
    """Map a human-readable growth violation to section key."""
    registry_match = _REGISTRY_VIOLATION_RE.match(violation)
    if registry_match is not None:
        return f"registry:{registry_match.group(1)}"

    group_match = _GROUP_VIOLATION_RE.match(violation)
    if group_match is not None:
        return f"group:{group_match.group(1)}"

    if _TOTAL_VIOLATION_RE.match(violation):
        return "total_exemptions"
    if _INTEGRAL_SCORE_VIOLATION_RE.match(violation):
        return "integral_score"
    return "unknown"


def _resolve_rollout_mode_for_section(
    *,
    scorecard: dict[str, Any],  # Any: YAML scorecard sections are heterogeneous
    section_key: str,
    today: date,
    fallback_mode: str,
) -> str:
    """Resolve warn/block mode for section with staged rollout overrides."""
    governance = scorecard.get("governance", {})
    if not isinstance(governance, dict):
        return fallback_mode

    rollout = governance.get("growth_section_gate_rollout", {})
    if not isinstance(rollout, dict):
        return fallback_mode

    default_mode = rollout.get("default_mode", fallback_mode)
    default_mode_str = (
        default_mode.strip().lower() if isinstance(default_mode, str) else fallback_mode
    )
    if default_mode_str not in {"warn", "block"}:
        default_mode_str = fallback_mode

    warn_until_by_section = rollout.get("warn_until_by_section", {})
    if not isinstance(warn_until_by_section, dict):
        return default_mode_str

    rollout_keys = [section_key]
    if ":" in section_key:
        section_prefix = section_key.split(":", 1)[0]
        rollout_keys.append(f"{section_prefix}:*")
    rollout_keys.append("*")

    for key in rollout_keys:
        raw_cutoff = warn_until_by_section.get(key)
        cutoff = _parse_iso_date(raw_cutoff)
        if cutoff is not None and today <= cutoff:
            return "warn"

    return default_mode_str


def split_growth_violations_by_severity(
    *,
    violations: list[str],
    scorecard: dict[str, Any],  # Any: YAML scorecard sections are heterogeneous
    today: date | None = None,
    fallback_mode: str = "block",
) -> tuple[list[str], list[str]]:
    """Split growth violations into (blocking, warning) using staged rollout policy."""
    now = today or date.today()
    default_mode = fallback_mode.strip().lower()
    if default_mode not in {"warn", "block"}:
        default_mode = "block"

    blocking: list[str] = []
    warning: list[str] = []
    for violation in violations:
        section_key = _extract_growth_violation_section(violation)
        section_mode = _resolve_rollout_mode_for_section(
            scorecard=scorecard,
            section_key=section_key,
            today=now,
            fallback_mode=default_mode,
        )
        if section_mode == "warn":
            warning.append(violation)
        else:
            blocking.append(violation)
    return blocking, warning


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


def _compute_group_counts(
    *,
    by_registry: dict[str, int],
    registry_groups: dict[str, Any],  # Any: YAML values are heterogeneous
) -> dict[str, int]:
    by_group: dict[str, int] = {}
    for group_name, group_cfg in sorted(registry_groups.items()):
        registries = group_cfg["registries"]
        by_group[group_name] = sum(by_registry.get(name, 0) for name in registries)
    return by_group


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


def evaluate_debt_scorecard(
    *,
    registry_path: Path | str | None = None,
    scorecard_path: Path | str | None = None,
    today: date | None = None,
) -> tuple[list[str], DebtScorecardEvaluation | None]:
    """Evaluate scorecard budgets and return (violations, summary)."""
    now = today or date.today()
    inventory = build_exemption_inventory(registry_path, today=now)
    scorecard = load_debt_scorecard(scorecard_path)

    validation_errors = validate_debt_scorecard(scorecard_path)
    if validation_errors:
        return validation_errors, None

    baseline = scorecard["baseline"]
    baseline_total = int(baseline["total_exemptions"])

    target = _current_quarter_target(scorecard, today=now)
    if target is None:
        return [
            f"Missing quarterly target for current quarter '{_quarter_label(now)}'"
        ], None

    active_windows = [
        window
        for window in scorecard.get("grace_windows", [])
        if _is_active_grace_window(window, today=now)
    ]
    typed_active_windows = [
        window for window in active_windows if isinstance(window, dict)
    ]
    allowance_total, allowance_by_registry, allowance_by_group = _collect_allowances(
        typed_active_windows
    )

    target_registry_budgets = target["registry_budgets"]
    target_group_budgets = target["group_budgets"]
    by_group = _compute_group_counts(
        by_registry=inventory.by_registry,
        registry_groups=scorecard["registry_groups"],
    )
    violations = _evaluate_registry_budgets(
        by_registry=inventory.by_registry,
        target_registry_budgets=target_registry_budgets,
        allowance_by_registry=allowance_by_registry,
    )
    violations.extend(
        _evaluate_group_budgets(
            by_group=by_group,
            target_group_budgets=target_group_budgets,
            allowance_by_group=allowance_by_group,
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

    summary = DebtScorecardEvaluation(
        quarter=str(target["quarter"]),
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
