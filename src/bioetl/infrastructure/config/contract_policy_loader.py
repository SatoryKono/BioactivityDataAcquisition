"""Loader for typed pipeline contract policy files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)

_CONFIGS_ROOT = Path("configs")


def _load_base_contract_defaults() -> dict[str, Any]:
    """Load contract defaults from consolidated base config if present."""
    base_path = _CONFIGS_ROOT / "base" / "pipeline.yaml"
    if not base_path.exists():
        return {}

    with open(base_path, encoding="utf-8") as f:
        base_raw: dict[str, Any] = yaml.safe_load(f) or {}

    defaults = base_raw.get("contract_defaults")
    return defaults if isinstance(defaults, dict) else {}


@lru_cache(maxsize=128)
def load_pipeline_contract_policy(provider: str, entity: str) -> PipelineContractPolicy:
    """Load typed policy from unified entity config or legacy contracts path."""
    base_defaults = _load_base_contract_defaults()

    unified_entity_path = _CONFIGS_ROOT / "entities" / provider / f"{entity}.yaml"
    if unified_entity_path.exists():
        with open(unified_entity_path, encoding="utf-8") as f:
            unified_raw: dict[str, Any] = yaml.safe_load(f) or {}

        contracts_section = unified_raw.get("contracts")
        if isinstance(contracts_section, dict):
            raw = {**base_defaults, **contracts_section}
            result: PipelineContractPolicy = PipelineContractPolicy.model_validate(raw)
            return result

    legacy_path = (
        _CONFIGS_ROOT / "contracts" / "pipelines" / provider / f"{entity}.yaml"
    )
    if not legacy_path.exists():
        raise ValueError(
            "Contract policy file not found in "
            f"{unified_entity_path} (section 'contracts') or {legacy_path}"
        )

    with open(legacy_path, encoding="utf-8") as f:
        legacy_raw: dict[str, Any] = yaml.safe_load(f) or {}

    raw = legacy_raw

    legacy_result: PipelineContractPolicy = PipelineContractPolicy.model_validate(raw)
    return legacy_result
