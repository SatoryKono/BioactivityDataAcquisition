"""Internal helpers for externalized shared composite policy merging."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config._composite_dq_externalization import (
    _deep_merge_dicts,
)

__all__ = ["merge_external_shared_policy"]


def _load_external_shared_policy(
    policy_file: str,
    config_path: Path,
) -> JsonDict:
    """Load and validate shared composite policy payload."""
    policy_path = config_path.parent / policy_file
    if not policy_path.exists():
        raise FileNotFoundError(
            "Composite shared policy not found: "
            f"{policy_path} (referenced from {config_path})"
        )

    with policy_path.open(encoding="utf-8") as handle:
        external_raw = yaml.safe_load(handle) or {}

    if not isinstance(external_raw, dict):
        raise ValueError(f"Composite shared policy must be a mapping: {policy_path}")
    return external_raw


def merge_external_shared_policy(
    raw: JsonDict,
    config_path: Path,
) -> None:
    """Merge shared composite policy into the inline composite payload."""
    composite = raw.get("composite")
    if not isinstance(composite, dict):
        return

    maintenance = raw.get("maintenance")
    if not isinstance(maintenance, dict):
        return

    policy_file = maintenance.get("composite_shared_policy_file")
    if not isinstance(policy_file, str) or not policy_file.strip():
        return

    external_policy = _load_external_shared_policy(policy_file, config_path)
    raw["composite"] = _deep_merge_dicts(external_policy, composite)
