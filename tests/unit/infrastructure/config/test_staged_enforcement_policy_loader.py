# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for staged-enforcement policy registry loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_active_policies_are_rejected(tmp_path: Path, reverse: bool) -> None:
    rows = [
        {
            "check_name": "example",
            "current_stage": "hard_fail",
            "failure_threshold": 0.2,
            "warning_threshold": 0.1,
        },
        {
            "check_name": "example",
            "current_stage": "observe",
            "failure_threshold": 0.9,
            "warning_threshold": 0.1,
        },
    ]
    if reverse:
        rows.reverse()
    path = tmp_path / "policies.yaml"
    path.write_text(yaml.safe_dump({"policies": rows}), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate.*example") as exc:
        load_staged_enforcement_policies(path)
    assert str(path) in str(exc.value)


@pytest.mark.parametrize("excluded_first", [False, True])
def test_excluded_duplicate_does_not_override_active_verdict(
    tmp_path: Path, excluded_first: bool
) -> None:
    active = {
        "check_name": "example",
        "current_stage": "hard_fail",
        "failure_threshold": 0.2,
        "warning_threshold": 0.1,
    }
    excluded = {"check_name": "example", "domain_engine": False}
    rows = [excluded, active] if excluded_first else [active, excluded]
    path = tmp_path / "policies.yaml"
    path.write_text(yaml.safe_dump({"policies": rows}), encoding="utf-8")

    engine = StagedEnforcementEngine(load_staged_enforcement_policies(path))
    assert (
        engine.get_enforcement_verdict("example", 1, 2)[0] is EnforcementStage.HARD_FAIL
    )
