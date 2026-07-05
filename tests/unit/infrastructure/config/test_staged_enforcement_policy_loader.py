"""Unit tests for staged-enforcement policy registry loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.behavior.staged_enforcement import (
    EnforcementStage,
    StagedEnforcementEngine,
)
from bioetl.infrastructure.config.staged_enforcement_policy_loader import (
    load_staged_enforcement_policies,
)


ROOT = Path(__file__).resolve().parents[4]
REGISTRY_PATH = ROOT / "configs" / "quality" / "staged_enforcement_policy_registry.yaml"

pytestmark = pytest.mark.unit


def test_loader_reads_externalized_policy_registry() -> None:
    loaded = load_staged_enforcement_policies(REGISTRY_PATH)

    assert set(loaded) == {
        "fixture_governance",
        "checkpoint_compatibility",
        "effective_config_stability",
        "contract_identity",
        "registry_consistency",
        "schema_compatibility",
    }
    assert loaded["fixture_governance"].current_stage is EnforcementStage.SOFT_FAIL
    assert loaded["schema_compatibility"].warning_threshold == pytest.approx(0.4)


def test_loader_matches_domain_default_thresholds() -> None:
    loaded = load_staged_enforcement_policies(REGISTRY_PATH)
    engine = StagedEnforcementEngine()

    assert {
        name: (
            policy.current_stage.value,
            policy.failure_threshold,
            policy.warning_threshold,
        )
        for name, policy in loaded.items()
    } == {
        name: (
            policy.current_stage.value,
            policy.failure_threshold,
            policy.warning_threshold,
        )
        for name, policy in engine.policies.items()
    }
