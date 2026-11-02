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
    return {
        "contract_exclusions_status": _status_for_rate(rate, soft=soft, hard=hard),
        "contract_exclusions_rate": rate,
        "contract_exclusions_soft_limit": soft,
        "contract_exclusions_hard_limit": hard,
    }


def extract_records_in(funnel: object) -> int | None:
    """Return bronze (else extract) ``records_in``, or null when unavailable."""
    stages = _stage_map(funnel)
    for stage_id in ("bronze", "extract"):
        value = _stage_records_in(stages.get(stage_id))
        if value is not None:
            return value
    return None


def _exclusion_rate(funnel: object) -> float | None:
    """Rate over bronze/silver/gold; extra stages (e.g. extract) are allowed."""
    stages = _stage_map(funnel)
    ordered = _required_stages(stages)
    if ordered is None:
        return None
    return _rate_for_stages(ordered)


def _rate_for_stages(stages: Sequence[Mapping[str, object]]) -> float | None:
    base = _non_negative_int(stages[0].get("records_out"))
    if base is None:
        return None
    excluded_total = _excluded_total(stages)
    if excluded_total is None or excluded_total > base:
        return None
    if base == 0:
        return 0.0
    return excluded_total / base


def _required_stages(
    stages: dict[str, Mapping[str, object]],
) -> list[Mapping[str, object]] | None:
    """Return bronze/silver/gold only; ignore extract and other extras."""
    ordered = _required_stage_entries(stages)
    if ordered is None:
        return None
    if not _all_stages_fully_tracked(ordered):
        return None
    return ordered


def _required_stage_entries(
    stages: dict[str, Mapping[str, object]],
) -> list[Mapping[str, object]] | None:
    ordered: list[Mapping[str, object]] = []
    for stage_id in _STAGE_IDS:
        stage = stages.get(stage_id)
        if stage is None:
            return None
        ordered.append(stage)
    return ordered


def _all_stages_fully_tracked(stages: Sequence[Mapping[str, object]]) -> bool:
    return all(_stage_fully_tracked(stage) for stage in stages)


def _excluded_total(stages: Sequence[Mapping[str, object]]) -> int | None:
    total = 0
    for stage in stages:
        count = _stage_excluded_count(stage)
        if count is None:
            return None
        total += count
    return total


def _stage_excluded_count(stage: Mapping[str, object]) -> int | None:
    removals = _removal_sequence(stage.get("removals"))
    if removals is None:
        return None
    total = 0
    for removal in removals:
        count = _excluded_removal_count(removal)
        if count is None:
            return None
        total += count
    return total


def _removal_sequence(value: object) -> Sequence[object] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    return value


def _excluded_removal_count(removal: object) -> int | None:
    if not isinstance(removal, Mapping):
        return None
    if removal.get("outcome") != _EXCLUDED:
        return 0
    return _non_negative_int(removal.get("count"))


def _stage_records_in(stage: Mapping[str, object] | None) -> int | None:
    if stage is None:
        return None
    return _non_negative_int(stage.get("records_in"))


def _status_for_rate(rate: float | None, *, soft: float, hard: float) -> str:
    if rate is None:
        return _UNKNOWN
    if rate >= hard:
        return _CRIT
    if rate >= soft:
        return _WARN
    return _OK


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _stage_fully_tracked(stage: Mapping[str, object]) -> bool:
    tracking = stage.get("tracking")
    removals = stage.get("removals")
    return tracking == "full" and isinstance(removals, list)


def _stage_map(funnel: object) -> dict[str, Mapping[str, object]]:
    return dict(_iter_stage_entries(funnel))


def _iter_stage_entries(
    funnel: object,
) -> list[tuple[str, Mapping[str, object]]]:
    if not isinstance(funnel, Sequence) or isinstance(funnel, (str, bytes)):
        return []
    return [entry for item in funnel if (entry := _stage_entry(item)) is not None]


def _stage_entry(item: object) -> tuple[str, Mapping[str, object]] | None:
    if not isinstance(item, Mapping):
        return None
    stage_id = item.get("stage_id")
    if isinstance(stage_id, str) and stage_id:
        return stage_id, item
    return None
