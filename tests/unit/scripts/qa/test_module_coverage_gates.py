"""Tests for per-module coverage gate evaluation."""

from __future__ import annotations

from scripts.engineering.qa.report_module_coverage_inventory import (
    evaluate_module_coverage_gates,
)

pytestmark = __import__("pytest").mark.unit


def _row(path: str, percent: float) -> dict[str, object]:
    return {
        "path": path,
        "coverage_status": "partially_covered",
        "coverage_percent": percent,
    }


def _gates() -> dict[str, object]:
    return {
        "enforcement": {
            "tier_violation_mode": "warn",
            "ranked_target_tier_violation_mode": "block",
        },
        "tiers": {
            "default_module": {
                "line_min_percent": 85,
                "path_prefixes": ["src/bioetl/"],
            },
            "aggregates_and_contracts": {
                "line_min_percent": 95,
                "path_prefixes": ["src/bioetl/domain/aggregates/"],
            },
        },
        "tier_resolution_order": ["aggregates_and_contracts", "default_module"],
        "regression": {"min_delta_points": 0.01},
        "coverage_tail": {
            "ranked_targets": [
                {"rank": 1, "path": "src/bioetl/domain/aggregates/_batch_lifecycle.py"}
            ]
        },
        "exemptions": [],
    }


def test_block_regression_detects_coverage_decrease() -> None:
    payload = {
        "modules": [_row("src/bioetl/domain/aggregates/_other_aggregate.py", 90.0)]
    }
    baseline = {
        "modules": [_row("src/bioetl/domain/aggregates/_other_aggregate.py", 95.0)]
    }

    violations = evaluate_module_coverage_gates(
        payload,
        baseline_payload=baseline,
        gates=_gates(),
        enforcement_mode="block-regression",
    )

    assert len(violations) == 1
    assert violations[0].kind == "regression"


def test_block_regression_ignores_tier_gaps() -> None:
    payload = {
        "modules": [_row("src/bioetl/domain/aggregates/_other_aggregate.py", 90.0)]
    }
    baseline = {
        "modules": [_row("src/bioetl/domain/aggregates/_other_aggregate.py", 90.0)]
    }

    violations = evaluate_module_coverage_gates(
        payload,
        baseline_payload=baseline,
        gates=_gates(),
        enforcement_mode="block-regression",
    )

    assert violations == []


def test_block_regression_blocks_ranked_target_tier_gap() -> None:
    payload = {
        "modules": [_row("src/bioetl/domain/aggregates/_batch_lifecycle.py", 90.0)]
    }
    baseline = {
        "modules": [_row("src/bioetl/domain/aggregates/_batch_lifecycle.py", 90.0)]
    }

    violations = evaluate_module_coverage_gates(
        payload,
        baseline_payload=baseline,
        gates=_gates(),
        enforcement_mode="block-regression",
    )

    assert len(violations) == 1
    assert violations[0].kind == "tier"


def test_block_all_reports_tier_gap() -> None:
    payload = {
        "modules": [_row("src/bioetl/domain/aggregates/_batch_lifecycle.py", 90.0)]
    }
    baseline = {
        "modules": [_row("src/bioetl/domain/aggregates/_batch_lifecycle.py", 90.0)]
    }

    violations = evaluate_module_coverage_gates(
        payload,
        baseline_payload=baseline,
        gates=_gates(),
        enforcement_mode="block-all",
    )

    assert any(violation.kind == "tier" for violation in violations)
