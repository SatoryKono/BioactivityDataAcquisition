"""Unit tests for staged enforcement policies and diagnostics helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.staged_enforcement import (
    CheckResult,
    EnforcementPolicy,
    EnforcementStage,
    StagedEnforcementEngine,
    _build_diagnostics_report,
    _calculate_pass_rate,
    _check_details,
    _failed_checks,
    _group_results_by_check,
    _pass_rates,
    _passed_checks,
    _serialize_policies,
    create_enforcement_engine,
)


pytestmark = pytest.mark.unit

def _make_result(
    check_name: str,
    passed: bool,
    *,
    message: str = "result",
    details: dict[str, object] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> CheckResult:
    return CheckResult(
        check_name=check_name,
        passed=passed,
        message=message,
        details=details,
        diagnostics=diagnostics,
    )


def test_check_result_to_dict_preserves_payloads() -> None:
    result = _make_result(
        "fixture_governance",
        True,
        message="all good",
        details={"count": 3},
        diagnostics={"elapsed_ms": 12},
    )

    assert result.to_dict() == {
        "check_name": "fixture_governance",
        "passed": True,
        "message": "all good",
        "details": {"count": 3},
        "diagnostics": {"elapsed_ms": 12},
    }


@pytest.mark.parametrize(
    ("failure_rate", "expected"),
    [
        (0.0, EnforcementStage.OBSERVE),
        (0.39, EnforcementStage.OBSERVE),
        (0.4, EnforcementStage.SOFT_FAIL),
        (0.89, EnforcementStage.SOFT_FAIL),
        (0.9, EnforcementStage.HARD_FAIL),
    ],
)
def test_enforcement_policy_get_effective_stage_uses_thresholds(
    failure_rate: float, expected: EnforcementStage
) -> None:
    policy = EnforcementPolicy(
        check_name="schema_compatibility",
        current_stage=EnforcementStage.OBSERVE,
        failure_threshold=0.9,
        warning_threshold=0.4,
    )

    assert policy.get_effective_stage(failure_rate) is expected


def test_engine_loads_default_and_contract_policies() -> None:
    engine = StagedEnforcementEngine()

    assert "fixture_governance" in engine.policies
    assert "contract_identity" in engine.policies
    assert "contract_identity" in engine._contract_policies
    assert engine.results == []


def test_get_enforcement_verdict_handles_empty_counts_and_missing_policy() -> None:
    engine = StagedEnforcementEngine()

    no_items = engine.get_enforcement_verdict("fixture_governance", 0, 0)
    missing_policy = engine.get_enforcement_verdict("missing", 1, 2)

    assert no_items == (EnforcementStage.OBSERVE, "No items to check")
    assert missing_policy == (EnforcementStage.OBSERVE, "No policy defined")


@pytest.mark.parametrize(
    ("failure_count", "total_count", "expected_stage", "message_fragment"),
    [
        (1, 10, EnforcementStage.OBSERVE, "Observation mode"),
        (4, 10, EnforcementStage.SOFT_FAIL, "Soft fail threshold exceeded"),
        (8, 10, EnforcementStage.HARD_FAIL, "Hard fail threshold exceeded"),
    ],
)
def test_get_enforcement_verdict_builds_stage_specific_messages(
    failure_count: int,
    total_count: int,
    expected_stage: EnforcementStage,
    message_fragment: str,
) -> None:
    engine = StagedEnforcementEngine()

    stage, message = engine.get_enforcement_verdict(
        "fixture_governance",
        failure_count,
        total_count,
    )

    assert stage is expected_stage
    assert message_fragment in message


def test_diagnostics_helpers_summarize_results_and_policies() -> None:
    policies = {
        "fixture_governance": EnforcementPolicy(
            check_name="fixture_governance",
            current_stage=EnforcementStage.SOFT_FAIL,
            failure_threshold=0.8,
            warning_threshold=0.3,
            observe_until="2024-04-01",
            soft_fail_until="2024-06-01",
        ),
    }
    results = [
        _make_result("fixture_governance", True, message="ok"),
        _make_result("fixture_governance", False, message="bad", details={"row": 1}),
        _make_result("schema_compatibility", True, message="schema ok"),
    ]

    grouped = _group_results_by_check(results)

    assert _passed_checks(results) == 2
    assert _failed_checks(results) == 1
    assert grouped["fixture_governance"][1].message == "bad"
    assert _calculate_pass_rate(grouped["fixture_governance"]) == pytest.approx(0.5)
    assert _calculate_pass_rate([]) == pytest.approx(0.0)
    assert _check_details(results)["schema_compatibility"]["passed"] is True
    assert _serialize_policies(policies) == {
        "fixture_governance": {
            "current_stage": "soft_fail",
            "failure_threshold": 0.8,
            "warning_threshold": 0.3,
            "observe_until": "2024-04-01",
            "soft_fail_until": "2024-06-01",
        }
    }
    assert _pass_rates(grouped) == {
        "fixture_governance": 0.5,
        "schema_compatibility": 1.0,
    }

    report = _build_diagnostics_report(results, grouped, policies)

    assert report["total_checks"] == 3
    assert report["passed_checks"] == 2
    assert report["failed_checks"] == 1
    assert report["pass_rates"]["fixture_governance"] == pytest.approx(0.5)
    assert (
        report["enforcement_policies"]["fixture_governance"]["current_stage"]
        == "soft_fail"
    )


def test_engine_register_result_generate_report_and_block_ci_only_on_hard_fail() -> (
    None
):
    engine = StagedEnforcementEngine()
    engine.results = []

    non_blocking = _make_result("missing_policy", False, message="warning")
    blocking = _make_result("fixture_governance", False, message="hard fail")
    passing = _make_result("schema_compatibility", True, message="ok")

    engine.register_result(non_blocking)
    engine.register_result(passing)

    report = engine.generate_diagnostics_report()

    assert report["total_checks"] == 2
    assert report["failed_checks"] == 1
    assert engine.should_block_ci() is False

    engine.register_result(blocking)

    assert engine.should_block_ci() is True


def test_engine_should_block_ci_ignores_results_without_policy() -> None:
    engine = StagedEnforcementEngine()
    engine.results = [_make_result("missing_policy", False)]

    assert engine.should_block_ci() is False


def test_create_enforcement_engine_returns_initialized_engine() -> None:
    engine = create_enforcement_engine()

    assert isinstance(engine, StagedEnforcementEngine)
    assert "fixture_governance" in engine.policies
