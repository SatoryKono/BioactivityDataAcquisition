"""Unit tests for coordinator job-result mapping."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    assert_step_outcomes,
    build_results,
)

pytestmark = pytest.mark.unit

HEAD = "a" * 40


def test_not_applicable_gate_does_not_inherit_job_success() -> None:
    """Keep a nonapplicable gate skipped even when its owner job succeeds."""
    results = build_results(
        {
            "docs-governance": {
                "decision": "not_applicable",
                "reason": "no_path_match",
            }
        },
        {"fast-governance": "success"},
        head_sha=HEAD,
    )

    assert results["docs-governance"] == {
        "required": "skipped",
        "not_applicable": "success",
        "na_head_sha": HEAD,
        "na_reason": "no_path_match",
    }


def test_required_gate_is_red_when_owner_job_is_skipped() -> None:
    """Keep required evidence missing when the owning CI job is skipped."""
    results = build_results(
        {"tests": {"decision": "required", "reason": "path_match"}},
        {"class-lane": "skipped"},
        head_sha=HEAD,
    )

    assert results["tests"]["required"] == "skipped"
    assert results["tests"]["not_applicable"] == "skipped"


def test_required_gate_passes_only_when_owner_job_succeeds() -> None:
    """Map a successful owner job to a successful required gate."""
    results = build_results(
        {"lint-arch": {"decision": "required", "reason": "path_match"}},
        {"class-lane": "success"},
        head_sha=HEAD,
    )

    assert results["lint-arch"]["required"] == "success"


def test_cancelled_job_is_failure() -> None:
    """Treat a cancelled owner job as failure for its required gate."""
    results = build_results(
        {"security": {"decision": "required", "reason": "path_match"}},
        {"class-lane": "cancelled"},
        head_sha=HEAD,
    )

    assert results["security"]["required"] == "failure"


def test_assert_steps_ignores_not_applicable_gates() -> None:
    """Allow missing step evidence for gates classified as nonapplicable."""
    failures = assert_step_outcomes(
        {"docker": {"decision": "not_applicable", "reason": "no_path_match"}},
        {},
        owner="class-lane",
    )

    assert failures == []


def test_assert_steps_fails_when_required_step_is_skipped() -> None:
    """Report a skipped required type-checking step as a failure."""
    failures = assert_step_outcomes(
        {"type-checking": {"decision": "required", "reason": "path_match"}},
        {
            "mypy": "skipped",
            "newtype-protocol": "success",
            "any-usage": "success",
        },
        owner="class-lane",
    )

    assert failures == ["type-checking:mypy=skipped"]


def test_assert_steps_fails_on_unrelated_step_failure() -> None:
    """Report failed job steps even when all required gate steps pass."""
    failures = assert_step_outcomes(
        {"type-checking": {"decision": "required", "reason": "path_match"}},
        {
            "mypy": "success",
            "newtype-protocol": "success",
            "any-usage": "success",
            "checkout": "failure",
        },
        owner="class-lane",
    )

    assert "step:checkout=failure" in failures


def test_affected_targets_map_source_and_existing_tests(tmp_path: Path) -> None:
    """Select source-layer tests and existing test paths, excluding missing paths."""
    unit_domain = tmp_path / "tests" / "unit" / "domain"
    unit_domain.mkdir(parents=True)
    test_file = tmp_path / "tests" / "unit" / "domain" / "test_sample.py"
    test_file.write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    missing = tmp_path / "tests" / "unit" / "missing_test.py"

    targets = affected_pytest_targets(
        [
            "src/bioetl/domain/sample.py",
            test_file.relative_to(tmp_path).as_posix(),
            missing.relative_to(tmp_path).as_posix(),
            "docs/readme.md",
        ],
        repo_root=tmp_path,
    )

    assert targets == [
        "tests/unit/domain",
        "tests/unit/domain/test_sample.py",
    ]


def test_affected_targets_map_telemetry_baseline(tmp_path: Path) -> None:
    """Telemetry baseline edits select the governance test and leave other configs unmapped."""
    governance = tmp_path / "tests/architecture/test_test_telemetry_governance.py"
    governance.parent.mkdir(parents=True)
    governance.write_text(
        "def test_identity() -> None:\n    assert True\n", encoding="utf-8"
    )
    targets = affected_pytest_targets(
        [
            "configs/quality/test_telemetry_baseline.yaml",
            "docs/readme.md",
        ],
        repo_root=tmp_path,
    )
    untouched = affected_pytest_targets(
        ["configs/quality/github_required_checks.yaml"],
        repo_root=tmp_path,
    )

    assert targets == ["tests/architecture/test_test_telemetry_governance.py"]
    assert untouched == []


def test_build_rejects_unknown_decision() -> None:
    """Reject gate decisions outside the coordinator decision vocabulary."""
    with pytest.raises(ValueError, match="unknown decision"):
        build_results(
            {"tests": {"decision": "maybe"}},
            {},
            head_sha=HEAD,
        )
