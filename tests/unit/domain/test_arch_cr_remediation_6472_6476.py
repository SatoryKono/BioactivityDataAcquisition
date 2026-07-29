# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Regression coverage for remaining CodeRabbit remediation issues."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.behavior import PhasedMigrationCoordinator
from bioetl.domain.behavior._dq_value_coercion import _coerce_numeric_value
from bioetl.domain.behavior.staged_enforcement import (
    EnforcementStage,
    StagedEnforcementEngine,
)
from bioetl.domain.config.validation_config import ValidationConfig

pytestmark = pytest.mark.unit


def test_phased_migration_coordinator_deprecated_facade() -> None:
    with pytest.warns(DeprecationWarning, match="retired compatibility shim"):
        coordinator = PhasedMigrationCoordinator()
    status = coordinator.get_current_migration_status()
    assert status.current_phase == "retired"
    report = coordinator.check_backward_compatibility({"x": 1})
    assert report["retired"] is True


def test_staged_enforcement_honors_empty_policy_map() -> None:
    engine = StagedEnforcementEngine(policies={})
    assert engine.policies == {}
    stage, message = engine.get_enforcement_verdict("missing", 1, 1)
    assert stage is EnforcementStage.OBSERVE
    assert "No policy" in message


def test_staged_enforcement_reports_rollout_cap() -> None:
    from bioetl.domain.behavior.staged_enforcement import EnforcementPolicy

    engine = StagedEnforcementEngine(
        policies={
            "fixture_governance": EnforcementPolicy(
                check_name="fixture_governance",
                current_stage=EnforcementStage.OBSERVE,
                failure_threshold=0.8,
                warning_threshold=0.3,
            )
        }
    )
    stage, message = engine.get_enforcement_verdict("fixture_governance", 5, 10)
    assert stage is EnforcementStage.OBSERVE
    assert "rollout cap" in message


def test_numeric_coercion_catches_overflow() -> None:
    # Extremely large ints may OverflowError on float() depending on platform.
    huge = 10**10000
    assert _coerce_numeric_value(huge) is None
    assert _coerce_numeric_value("not-a-number") is None
    assert _coerce_numeric_value(1.5) == 1.5


def test_validation_config_rejects_non_finite_bounds() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        ValidationConfig(min_molecular_weight=math.nan)
