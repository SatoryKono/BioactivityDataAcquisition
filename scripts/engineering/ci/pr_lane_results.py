"""Map coordinator job results onto the pr-gate catalog.

One class-lane job owns several gates. A failed required step fails that job,
and every required gate owned by the job stays red. A not-applicable gate never
inherits a sibling job result.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

SUCCESS = "success"
FAILURE = "failure"
SKIPPED = "skipped"
REQUIRED = "required"
NOT_APPLICABLE = "not_applicable"

AFFECTED_TESTS_BY_PATH: dict[str, tuple[str, ...]] = {
    ".circleci/config.yml": ("tests/architecture/test_circleci_migration_contract.py",),
    "scripts/engineering/ci/publish_docker_image.sh": (
        "tests/unit/scripts/ci/test_docker_publication_guards.py",
    ),
    "scripts/engineering/ci/pr_lane_results.py": (
        "tests/unit/scripts/engineering/ci/test_pr_lane_results.py",
    ),
}

FAST_GOVERNANCE = "fast-governance"
CLASS_LANE = "class-lane"

GATE_OWNERS: dict[str, str] = {
    "root-hygiene": FAST_GOVERNANCE,
    "compiled-artifacts": FAST_GOVERNANCE,
    "commit-governance": FAST_GOVERNANCE,
    "docs-governance": FAST_GOVERNANCE,
    "lint-arch": CLASS_LANE,
    "tests": CLASS_LANE,
    "type-checking": CLASS_LANE,
    "security": CLASS_LANE,
    "docker": CLASS_LANE,
    "generated-artifacts": CLASS_LANE,
    "duplication": CLASS_LANE,
}

OWNER_STEPS: dict[str, dict[str, tuple[str, ...]]] = {
    FAST_GOVERNANCE: {
        "root-hygiene": (
            "cleanliness",
            "cleanup-governance",
            "root-docs",
            "root-registry",
            "structure-audit",
            "hygiene-pytest",
        ),
        "compiled-artifacts": ("compiled-artifacts", "cleanliness"),
        "commit-governance": ("commitlint",),
        "docs-governance": (
            "docs-passports",
            "docs-links",
            "docs-verify",
            "mkdocs-nav",
        ),
    },
    CLASS_LANE: {
        "lint-arch": (
            "ruff",
            "ruff-format",
            "ruff-isort",
            "c901",
            "lint-imports",
            "arch-pytest",
        ),
        "tests": ("affected-pytest",),
        "type-checking": ("mypy", "newtype-protocol", "any-usage"),
        "security": (
            "detect-secrets",
            "pip-audit",
            "bandit",
            "gitleaks",
            "osv-gate",
        ),
        "docker": ("docker-compose", "docker-monitoring-compose", "docker-contracts"),
        "generated-artifacts": ("schema-artifacts", "schema-parity"),
        "duplication": (
            "duplication-exemptions",
            "constructor-args",
            "jscpd",
            "duplication-hotspots",
        ),
    },
}


def _normalize_job_result(raw: str) -> str:
    value = raw.strip().lower()
    if value == SUCCESS:
        return SUCCESS
    if value == SKIPPED:
        return SKIPPED
    return FAILURE


def build_results(
    decisions: dict[str, Any],
    job_results: dict[str, str],
    *,
    head_sha: str,
    gate_owners: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    """Return the result map ``evaluate_results`` expects."""
    owners = GATE_OWNERS if gate_owners is None else gate_owners
    results: dict[str, dict[str, str]] = {}
    for gate_id, raw_decision in decisions.items():
        if not isinstance(raw_decision, dict):
            raise ValueError(f"{gate_id}: decision must be a mapping")
        kind = raw_decision.get("decision")
        if kind == NOT_APPLICABLE:
            reason = raw_decision.get("reason")
            if not isinstance(reason, str) or not reason:
                raise ValueError(f"{gate_id}: N/A reason is missing")
            results[gate_id] = {
                "required": SKIPPED,
                "not_applicable": SUCCESS,
                "na_head_sha": head_sha,
                "na_reason": reason,
            }
            continue
        if kind != REQUIRED:
            raise ValueError(f"{gate_id}: unknown decision={kind!r}")
        owner = owners.get(gate_id)
        if owner is None:
            raise ValueError(f"{gate_id}: no coordinator owner")
        job_result = _normalize_job_result(job_results.get(owner, SKIPPED))
        results[gate_id] = {
            "required": job_result,
            "not_applicable": SKIPPED,
        }
    return results


def assert_step_outcomes(
    decisions: dict[str, Any],
    outcomes: dict[str, str],
    *,
    owner: str,
) -> list[str]:
    """Return failures when a required gate's step did not succeed."""
    steps_for_owner = OWNER_STEPS.get(owner)
    if steps_for_owner is None:
        raise ValueError(f"unknown owner {owner!r}")
    failures: list[str] = []
    for gate_id, step_names in steps_for_owner.items():
        raw_decision = decisions.get(gate_id)
        if not isinstance(raw_decision, dict):
            continue
        if raw_decision.get("decision") != REQUIRED:
            continue
        for step_name in step_names:
            outcome = str(outcomes.get(step_name, "")).strip().lower()
            if outcome != SUCCESS:
                failures.append(f"{gate_id}:{step_name}={outcome or 'missing'}")
    for key, raw_outcome in outcomes.items():
        outcome = str(raw_outcome).strip().lower()
        if outcome not in {FAILURE, "cancelled"}:
            continue
        token = f"{key}={outcome}"
        if any(token in failure for failure in failures):
            continue
        failures.append(f"step:{token}")
    return failures


def affected_pytest_targets(changed_files: list[str], *, repo_root: Path) -> list[str]:
    """Map a diff to existing unit tests. Empty means the caller must fail closed."""
    targets: list[str] = []
    for raw_path in changed_files:
        path = raw_path.strip().replace("\\", "/")
        if not path:
            continue
        for candidate_path in AFFECTED_TESTS_BY_PATH.get(path, ()):
            if (repo_root / candidate_path).is_file():
                targets.append(candidate_path)
        if path.startswith("tests/") and path.endswith(".py"):
            if (repo_root / path).is_file():
                targets.append(path)
            continue
        if path.startswith("src/bioetl/") and path.endswith(".py"):
            relative = path.removeprefix("src/bioetl/")
            first = relative.split("/", 1)[0]
            candidate = repo_root / "tests" / "unit" / first
            if candidate.is_dir():
                targets.append(candidate.relative_to(repo_root).as_posix())
            continue
        if path.startswith("scripts/") and path.endswith(".py"):
            relative = Path(path.removeprefix("scripts/"))
            scripts_test_roots = (
                repo_root / "tests" / "unit" / "scripts",
                repo_root / "tests" / "unit" / "repo_backed" / "scripts",
            )
            direct_test_name = f"test_{relative.name.lstrip('_')}"
            direct_test_dirs = [
                test_root / relative.parent for test_root in scripts_test_roots
            ]
            if relative.parts[0] == "engineering":
                direct_test_dirs.append(
                    scripts_test_roots[0] / Path(*relative.parts[1:-1])
                )
            direct_tests = sorted(
                candidate
                for test_dir in direct_test_dirs
                if (candidate := test_dir / direct_test_name).is_file()
            )
            module_name = ".".join(("scripts", *relative.with_suffix("").parts))
            importing_tests = sorted(
                test_path
                for test_root in scripts_test_roots
                if test_root.is_dir()
                for test_path in test_root.rglob("test_*.py")
                if _imports_module(test_path, module_name)
            )
            selected_tests = sorted({*direct_tests, *importing_tests})
            if selected_tests:
                targets.extend(
                    test_path.relative_to(repo_root).as_posix()
                    for test_path in selected_tests
                )
            else:
                targets.extend(
                    test_root.relative_to(repo_root).as_posix()
                    for test_root in scripts_test_roots
                    if test_root.is_dir()
                )
    ordered: list[str] = []
    seen: set[str] = set()
    for target in targets:
        if target not in seen:
            seen.add(target)
            ordered.append(target)
    return ordered


def _imports_module(test_path: Path, module_name: str) -> bool:
    """Return whether a test statically imports the selected script module."""
    tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))
    parent_module, _, leaf_name = module_name.rpartition(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name == module_name or alias.name.startswith(f"{module_name}.")
                for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == module_name or (
                node.module == parent_module
                and any(alias.name == leaf_name for alias in node.names)
            ):
                return True
    return False


def _load_json_object(raw: str, *, label: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return cast(dict[str, Any], payload)


def _decision_map(matrix: dict[str, Any]) -> dict[str, Any]:
    decisions = matrix.get("decisions", matrix)
    if not isinstance(decisions, dict):
        raise ValueError("decision matrix decisions must be a mapping")
    return cast(dict[str, Any], decisions)


def _env_or_text(value: str, *, from_env: bool) -> str:
    if from_env:
        if value not in os.environ:
            raise ValueError(f"environment variable {value} is missing")
        return os.environ[value]
    return value


def _build_command(args: argparse.Namespace) -> int:
    matrix = _load_json_object(
        _env_or_text(args.decision_matrix, from_env=args.decision_matrix_env),
        label="decision matrix",
    )
    job_results = dict(args.job_result or [])
    results = build_results(
        _decision_map(matrix),
        job_results,
        head_sha=args.head_sha,
    )
    rendered = json.dumps(results, sort_keys=True, separators=(",", ":"))
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def _assert_command(args: argparse.Namespace) -> int:
    matrix = _load_json_object(
        _env_or_text(args.decision_matrix, from_env=args.decision_matrix_env),
        label="decision matrix",
    )
    outcomes = _load_json_object(
        _env_or_text(args.outcomes, from_env=args.outcomes_env),
        label="step outcomes",
    )
    failures = assert_step_outcomes(
        _decision_map(matrix),
        {str(key): str(value) for key, value in outcomes.items()},
        owner=args.owner,
    )
    if failures:
        for failure in failures:
            print(f"::error::{failure}", file=sys.stderr)
        return 1
    print(f"{args.owner} required steps succeeded")
    return 0


def _affected_command(args: argparse.Namespace) -> int:
    if args.changed_file:
        changed = list(args.changed_file)
    else:
        completed = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                f"{args.base_sha}...{args.head_sha}",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=args.repo_root,
        )
        changed = [line for line in completed.stdout.splitlines() if line.strip()]
    targets = affected_pytest_targets(changed, repo_root=args.repo_root)
    if not targets:
        print("tests gate has no affected pytest target", file=sys.stderr)
        return 1
    print("\n".join(targets))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--decision-matrix", required=True)
    build.add_argument("--decision-matrix-env", action="store_true")
    build.add_argument("--head-sha", required=True)
    build.add_argument(
        "--job-result",
        action="append",
        type=_job_result_pair,
        default=[],
    )
    build.add_argument("--output", type=Path)
    build.set_defaults(handler=_build_command)

    assert_steps = subparsers.add_parser("assert-steps")
    assert_steps.add_argument("--decision-matrix", required=True)
    assert_steps.add_argument("--decision-matrix-env", action="store_true")
    assert_steps.add_argument("--outcomes", required=True)
    assert_steps.add_argument("--outcomes-env", action="store_true")
    assert_steps.add_argument("--owner", required=True, choices=sorted(OWNER_STEPS))
    assert_steps.set_defaults(handler=_assert_command)

    affected = subparsers.add_parser("affected-tests")
    affected.add_argument("--repo-root", type=Path, default=Path("."))
    affected.add_argument("--base-sha", default="")
    affected.add_argument("--head-sha", default="HEAD")
    affected.add_argument("--changed-file", action="append", default=[])
    affected.set_defaults(handler=_affected_command)
    return parser


def _job_result_pair(raw: str) -> tuple[str, str]:
    job_name, separator, result = raw.partition("=")
    if not separator or not job_name or not result:
        raise argparse.ArgumentTypeError("expected name=result")
    return job_name, result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return cast(int, args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
