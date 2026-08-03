"""Report formatting and grace-window policy logic for debt scorecard evaluation."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import _parse_iso_date

_REGISTRY_VIOLATION_RE = re.compile(
    r"^registry '([^']+)' count \d+ exceeds budget \d+$"
)
_GROUP_VIOLATION_RE = re.compile(r"^group '([^']+)' count \d+ exceeds budget \d+$")
_TOTAL_VIOLATION_RE = re.compile(r"^total exemptions \d+ exceeds budget \d+$")
_INTEGRAL_SCORE_VIOLATION_RE = re.compile(
    r"^integral debt score [\d.]+ is below target [\d.]+$"
)


def _is_rollout_cutoff_active(
    raw_cutoff: object,
    *,
    today: date,
) -> bool:
    """Return True when a rollout cutoff still keeps a section in warn mode."""
    cutoff = _parse_iso_date(raw_cutoff)
    return cutoff is not None and today <= cutoff


def _is_rollout_cutoff_stale(
    raw_cutoff: object,
    *,
    today: date,
) -> bool:
    """Return True when a rollout cutoff exists but is already in the past."""
    cutoff = _parse_iso_date(raw_cutoff)
    return cutoff is not None and cutoff < today


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
    active_windows: list[JsonDict],  # Any: YAML values are heterogeneous
) -> tuple[int, Counter[str], Counter[str]]:
    allowance_total = 0
    allowance_by_registry: Counter[str] = Counter()
    allowance_by_group: Counter[str] = Counter()

    for window in active_windows:
        allowances = window.get("allowances", {})
        if not isinstance(allowances, dict):
            continue

        allowance_total += int(allowances.get("total_exemptions", 0))
        _accumulate_allowances(
            allowances.get("registry_budgets", {}),
            allowance_by_registry,
        )
        _accumulate_allowances(
            allowances.get("group_budgets", {}),
            allowance_by_group,
        )

    return allowance_total, allowance_by_registry, allowance_by_group


def _accumulate_allowances(source: object, destination: Counter[str]) -> None:
    """Accumulate integer budget entries from one allowance mapping."""
    if not isinstance(source, dict):
        return
    for name, value in source.items():
        if isinstance(value, int):
            destination[name] += value


def _extract_growth_violation_section(violation: str) -> str:
    """Map a human-readable growth violation to section key.

    Returns:
        Section key string such as 'registry:name', 'group:name', 'total_exemptions', or 'unknown'.
    """
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
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
    section_key: str,
    today: date,
    fallback_mode: str,
) -> str:
    """Resolve warn/block mode for section with staged rollout overrides.

    Returns:
        Mode string 'warn' or 'block' based on staged rollout policy for the given section.
    """
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
        if _is_rollout_cutoff_active(raw_cutoff, today=today):
            return "warn"

    return default_mode_str


def split_growth_violations_by_severity(
    *,
    violations: list[str],
    scorecard: JsonDict,  # Any: YAML scorecard sections are heterogeneous
    today: date | None = None,
    fallback_mode: str = "block",
) -> tuple[list[str], list[str]]:
    """Split growth violations into (blocking, warning) using staged rollout policy.

    Returns:
        Tuple of (blocking violations, warning violations) lists.
    """
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


__all__ = [
    "_collect_allowances",
    "_extract_growth_violation_section",
    "_is_active_grace_window",
    "_is_rollout_cutoff_active",
    "_is_rollout_cutoff_stale",
    "_resolve_rollout_mode_for_section",
    "split_growth_violations_by_severity",
]
