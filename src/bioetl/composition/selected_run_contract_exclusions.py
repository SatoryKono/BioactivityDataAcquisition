"""Composition wiring for selected-run contract exclusion fields (plan 3.1).

Loads DQ soft/hard limits from entity configs; pure status/funnel math lives in
``bioetl.domain.control_plane.selected_run_contract_exclusions``.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re

from bioetl.domain.control_plane.selected_run_contract_exclusions import (
    classify_contract_exclusions,
    extract_records_in,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader

_SAFE_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def evaluate_contract_exclusions(
    pipeline: str,
    funnel: object,
    *,
    configs_root: Path | None = None,
) -> dict[str, object]:
    """Return contract_exclusions_* fields for one pipeline/funnel snapshot."""
    soft, hard = _limits_for_pipeline(pipeline, configs_root=configs_root)
    return classify_contract_exclusions(soft, hard, funnel)


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
    provider, separator, entity = pipeline.partition("_")
    if (
        not separator
        or not _SAFE_SEGMENT.fullmatch(provider)
        or not _SAFE_SEGMENT.fullmatch(entity)
    ):
        return None, None
    root = resolve_configs_root(configs_root)
    entity_path = root / "entities" / provider / f"{entity}.yaml"
    if not entity_path.is_file():
        return None, None
    try:
        config = DQConfigLoader(root).load(provider, entity)
    except (OSError, ValueError, TypeError, KeyError):
        return None, None
    soft = float(config.soft_fail_threshold)
    hard = float(config.hard_fail_threshold)
    if soft > hard:
        soft, hard = hard, soft
    return soft, hard


__all__ = [
    "attach_contract_fields",
    "evaluate_contract_exclusions",
    "extract_records_in",
]
