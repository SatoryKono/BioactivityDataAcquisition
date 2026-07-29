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
"""Unit tests for staged enforcement domain helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.staged_enforcement import (
    CheckResult,
    EnforcementPolicy,
    EnforcementStage,
    StagedEnforcementEngine,
    _calculate_pass_rate,
    _group_results_by_check,
    _serialize_policies,
    create_enforcement_engine,
)

pytestmark = pytest.mark.unit


def test_check_result_serializes_details_and_diagnostics() -> None:
    result = CheckResult(
        "schema_compatibility",
        passed=False,
        message="missing field",
        details={"field": "pmid"},
        diagnostics={"layer": "gold"},
    )

    assert result.to_dict() == {
        "check_name": "schema_compatibility",
        "passed": False,
        "message": "missing field",
        "details": {"field": "pmid"},
        "diagnostics": {"layer": "gold"},
    }


def test_policy_resolves_observe_soft_and_hard_stages() -> None:
    policy = EnforcementPolicy(
        check_name="contract_identity",
        current_stage=EnforcementStage.OBSERVE,
        failure_threshold=0.8,
        warning_threshold=0.3,
    )

    assert policy.get_effective_stage(0.1) == EnforcementStage.OBSERVE
    assert policy.get_effective_stage(0.3) == EnforcementStage.SOFT_FAIL
    assert policy.get_effective_stage(0.8) == EnforcementStage.HARD_FAIL


def test_engine_verdicts_respect_current_stage_cap() -> None:
    engine = StagedEnforcementEngine()

    assert engine.get_enforcement_verdict("fixture_governance", 0, 0) == (
        EnforcementStage.OBSERVE,
        "No items to check",
    )
    assert engine.get_enforcement_verdict("missing_policy", 1, 2) == (
        EnforcementStage.OBSERVE,
        "No policy defined",
    )
    assert engine.get_enforcement_verdict("fixture_governance", 1, 2)[0] == (
        EnforcementStage.SOFT_FAIL
    )
    stage, message = engine.get_enforcement_verdict("fixture_governance", 4, 5)
    assert stage is EnforcementStage.SOFT_FAIL
    assert "Soft fail threshold exceeded" in message


def test_engine_reports_pass_rates_and_blocking_decision() -> None:
    engine = create_enforcement_engine()
    engine.register_result(CheckResult("fixture_governance", False, "bad fixture"))
    engine.register_result(CheckResult("schema_compatibility", True, "ok"))

    report = engine.generate_diagnostics_report()

    assert report["total_checks"] == 2
    assert report["passed_checks"] == 1
    assert report["failed_checks"] == 1
    assert report["pass_rates"]["fixture_governance"] == 0.0
    assert report["pass_rates"]["schema_compatibility"] == 1.0
    assert engine.should_block_ci() is False


def test_grouping_and_policy_serialization_helpers_are_stable() -> None:
    results = [
        CheckResult("a", True, "ok"),
        CheckResult("a", False, "bad"),
        CheckResult("b", True, "ok"),
    ]
    grouped = _group_results_by_check(results)
    policies = _serialize_policies(
        {
            "a": EnforcementPolicy(
                "a",
                EnforcementStage.SOFT_FAIL,
                observe_until="2026-01-01",
                soft_fail_until="2026-02-01",
            )
        }
    )

    assert set(grouped) == {"a", "b"}
    assert _calculate_pass_rate(grouped["a"]) == 0.5
    assert _calculate_pass_rate([]) == 0.0
    assert policies["a"]["current_stage"] == "soft_fail"
    assert policies["a"]["observe_until"] == "2026-01-01"


def test_engine_contract_subset_comes_from_single_default_policy_map() -> None:
    engine = StagedEnforcementEngine()

    assert set(engine._contract_policies) == {
        "contract_identity",
        "registry_consistency",
        "schema_compatibility",
    }
    assert all(name in engine.policies for name in engine._contract_policies)
