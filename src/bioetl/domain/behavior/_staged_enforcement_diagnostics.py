"""Diagnostics and serialization helpers for staged enforcement."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from .staged_enforcement import CheckResult, EnforcementPolicy


def _serialize_policies(policies: dict[str, EnforcementPolicy]) -> JsonDict:
    """Serialize enforcement policies for diagnostics output."""
    return {
        name: {
            "current_stage": policy.current_stage.value,
            "failure_threshold": policy.failure_threshold,
            "warning_threshold": policy.warning_threshold,
            "observe_until": policy.observe_until,
            "soft_fail_until": policy.soft_fail_until,
        }
        for name, policy in policies.items()
    }


def _passed_checks(results: list[CheckResult]) -> int:
    """Count passed checks."""
    return sum(1 for result in results if result.passed)


def _failed_checks(results: list[CheckResult]) -> int:
    """Count failed checks."""
    return sum(1 for result in results if not result.passed)


def _check_details(results: list[CheckResult]) -> JsonDict:
    """Serialize all check results keyed by check name."""
    return {result.check_name: result.to_dict() for result in results}


def _pass_rates(grouped_results: dict[str, list[CheckResult]]) -> JsonDict:
    """Calculate pass rates by check name."""
    return {
        check_name: _calculate_pass_rate(results)
        for check_name, results in grouped_results.items()
    }


def _build_diagnostics_report(
    results: list[CheckResult],
    grouped_results: dict[str, list[CheckResult]],
    policies: dict[str, EnforcementPolicy],
) -> JsonDict:
    """Build diagnostics report payload from engine state."""
    return {
        "total_checks": len(results),
        "passed_checks": _passed_checks(results),
        "failed_checks": _failed_checks(results),
        "check_details": _check_details(results),
        "enforcement_policies": _serialize_policies(policies),
        "pass_rates": _pass_rates(grouped_results),
    }


def _group_results_by_check(results: list[CheckResult]) -> dict[str, list[CheckResult]]:
    """Group check results by check name."""
    grouped: dict[str, list[CheckResult]] = {}
    for result in results:
        grouped.setdefault(result.check_name, []).append(result)
    return grouped


def _calculate_pass_rate(results: list[CheckResult]) -> float:
    """Calculate pass rate for a single check group."""
    if not results:
        return 0.0
    return sum(1 for result in results if result.passed) / len(results)
