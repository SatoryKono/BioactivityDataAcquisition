"""Scorecard governance facade for architecture metric exemptions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import _quarter_label
from bioetl.infrastructure.quality.budget_evaluator import (
    current_quarter_target,
    evaluate_budget_violations,
    evaluate_governance_violations,
    evaluate_hotspot_budget_violations,
    resolve_grace_allowances,
)
from bioetl.infrastructure.quality.debt_scorecard_validation import (
    validate_debt_scorecard_raw,
)
from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry
from bioetl.infrastructure.quality.inventory import (
    ExemptionInventorySummary,
    build_exemption_inventory,
)
from bioetl.infrastructure.quality.registry_sync_service import validate_registry_sync
from bioetl.infrastructure.quality.report_formatter import (
    split_growth_violations_by_severity,
)
from bioetl.infrastructure.quality.scoring import compute_integral_debt_score

_DEFAULT_SCORECARD_PATH = Path("configs/quality/debt_scorecard.yaml")


@dataclass(frozen=True)
class DebtScorecardResult:
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
    by_hotspot: dict[str, dict[str, int]] = field(default_factory=dict)


def _resolve_enforceable_baseline(scorecard: JsonDict) -> dict[str, object]:
    """Resolve the baseline section used for scoring/integral debt evaluation."""
    governance = scorecard.get("governance", {})
    section_name = "baseline"
    if isinstance(governance, dict):
        baseline_policy = governance.get("baseline_policy", {})
        if isinstance(baseline_policy, dict):
            configured = baseline_policy.get("enforceable_section")
            if isinstance(configured, str) and configured.strip():
                section_name = configured.strip()

    baseline = scorecard.get(section_name, {})
    if not isinstance(baseline, dict):
        raise ValueError(f"scorecard.{section_name}: expected mapping")
    return baseline


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_scorecard_path(path: Path | str | None = None) -> Path:
    candidate = _DEFAULT_SCORECARD_PATH if path is None else Path(path)
    if candidate.is_absolute():
        return candidate
    return _project_root() / candidate


def load_debt_scorecard(
    path: Path | str | None = None,
) -> JsonDict:
    """Load debt scorecard YAML as dictionary."""
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
    """Validate debt scorecard schema and monotonic governance targets."""
    raw = load_debt_scorecard(path)
    return validate_debt_scorecard_raw(raw)


def validate_scorecard_registry_sync(
    *,
    registry_path: Path | str | None = None,
    scorecard_path: Path | str | None = None,
    today: date | None = None,
) -> list[str]:
    """Validate that scorecard baseline is synchronized with exemption registry."""
    now = today or date.today()
    inventory = build_exemption_inventory(registry_path, today=now)
    raw_registry = load_exemptions_registry(registry_path)
    scorecard = load_debt_scorecard(scorecard_path)
    return validate_registry_sync(
        raw_registry=raw_registry,
        scorecard=scorecard,
        inventory=inventory,
    )


def _iter_registry_entries(raw_registry: JsonDict) -> tuple[dict[str, object], ...]:
    """Yield normalized registry entry mappings from the raw exemptions payload."""
    registries = raw_registry.get("registries", {})
    if not isinstance(registries, dict):
        return ()

    entries: list[dict[str, object]] = []
    for registry_entries in registries.values():
        if not isinstance(registry_entries, dict):
            continue
        for entry in registry_entries.values():
            if isinstance(entry, dict):
                entries.append(entry)
    return tuple(entries)


def _is_technical_debt_entry(entry: dict[str, object]) -> bool:
    """Return True when a registry entry is classified as technical debt."""
    return entry.get("classification") == "technical_debt"


def _normalized_owner(owner: object) -> str:
    """Normalize missing or blank owner values into one sortable bucket."""
    return owner.strip() if isinstance(owner, str) and owner.strip() else "<missing>"


def _technical_debt_owner_counts(raw_registry: JsonDict) -> dict[str, int]:
    """Return active-owner counts considering only technical_debt entries."""
    by_owner: Counter[str] = Counter()
    for entry in _iter_registry_entries(raw_registry):
        if not _is_technical_debt_entry(entry):
            continue
        by_owner[_normalized_owner(entry.get("owner"))] += 1
    return dict(sorted(by_owner.items()))


def evaluate_debt_scorecard(
    *,
    registry_path: Path | str | None = None,
    scorecard_path: Path | str | None = None,
    today: date | None = None,
) -> tuple[list[str], DebtScorecardResult | None]:
    """Evaluate scorecard budgets and return (violations, summary)."""
    now = today or date.today()
    raw_registry = load_exemptions_registry(registry_path)
    inventory = build_exemption_inventory(registry_path, today=now)
    scorecard = load_debt_scorecard(scorecard_path)

    validation_errors = validate_debt_scorecard(scorecard_path)
    if validation_errors:
        return validation_errors, None

    enforceable_baseline = _resolve_enforceable_baseline(scorecard)
    baseline_total_raw = enforceable_baseline.get("total_exemptions")
    if not isinstance(baseline_total_raw, int):
        return ["scorecard enforceable baseline missing int total_exemptions"], None
    baseline_total = baseline_total_raw

    target = current_quarter_target(scorecard, today=now)
    if target is None:
        return [
            f"Missing quarterly target for current quarter '{_quarter_label(now)}'"
        ], None

    active_windows, allowance_total, allowance_by_registry, allowance_by_group = (
        resolve_grace_allowances(scorecard, now)
    )

    violations, by_group, score = evaluate_budget_violations(
        inventory=inventory,
        scorecard=scorecard,
        target=target,
        baseline_total=baseline_total,
        allowance_total=allowance_total,
        allowance_by_registry=allowance_by_registry,
        allowance_by_group=allowance_by_group,
    )
    hotspot_violations, by_hotspot = evaluate_hotspot_budget_violations(
        raw_registry=raw_registry,
        scorecard=scorecard,
    )
    violations.extend(hotspot_violations)

    quarter = str(target["quarter"])
    violations.extend(
        evaluate_governance_violations(
            inventory=inventory,
            scorecard=scorecard,
            quarter=quarter,
            integral_score=score,
            owner_counts=_technical_debt_owner_counts(raw_registry),
        )
    )

    total_budget = int(target["max_total_exemptions"]) + allowance_total
    summary = DebtScorecardResult(
        quarter=quarter,
        integral_score=score,
        total_exemptions=inventory.total_exemptions,
        total_budget=total_budget,
        active_grace_windows=tuple(
            str(window.get("rf_id", "<unknown>")) for window in active_windows
        ),
        by_registry=dict(inventory.by_registry),
        by_group=by_group,
        by_hotspot=by_hotspot,
        by_owner=dict(inventory.by_owner),
        by_expiry_quarter=dict(inventory.by_expiry_quarter),
        expired_entries=inventory.expired_entries,
    )
    return violations, summary


__all__ = [
    "DebtScorecardResult",
    "ExemptionInventorySummary",
    "build_exemption_inventory",
    "compute_integral_debt_score",
    "evaluate_debt_scorecard",
    "load_debt_scorecard",
    "split_growth_violations_by_severity",
    "validate_debt_scorecard",
    "validate_scorecard_registry_sync",
]
