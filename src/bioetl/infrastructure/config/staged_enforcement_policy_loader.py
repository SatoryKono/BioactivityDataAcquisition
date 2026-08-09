"""Canonical loader for staged-enforcement policy registry."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.behavior.staged_enforcement import (
    EnforcementPolicy,
    EnforcementStage,
)

DEFAULT_POLICY_REGISTRY_PATH = Path(
    "configs/quality/staged_enforcement_policy_registry.yaml"
)

_STAGE_BY_NAME = {
    stage.value: stage
    for stage in (
        EnforcementStage.OBSERVE,
        EnforcementStage.SOFT_FAIL,
        EnforcementStage.HARD_FAIL,
    )
}


def load_staged_enforcement_policies(
    registry_path: Path | None = None,
) -> dict[str, EnforcementPolicy]:
    """Load staged-enforcement policy definitions from governance config."""
    path = registry_path or DEFAULT_POLICY_REGISTRY_PATH
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    policies = payload.get("policies")
    if not isinstance(policies, list):
        raise ValueError(f"Expected 'policies' list in {path}")

    loaded: dict[str, EnforcementPolicy] = {}
    for row in policies:
        if not isinstance(row, dict):
            raise ValueError(f"Expected mapping policy row in {path}")
        # Control-plane policies share the governance registry but do not
        # participate in per-pipeline domain enforcement.
        if row.get("domain_engine", True) is False:
            continue
        check_name = str(row["check_name"])
        current_stage = _STAGE_BY_NAME[str(row["current_stage"])]
        loaded[check_name] = EnforcementPolicy(
            check_name=check_name,
            current_stage=current_stage,
            failure_threshold=float(row["failure_threshold"]),
            warning_threshold=float(row["warning_threshold"]),
        )
    return loaded


__all__ = ["DEFAULT_POLICY_REGISTRY_PATH", "load_staged_enforcement_policies"]
