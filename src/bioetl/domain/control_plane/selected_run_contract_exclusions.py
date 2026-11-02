"""Pure contract-exclusion status and funnel metrics for selected-run-status.

Status vocabulary is OK / WARN / CRIT / UNKNOWN (CRIT replaces the legacy
dashboard JSONata ``ERROR`` hard-limit label). Limits are supplied by callers;
this module does not load configs or touch the filesystem.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

_OK = "OK"
_WARN = "WARN"
_CRIT = "CRIT"
_UNKNOWN = "UNKNOWN"
_STAGE_IDS = ("bronze", "silver", "gold")
_EXCLUDED = "excluded_by_contract"


def classify_contract_exclusions(
    soft: float | None,
    hard: float | None,
    funnel: object,
) -> dict[str, object]:
    """Classify contract_exclusions_* from preloaded soft/hard limits and funnel."""
    if soft is None or hard is None:
        return {
            "contract_exclusions_status": _UNKNOWN,
            "contract_exclusions_rate": None,
            "contract_exclusions_soft_limit": None,
            "contract_exclusions_hard_limit": None,
        }
    rate = _exclusion_rate(funnel)
    if rate is None:
        status: str = _UNKNOWN
    elif rate >= hard:
        status = _CRIT
    elif rate >= soft:
        status = _WARN
    else:
        status = _OK
    return {
        "contract_exclusions_status": status,
        "contract_exclusions_rate": rate,
        "contract_exclusions_soft_limit": soft,
        "contract_exclusions_hard_limit": hard,
    }


def extract_records_in(funnel: object) -> int | None:
    """Return bronze (else extract) ``records_in``, or null when unavailable."""
    stages = _stage_map(funnel)
    for stage_id in ("bronze", "extract"):
        stage = stages.get(stage_id)
        if stage is None:
            continue
        value = stage.get("records_in")
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        if value >= 0:
            return value
    return None


def _exclusion_rate(funnel: object) -> float | None:
    """Rate over bronze/silver/gold; extra stages (e.g. extract) are allowed."""
    stages = _stage_map(funnel)
    ordered = _required_stages(stages)
    if ordered is None:
        return None
    base = _non_negative_int(ordered[0].get("records_out"))
    if base is None:
        return None
    excluded_total = _excluded_total(ordered)
    if excluded_total is None or excluded_total > base:
        return None
    if base == 0:
        return 0.0
    return excluded_total / base


def _required_stages(
    stages: dict[str, Mapping[str, object]],
) -> list[Mapping[str, object]] | None:
    """Return bronze/silver/gold only; ignore extract and other extras."""
    if any(stage_id not in stages for stage_id in _STAGE_IDS):
        return None
    ordered = [stages[stage_id] for stage_id in _STAGE_IDS]
    if not all(_stage_fully_tracked(stage) for stage in ordered):
        return None
    return ordered


def _excluded_total(stages: Sequence[Mapping[str, object]]) -> int | None:
    total = 0
    for stage in stages:
        count = _stage_excluded_count(stage)
        if count is None:
            return None
        total += count
    return total


def _stage_excluded_count(stage: Mapping[str, object]) -> int | None:
    removals = stage.get("removals")
    if not isinstance(removals, Sequence) or isinstance(removals, (str, bytes)):
        return None
    total = 0
    for removal in removals:
        if not isinstance(removal, Mapping):
            return None
        if removal.get("outcome") != _EXCLUDED:
            continue
        count = _non_negative_int(removal.get("count"))
        if count is None:
            return None
        total += count
    return total


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _stage_fully_tracked(stage: Mapping[str, object]) -> bool:
    tracking = stage.get("tracking")
    removals = stage.get("removals")
    return tracking == "full" and isinstance(removals, list)


def _stage_map(funnel: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(funnel, Sequence) or isinstance(funnel, (str, bytes)):
        return {}
    stages: dict[str, Mapping[str, object]] = {}
    for item in funnel:
        if not isinstance(item, Mapping):
            continue
        stage_id = item.get("stage_id")
        if isinstance(stage_id, str) and stage_id:
            stages[stage_id] = item
    return stages
