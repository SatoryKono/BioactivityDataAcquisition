"""Unit tests for coordinator job-result mapping."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    OWNER_STEPS,
    affected_pytest_targets,
    assert_step_outcomes,
    build_results,
    build_shadow_compare,
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


def test_docs_governance_requires_prose_consistency_step() -> None:
    """A selected docs-governance gate fails when the prose pytest step is skipped."""
    failures = assert_step_outcomes(
        {"docs-governance": {"decision": "required", "reason": "path_match"}},
        {
            "docs-passports": "success",
            "docs-links": "success",
            "docs-verify": "success",
            "mkdocs-nav": "success",
            "prose-consistency": "skipped",
        },
        owner="fast-governance",
    )

    assert failures == ["docs-governance:prose-consistency=skipped"]


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


def test_empty_diff_selects_full_python_suite() -> None:
    """An empty diff still has a required tests gate, so run the whole suite."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets([], repo_root=repo_root) == ["tests"]
    assert affected_pytest_targets(["   "], repo_root=repo_root) == ["tests"]


def test_empty_diff_fails_closed_when_suite_root_is_missing(tmp_path: Path) -> None:
    """A missing tests tree cannot satisfy the empty-diff tests gate."""
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets([], repo_root=tmp_path)


def test_empty_diff_cli_prints_full_suite(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The lane command must emit the full suite when git reports no paths."""
    from scripts.engineering.ci import pr_lane_results as lane

    def _empty_diff(
        *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["git"], returncode=0, stdout="")

    monkeypatch.setattr(lane.subprocess, "run", _empty_diff)
    repo_root = Path(__file__).resolve().parents[5]
    assert (
        lane_main(
            [
                "affected-tests",
                "--repo-root",
                str(repo_root),
                "--base-sha",
                HEAD,
                "--head-sha",
                HEAD,
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.splitlines() == ["tests"]


def test_shadow_compare_records_selection_without_activation(tmp_path: Path) -> None:
    """Shadow mode records a narrow selection and does not mark it activated."""
    unit_domain = tmp_path / "tests" / "unit" / "domain"
    unit_domain.mkdir(parents=True)
    (unit_domain / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["tests/unit/domain/test_sample.py"],
        repo_root=tmp_path,
    )

    assert report == {
        "activation": "not_applied",
        "covers_full_suite": False,
        "full_suite_root": "tests",
        "mode": "shadow",
        "selected": ["tests/unit/domain/test_sample.py"],
        "selected_count": 1,
    }


def test_shadow_compare_routes_billing_pr_non_code_changes() -> None:
    """Billing documentation and its manifest have explicit test routes."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            "CHANGELOG.md",
            "docs/02-architecture/finances-github-billing.md",
            "reports/engineering/ci/acceptance_f1_report.md",
            "reports/engineering/finances/billing_manifest.json",
        ],
        repo_root=repo_root,
    )

    assert "tests/architecture/test_docs_version_sync.py" in report["selected"]
    assert "tests/architecture/test_documentation_sync.py" in report["selected"]
    assert "tests/unit/scripts/test_github_billing.py" in report["selected"]


def test_shadow_compare_rejects_mixed_diff_with_unmapped_path(
    tmp_path: Path,
) -> None:
    """One unmapped path fails the report even when another path selects tests."""
    unit_domain = tmp_path / "tests" / "unit" / "domain"
    unit_domain.mkdir(parents=True)
    (unit_domain / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unmapped paths: docs/readme.md"):
        build_shadow_compare(
            ["tests/unit/domain/test_sample.py", "docs/readme.md"],
            repo_root=tmp_path,
        )


def test_shadow_compare_marks_full_suite_for_empty_diff(tmp_path: Path) -> None:
    """An empty diff is recorded as the full suite and still stays observational."""
    (tmp_path / "tests").mkdir()

    report = build_shadow_compare([], repo_root=tmp_path)

    assert report["activation"] == "not_applied"
    assert report["covers_full_suite"] is True
    assert report["selected"] == ["tests"]


def test_shadow_compare_cli_fails_closed_on_unmapped_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unmapped path must not produce a successful shadow report."""
    repo_root = Path(__file__).resolve().parents[5]
    assert (
        lane_main(
            [
                "shadow-compare",
                "--repo-root",
                str(repo_root),
                "--changed-file",
                "docs/readme.md",
            ]
        )
        == 1
    )
    assert "unmapped paths: docs/readme.md" in capsys.readouterr().err


def test_shadow_compare_cli_writes_canonical_json(tmp_path: Path) -> None:
    """The report file is canonical JSON and replaces the path atomically."""
    (tmp_path / "tests").mkdir()
    output = tmp_path / "reports" / "impact-shadow-compare.json"

    assert (
        lane_main(
            [
                "shadow-compare",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                " ",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = output.read_text(encoding="utf-8")
    assert payload.endswith("\n")
    assert json.loads(payload)["activation"] == "not_applied"
    assert list(json.loads(payload)) == [
        "activation",
        "covers_full_suite",
        "full_suite_root",
        "mode",
        "selected",
        "selected_count",
    ]
    assert not output.with_suffix(".json.tmp").exists()


def test_required_tests_gate_requires_shadow_step() -> None:
    """A required tests gate fails closed when the shadow step did not succeed."""
    failures = assert_step_outcomes(
        {"tests": {"decision": "required", "reason": "path_match"}},
        {"affected-pytest": "success", "impact-shadow-compare": "skipped"},
        owner="class-lane",
    )

    assert failures == ["tests:impact-shadow-compare=skipped"]


def test_unmapped_path_still_has_no_pytest_target(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A real unmapped path stays fail-closed and does not expand to every test."""
    repo_root = Path(__file__).resolve().parents[5]
    assert (
        lane_main(
            [
                "affected-tests",
                "--repo-root",
                str(repo_root),
                "--changed-file",
                "docs/readme.md",
            ]
        )
        == 1
    )
    assert "tests gate has no affected pytest target" in capsys.readouterr().err


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

    # The selected parent suite already executes test_sample.py exactly once.
    assert targets == ["tests/unit/domain"]


def test_affected_targets_map_integration_vcr_policy() -> None:
    """VCR policy edits select the inventory architecture test."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        ["configs/quality/integration_vcr_policy.yaml"],
        repo_root=repo_root,
    ) == ["tests/architecture/test_integration_vcr_policy.py"]


def test_affected_targets_map_telemetry_baseline(tmp_path: Path) -> None:
    """Telemetry edits select both baseline guards and leave other configs unmapped."""
    governance = tmp_path / "tests/architecture/test_test_telemetry_governance.py"
    governance.parent.mkdir(parents=True)
    governance.write_text(
        "def test_identity() -> None:\n    assert True\n", encoding="utf-8"
    )
    (governance.parent / "test_test_telemetry_baseline.py").write_text(
        "def test_baseline() -> None:\n    assert True\n", encoding="utf-8"
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

    assert targets == [
        "tests/architecture/test_test_telemetry_baseline.py",
        "tests/architecture/test_test_telemetry_governance.py",
    ]
    assert untouched == []


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


def test_affected_targets_map_makefile_benchmark_contract() -> None:
    """Makefile edits select the benchmark-target contract, not an empty lane."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(["Makefile"], repo_root=repo_root) == [
        "tests/unit/repo_backed/scripts/engineering/ci/test_makefile_benchmark_target.py",
    ]


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


def test_mcp_check_source_routes_both_mandatory_contract_suites(tmp_path: Path) -> None:
    from scripts.engineering.ci.pr_lane_results import (
        affected_pytest_targets,
        NPM_RUNTIME_TEST,
    )

    mcp_target = "tests/unit/repo_backed/scripts/ai/mcp/test_mcp_wrapper_contracts.py"
    for name in (NPM_RUNTIME_TEST, mcp_target):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    assert affected_pytest_targets(["scripts/ai/mcp/check.sh"], repo_root=tmp_path) == [
        NPM_RUNTIME_TEST,
        mcp_target,
    ]
    (tmp_path / mcp_target).unlink()
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets(["scripts/ai/mcp/check.sh"], repo_root=tmp_path)


def test_complete_suite_removes_nested_duplicates_after_required_validation(
    tmp_path: Path,
) -> None:
    from scripts.engineering.ci.pr_lane_results import affected_pytest_targets

    rag = "tests/unit/memory/test_rag_indexing.py"
    path = tmp_path / rag
    path.parent.mkdir(parents=True)
    path.touch()
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    changed = ["uv.lock", "src/memory/rag/chunking.py", rag]
    assert affected_pytest_targets(
        changed, repo_root=tmp_path, changed_python_dependencies={"pytest"}
    ) == ["tests"]
    path.unlink()
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets(
            changed, repo_root=tmp_path, changed_python_dependencies={"pytest"}
        )


def test_router_executes_lane_results_as_importable_module(capsys):
    """Verify router executes lane results as importable module."""
    from scripts.engineering.ci.__main__ import main

    assert main(["pr-lane-results", "--help"]) == 0
    assert "affected-tests" in capsys.readouterr().out


def test_benchmark_and_governance_artifacts_have_impact_routes() -> None:
    """Durable evidence and coupled snapshots select their governing tests."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            ".gitignore",
            "Dockerfile.bioetl",
            "docs/reports/generated/documentation-cleanup-inventory.json",
            "docs/reports/generated/documentation-cleanup-inventory.md",
            "reports/performance/benchmark-summary.json",
            (
                "reports/performance/evidence/deadbeef/raw/"
                "benchmark-validation-manifest.json"
            ),
            "reports/quality/flaky-test-burndown-review.json",
            "reports/quality/test-governance-current.json",
        ],
        repo_root=repo_root,
    )

    assert report["activation"] == "not_applied"
    assert report["covers_full_suite"] is False
    selected = set(report["selected"])
    assert selected == {
        "tests/architecture/test_documentation_cleanup_inventory.py",
        "tests/architecture/test_docker_runtime_contracts.py",
        "tests/architecture/test_gitignore_secret_and_agents_policy.py",
        "tests/architecture/test_tech_debt_issues_5514_5515_governance.py",
        "tests/architecture/test_test_governance_audit.py",
        "tests/unit/repo_backed/scripts/qa/test_validate_benchmark_evidence_repo.py",
    }


def test_base_checkout_aggregation_uses_existing_module_entrypoint():
    """Verify base checkout aggregation uses existing module entrypoint."""
    import yaml

    root = Path(__file__).resolve().parents[5]
    workflow = yaml.safe_load(
        (root / ".github/workflows/pr-required.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["pr-gate-complete"]["steps"]
    build = next(
        step["run"] for step in steps if "pr_lane_results build" in step.get("run", "")
    )
    assert "python -m scripts.engineering.ci.pr_lane_results build" in build


def test_record_steps_uses_bounded_outcomes_instead_of_all_step_outputs() -> None:
    """Keep large action outputs out of the recorder process environment."""
    import re
    import yaml

    root = Path(__file__).resolve().parents[5]
    workflow_text = (root / ".github/workflows/pr-required.yml").read_text(
        encoding="utf-8"
    )
    assert "toJson(steps)" not in workflow_text

    workflow = yaml.safe_load(workflow_text)
    for job_id, owner in (
        ("fast-governance", "fast-governance"),
        ("class-lane", "class-lane"),
    ):
        record = next(
            step
            for step in workflow["jobs"][job_id]["steps"]
            if step.get("name") == "Record required step outcomes"
        )
        serialized = set(re.findall(r"steps\.([a-z0-9-]+)\.outcome", record["run"]))
        required = {
            step_id for step_ids in OWNER_STEPS[owner].values() for step_id in step_ids
        }
        assert serialized == required


def test_assert_steps_malformed_outcomes() -> None:
    """Simulate a malformed outcome payload that includes strange formatting."""
    failures = assert_step_outcomes(
        {"type-checking": {"decision": "required", "reason": "path_match"}},
        {
            "mypy": "",  # Missing outcome
            "newtype-protocol": "success",
            "any-usage": "success",
        },
        owner="class-lane",
    )

    # Empty string outcome defaults to 'missing' string representation in assert_step_outcomes
    assert failures == ["type-checking:mypy=missing"]


def test_generated_artifact_sibling_uses_canonical_test_registry(
    tmp_path: Path,
) -> None:
    """Route a generated sibling through its registered artifact test."""
    test_path = "tests/architecture/test_generated_report.py"
    target = tmp_path / test_path
    target.parent.mkdir(parents=True)
    target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{test_path}::test_report",
                        "artifacts": ["reports/quality/report.json"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (registry.parent / "generated_artifact_routing.yaml").write_text(
        "routes:\n"
        "  - id: report\n"
        "    outputs:\n"
        "      - reports/quality/report.json\n"
        "      - reports/quality/report.md\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["reports/quality/report.md"],
        repo_root=tmp_path,
    )

    assert report["selected"] == [test_path]
