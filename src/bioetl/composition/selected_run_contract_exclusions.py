"""Contract-exclusion status and records_in for selected-run-status (plan 3.1).

Additive fields for Grafana: limits come from DQ configs; rate from saved funnel.
Status vocabulary is OK / WARN / CRIT / UNKNOWN (CRIT replaces the legacy
dashboard JSONata ``ERROR`` hard-limit label).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader

_OK = "OK"
_WARN = "WARN"
_CRIT = "CRIT"
_UNKNOWN = "UNKNOWN"
_STAGE_IDS = ("bronze", "silver", "gold")
_EXCLUDED = "excluded_by_contract"


def evaluate_contract_exclusions(
    pipeline: str,
    funnel: object,
    *,
    configs_root: Path | None = None,
) -> dict[str, object]:
    """Return contract_exclusions_* fields for one pipeline/funnel snapshot."""
    soft, hard = _limits_for_pipeline(pipeline, configs_root=configs_root)
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


def attach_contract_fields(
    payload: dict[str, object],
    *,
    configs_root: Path | None = None,
) -> dict[str, object]:
    """Mutate and return payload with 3.1 contract fields (additive)."""
    pipeline = str(payload.get("pipeline") or "")
    quality = payload.get("quality_evidence")
    funnel: object = None
    if isinstance(quality, Mapping):
        funnel = quality.get("funnel")
    payload.update(
        evaluate_contract_exclusions(pipeline, funnel, configs_root=configs_root)
    )
    payload["records_in"] = extract_records_in(funnel)
    return payload


def _limits_for_pipeline(
    pipeline: str,
    *,
    configs_root: Path | None = None,
) -> tuple[float | None, float | None]:
    if not pipeline or pipeline in {".*", "-", "All", "$__all", "unknown"}:
        return None, None
    root = resolve_configs_root(configs_root)
    limits = _pipeline_limits_map(str(root), _configs_signature(root))
    pair = limits.get(pipeline)
    if pair is None:
        return None, None
    soft, hard = pair
    return soft, hard


def _configs_signature(root: Path) -> str:
    """Invalidate limits cache when DQ-related YAML mtimes/sizes change."""
    parts: list[str] = []
    for relative in ("entities", "providers", "base"):
        base = root / relative
        if not base.is_dir():
            continue
        pattern = "*/*.yaml" if relative == "entities" else "*.yaml"
        for path in sorted(base.glob(pattern)):
            try:
                stat = path.stat()
            except OSError:
                parts.append(f"{path.as_posix()}:missing")
                continue
            parts.append(f"{path.as_posix()}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


@lru_cache(maxsize=8)
def _pipeline_limits_map(
    configs_root_key: str, signature: str
) -> dict[str, tuple[float, float]]:
    del signature  # participates in the cache key only
    root = Path(configs_root_key)
    loader = DQConfigLoader(root)
    limits: dict[str, tuple[float, float]] = {}
    entities_root = root / "entities"
    if not entities_root.is_dir():
        return limits
    for path in sorted(entities_root.glob("*/*.yaml")):
        pair = _limits_from_entity_path(loader, path)
        if pair is None:
            continue
        pipeline, soft, hard = pair
        limits[pipeline] = (soft, hard)
    return limits


def _limits_from_entity_path(
    loader: DQConfigLoader, path: Path
) -> tuple[str, float, float] | None:
    try:
        entity = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return None
    if not isinstance(entity, dict):
        return None
    pipeline_block = entity.get("pipeline")
    if not isinstance(pipeline_block, dict):
        return None
    pipeline = pipeline_block.get("pipeline_name")
    if not isinstance(pipeline, str) or not pipeline:
        return None
    try:
        config = loader.load(path.parent.name, path.stem)
    except (OSError, ValueError, TypeError, KeyError):
        return None
    soft = float(config.soft_fail_threshold)
    hard = float(config.hard_fail_threshold)
    if soft > hard:
        soft, hard = hard, soft
    return pipeline, soft, hard


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
    stages: dict[str, Mapping[str, Any]],
) -> list[Mapping[str, Any]] | None:
    """Return bronze/silver/gold only; ignore extract and other extras."""
    if any(stage_id not in stages for stage_id in _STAGE_IDS):
        return None
    ordered = [stages[stage_id] for stage_id in _STAGE_IDS]
    if not all(_stage_fully_tracked(stage) for stage in ordered):
        return None
    return ordered


def _excluded_total(stages: Sequence[Mapping[str, Any]]) -> int | None:
    total = 0
    for stage in stages:
        count = _stage_excluded_count(stage)
        if count is None:
            return None
        total += count
    return total


def _stage_excluded_count(stage: Mapping[str, Any]) -> int | None:
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


def _stage_fully_tracked(stage: Mapping[str, Any]) -> bool:
    tracking = stage.get("tracking")
    removals = stage.get("removals")
    return tracking == "full" and isinstance(removals, list)


def _stage_map(funnel: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(funnel, Sequence) or isinstance(funnel, (str, bytes)):
        return {}
    stages: dict[str, Mapping[str, Any]] = {}
    for item in funnel:
        if not isinstance(item, Mapping):
            continue
        stage_id = item.get("stage_id")
        if isinstance(stage_id, str) and stage_id:
            stages[stage_id] = item
    return stages