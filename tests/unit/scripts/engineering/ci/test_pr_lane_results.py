"""Unit tests for coordinator job-result mapping."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    assert_step_outcomes,
    build_results,
    main as lane_main,
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


def test_affected_targets_map_memory_source_without_test_diff() -> None:
    """A chunking-only PR must select its real RAG regression suite."""
    repo_root = Path(__file__).resolve().parents[5]
    targets = affected_pytest_targets(
        ["src/memory/rag/chunking.py", "src/memory/rag/chunking.py"],
        repo_root=repo_root,
    )

    assert targets == ["tests/unit/memory/test_rag_indexing.py"]
    assert all((repo_root / target).is_file() for target in targets)


def test_affected_targets_fail_closed_without_memory_test(tmp_path: Path) -> None:
    """A mapping never turns an absent test into a passing target."""
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets(["src/memory/rag/chunking.py"], repo_root=tmp_path)


def test_affected_targets_map_root_npm_only_and_deduplicate() -> None:
    """Manifest-only tooling updates execute their existing runtime contract."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        ["package.json", "package-lock.json", "package.json"], repo_root=repo_root
    ) == [
        "tests/architecture/test_observability_dashboard_tooling.py",
        "tests/unit/repo_backed/scripts/ai/test_npm_runtime_contract.py",
    ]


def test_python_dependency_diff_must_be_verified(tmp_path: Path) -> None:
    """No fixed unrelated list can qualify a Python dependency gate."""
    with pytest.raises(ValueError, match="verified dependency diff"):
        affected_pytest_targets(["uv.lock"], repo_root=tmp_path)


@pytest.mark.parametrize(
    "changed_file", ["package.json", "package-lock.json", "pyproject.toml", "uv.lock"]
)
def test_root_npm_lane_fails_when_target_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], changed_file: str
) -> None:
    """An absent mapped contract cannot satisfy required affected-tests."""
    with pytest.raises(ValueError):
        affected_pytest_targets([changed_file], repo_root=tmp_path)
    assert (
        lane_main(
            [
                "affected-tests",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                changed_file,
            ]
        )
        == 1
    )
    assert "tests gate selection failed" in capsys.readouterr().err


def test_affected_targets_preserve_bioetl_and_scripts_routes(tmp_path: Path) -> None:
    """Memory routing keeps the existing source and script selection."""
    (tmp_path / "tests/unit/domain").mkdir(parents=True)
    script_test = tmp_path / "tests/unit/scripts/engineering/ci/test_tool.py"
    script_test.parent.mkdir(parents=True)
    script_test.write_text("def test_tool():\n    assert True\n", encoding="utf-8")

    targets = affected_pytest_targets(
        ["src/bioetl/domain/sample.py", "scripts/engineering/ci/tool.py"],
        repo_root=tmp_path,
    )

    assert targets == [
        "tests/unit/domain",
        "tests/unit/scripts/engineering/ci/test_tool.py",
    ]


def test_build_rejects_unknown_decision() -> None:
    """Reject gate decisions outside the coordinator decision vocabulary."""
    with pytest.raises(ValueError, match="unknown decision"):
        build_results(
            {"tests": {"decision": "maybe"}},
            {},
            head_sha=HEAD,
        )


@pytest.mark.parametrize("missing_count", [0, 1, 2])
def test_partial_mapped_targets_fail_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing_count: int,
) -> None:
    """Reject partial mappings before printing targets for the caller to run."""
    from scripts.engineering.ci import pr_lane_results as lane

    mapped = ("tests/unit/test_one.py", "tests/unit/test_two.py")
    monkeypatch.setitem(lane.AFFECTED_TESTS_BY_PATH, "fixture/source.py", mapped)
    for target in mapped[: 2 - missing_count]:
        path = tmp_path / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_contract(): pass\n", encoding="utf-8")
    result = lane_main(
        [
            "affected-tests",
            "--repo-root",
            str(tmp_path),
            "--changed-file",
            "fixture/source.py",
        ]
    )
    captured = capsys.readouterr()
    if missing_count:
        assert result == 1
        assert not captured.out
        for target in mapped[2 - missing_count :]:
            assert target in captured.err
    else:
        assert result == 0
        assert captured.out.splitlines() == list(mapped)
