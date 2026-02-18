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


@lru_cache(maxsize=128)
def load_pipeline_contract_policy(provider: str, entity: str) -> PipelineContractPolicy:
    """Load typed policy from configs/contracts/pipelines/{provider}/{entity}.yaml."""
    path = _CONFIGS_ROOT / "contracts" / "pipelines" / provider / f"{entity}.yaml"
    if not path.exists():
        raise ValueError(f"Contract policy file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    return PipelineContractPolicy.model_validate(raw)
