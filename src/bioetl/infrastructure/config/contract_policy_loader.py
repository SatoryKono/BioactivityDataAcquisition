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


def _load_base_contract_defaults() -> dict[
    str, Any  # Any: YAML config has heterogeneous values
]:  # Any: YAML config has heterogeneous values
    """Load contract defaults from consolidated base config if present."""
    base_path = _CONFIGS_ROOT / "base" / "pipeline.yaml"
    if not base_path.exists():
        return {}

    with open(base_path, encoding="utf-8") as f:
        base_raw: dict[str, Any] = (  # Any: YAML config has heterogeneous values
            yaml.safe_load(f) or {}
        )  # Any: YAML config has heterogeneous values

    defaults = base_raw.get("contract_defaults")
    return defaults if isinstance(defaults, dict) else {}


@lru_cache(maxsize=128)
def load_pipeline_contract_policy(provider: str, entity: str) -> PipelineContractPolicy:
    """Load typed policy from unified entity config contracts section.

    Args:
        provider: Data provider name.
        entity: Entity.

    Returns:
        Loaded PipelineContractPolicy.
    """
    base_defaults = _load_base_contract_defaults()

    unified_entity_path = _CONFIGS_ROOT / "entities" / provider / f"{entity}.yaml"
    if not unified_entity_path.exists():
        raise ValueError(f"Contract policy file not found: {unified_entity_path}")

    with open(unified_entity_path, encoding="utf-8") as f:
        unified_raw: dict[str, Any] = (  # Any: YAML config has heterogeneous values
            yaml.safe_load(f) or {}
        )  # Any: YAML config has heterogeneous values

    contracts_section = unified_raw.get("contracts")
    if not isinstance(contracts_section, dict):
        raise ValueError(
            f"Contract policy section 'contracts' not found in {unified_entity_path}"
        )

    raw = {**base_defaults, **contracts_section}
    result: PipelineContractPolicy = PipelineContractPolicy.model_validate(raw)
    return result
