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

import yaml


SUCCESS = "success"
FAILURE = "failure"
SKIPPED = "skipped"
REQUIRED = "required"
NOT_APPLICABLE = "not_applicable"
TESTS_PREFIX = "tests/"
TEST_FILE_GLOB = "test_*.py"

from scripts.engineering.dev.run_tests import TESTS_ROOT as PYTEST_ALL_ROOT

NPM_RUNTIME_TEST = "tests/unit/repo_backed/scripts/ai/test_npm_runtime_contract.py"

TELEMETRY_BASELINE_TESTS: tuple[str, ...] = (
    "tests/architecture/test_test_telemetry_baseline.py",
    "tests/architecture/test_test_telemetry_governance.py",
)

AFFECTED_TESTS_BY_PATH: dict[str, tuple[str, ...]] = {
    ".coderabbit.yaml": ("tests/architecture/test_coderabbit_config.py",),
    "Makefile": (
        "tests/unit/repo_backed/scripts/engineering/ci/test_makefile_benchmark_target.py",
    ),
    "tests/fixtures/contracts/coderabbit-schema.v2.json": (
        "tests/architecture/test_coderabbit_config.py",
    ),
    "package.json": (
        "tests/architecture/test_observability_dashboard_tooling.py",
        NPM_RUNTIME_TEST,
    ),
    "package-lock.json": (
        "tests/architecture/test_observability_dashboard_tooling.py",
        NPM_RUNTIME_TEST,
    ),
    "scripts/ai/npm_runtime_contract.cjs": (NPM_RUNTIME_TEST,),
    "scripts/ai/mcp/mcp_filesystem_wrapper.sh": (NPM_RUNTIME_TEST,),
    "scripts/ai/mcp/mcp_filesystem_wrapper.ps1": (NPM_RUNTIME_TEST,),
    "scripts/ai/mcp/check.sh": (
        NPM_RUNTIME_TEST,
        "tests/unit/repo_backed/scripts/ai/mcp/test_mcp_wrapper_contracts.py",
    ),
    ".github/workflows/pr-required.yml": (
        "tests/architecture/test_github_actions_runtime_policy.py",
    ),
    "configs/quality/reusable_action_pins.yaml": (
        "tests/architecture/test_github_actions_runtime_policy.py",
    ),
    "scripts/engineering/repo/check_github_actions_runtime_policy.py": (
        "tests/architecture/test_github_actions_runtime_policy.py",
    ),
    ".circleci/config.yml": ("tests/architecture/test_circleci_migration_contract.py",),
    "src/memory/rag/chunking.py": ("tests/unit/memory/test_rag_indexing.py",),
    "scripts/engineering/ci/publish_docker_image.sh": (
        "tests/unit/scripts/ci/test_docker_publication_guards.py",
    ),
    "scripts/engineering/ci/pr_lane_results.py": (
        "tests/unit/scripts/engineering/ci/test_pr_lane_results.py",
    ),
    "configs/quality/integration_vcr_policy.yaml": (
        "tests/architecture/test_integration_vcr_policy.py",
    ),
    "configs/quality/test_telemetry_baseline.yaml": TELEMETRY_BASELINE_TESTS,
    "configs/quality/scripts_inventory_manifest.json": (
        "tests/architecture/test_scripts_inventory_manifest.py",
    ),
    "docs/05-engineering/test-telemetry-baseline.md": TELEMETRY_BASELINE_TESTS,
}

# Directory-level edges for generated artifacts and diagrams where an exact
# file mapping would need hundreds of entries. Each prefix still maps to real
# governing tests; fail-closed semantics are unchanged for unmapped paths.
AFFECTED_TESTS_BY_PREFIX: dict[str, tuple[str, ...]] = {
    "reports/test-telemetry/": TELEMETRY_BASELINE_TESTS,
    "scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.": (
        NPM_RUNTIME_TEST,
    ),
    "scripts/ops/observability/grafana/capture_grafana_screenshots_docker.sh": (
        NPM_RUNTIME_TEST,
    ),
    "docs/02-architecture/diagrams/": (
        "tests/architecture/test_diagram_corpus_regression_guards.py",
        "tests/architecture/test_diagram_drift_and_embed_guards.py",
        "tests/architecture/test_diagram_lint_policy_rules.py",
    ),
    "src/memory/episodic/": (
        "tests/architecture/test_ai_session_memory_placement.py",
        "tests/architecture/test_pretest_guardrails_memory_phase.py",
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
            "prose-consistency",
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
    """Map a job conclusion to success, skipped, or failure."""
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


def affected_pytest_targets(
    changed_files: list[str],
    *,
    repo_root: Path,
    changed_python_dependencies: set[str] | None = None,
    require_all_python_tests: bool = False,
) -> list[str]:
    """Map a diff to tests; validate all declared targets before selection.

    An empty diff has no path mapping. Classification still requires the tests
    gate (``fail_closed_empty_diff``), so the full Python suite is the target.
    """
    paths = [path for raw in changed_files if (path := raw.strip().replace("\\", "/"))]
    if not paths:
        return [_python_suite_root(repo_root)]
    mapped = {path: _mapped_targets(path) for path in paths}
    _require_targets(
        [target for values in mapped.values() for target in values], repo_root
    )
    targets: list[str] = []
    if {"pyproject.toml", "uv.lock"} & set(paths):
        if changed_python_dependencies is None:
            raise ValueError(
                "Python dependency route requires verified dependency diff"
            )
        if require_all_python_tests or _global_dependency_lane(
            repo_root, changed_python_dependencies
        ):
            targets.append(_python_suite_root(repo_root))
        else:
            targets.extend(_dependency_targets(repo_root, changed_python_dependencies))
    for path in paths:
        targets.extend(mapped[path])
        targets.extend(_path_targets(path, repo_root))
    return _deduplicate_targets(targets, repo_root)


def _python_suite_root(repo_root: Path) -> str:
    """Return the full Python suite, or fail closed when that tree is absent."""
    if not (repo_root / PYTEST_ALL_ROOT).is_dir():
        raise ValueError("Missing mandatory mapped test targets: " + PYTEST_ALL_ROOT)
    return PYTEST_ALL_ROOT.rstrip("/")


def _deduplicate_targets(targets: list[str], root: Path) -> list[str]:
    """Drop a test path when a selected parent directory already covers it."""
    unique = list(dict.fromkeys(targets))
    suites = {target.rstrip("/") for target in unique if (root / target).is_dir()}
    return [
        target
        for target in unique
        if not any(parent.as_posix() in suites for parent in Path(target).parents)
    ]


def _global_dependency_lane(root: Path, dependencies: set[str]) -> bool:
    """Return whether a dependency diff selects the full Python test lane."""
    from scripts.engineering.ci._python_dependency_changes import (
        pytest_framework_affected,
        repository_cli_affected,
    )

    return pytest_framework_affected(root, dependencies) or repository_cli_affected(
        root, dependencies
    )


def _mapped_targets(path: str) -> list[str]:
    """Return catalog-mapped tests for one changed path."""
    targets = list(AFFECTED_TESTS_BY_PATH.get(path, ()))
    for prefix, values in AFFECTED_TESTS_BY_PREFIX.items():
        if path.startswith(prefix):
            targets.extend(values)
    return targets


def _require_targets(targets: list[str], root: Path) -> None:
    """Reject mapped targets that are not files in the repository."""
    missing = sorted({target for target in targets if not (root / target).is_file()})
    if missing:
        raise ValueError("Missing mandatory mapped test targets: " + ", ".join(missing))


def _path_targets(path: str, root: Path) -> list[str]:
    """Return the test path or unit directory implied by one changed path."""
    if path.startswith(TESTS_PREFIX) and path.endswith(".py"):
        return [path] if (root / path).is_file() else []
    if path.startswith("src/bioetl/") and path.endswith(".py"):
        first = path.removeprefix("src/bioetl/").split("/", 1)[0]
        candidate = root / "tests" / "unit" / first
        return [candidate.relative_to(root).as_posix()] if candidate.is_dir() else []
    if path.startswith("scripts/") and path.endswith(".py"):
        return _script_targets(path, root)
    return []


def _script_targets(path: str, root: Path) -> list[str]:
    """Return direct or importing tests for one scripts path."""
    relative = Path(path.removeprefix("scripts/"))
    test_roots = (root / "tests/unit/scripts", root / "tests/unit/repo_backed/scripts")
    direct_dirs = [test_root / relative.parent for test_root in test_roots]
    if relative.parts[0] == "engineering":
        direct_dirs.append(test_roots[0] / Path(*relative.parts[1:-1]))
    direct_name = f"test_{relative.name.lstrip('_')}"
    direct = {
        candidate
        for directory in direct_dirs
        if (candidate := directory / direct_name).is_file()
    }
    module = ".".join(("scripts", *relative.with_suffix("").parts))
    selected = sorted(direct | _importing_script_tests(test_roots, module))
    if selected:
        return [test.relative_to(root).as_posix() for test in selected]
    return [
        test_root.relative_to(root).as_posix()
        for test_root in test_roots
        if test_root.is_dir()
    ]


def _importing_script_tests(roots: tuple[Path, Path], module: str) -> set[Path]:
    """Return test files that statically import the script module."""
    return {
        test
        for root in roots
        if root.is_dir()
        for test in root.rglob(TEST_FILE_GLOB)
        if _imports_module(test, module)
    }


def _dependency_targets(repo_root: Path, dependencies: set[str]) -> list[str]:
    """Reuse source routing and canonical owners for actual dependency consumers."""
    from scripts.engineering.ci._python_dependency_changes import dependency_consumers

    inventory = repo_root / "configs/quality/source_test_owner_inventory.yaml"
    owners: dict[str, list[str]] = {}
    if inventory.is_file():
        document = yaml.safe_load(inventory.read_text(encoding="utf-8"))
        owners = {row["source"]: row["owner_tests"] for row in document["modules"]}
    targets: list[str] = []
    for consumer in dependency_consumers(repo_root, dependencies):
        selected = _consumer_targets(consumer, repo_root, owners)
        if not selected:
            raise ValueError(
                f"Unconfirmed Python dependency consumer route: {consumer}"
            )
        targets.extend(selected)
    return targets


def _consumer_targets(
    consumer: str, root: Path, owners: dict[str, list[str]]
) -> list[str]:
    """Return the confirmed test route for one dependency consumer."""
    if consumer in owners:
        selected = owners[consumer]
        _require_targets(selected, root)
        return selected
    if consumer.startswith(TESTS_PREFIX):
        if Path(consumer).name == "conftest.py":
            return [Path(consumer).parent.as_posix()]
        if not Path(consumer).name.startswith("test_"):
            return _helper_suite(consumer, root)
    if consumer.startswith("src/memory/"):
        return ["tests/unit/memory"] if (root / "tests/unit/memory").is_dir() else []
    return affected_pytest_targets([consumer], repo_root=root)


def _helper_suite(consumer: str, root: Path) -> list[str]:
    """Shared helpers require their complete owning suite, never a helper file alone."""
    suite = Path(consumer).parent
    while suite.as_posix().startswith(TESTS_PREFIX) and not any(
        (root / suite).rglob(TEST_FILE_GLOB)
    ):
        suite = suite.parent
    if not (root / suite).is_dir() or not any((root / suite).rglob(TEST_FILE_GLOB)):
        raise ValueError(
            f"Unconfirmed Python dependency test-helper owner route: {consumer}"
        )
    return [suite.as_posix()]


def _imports_module(test_path: Path, module_name: str) -> bool:
    """Return whether a test statically imports the selected script module."""
    tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))
    parent_module, _, leaf_name = module_name.rpartition(".")
    return any(
        _matches_module_import(
            node,
            module_name=module_name,
            parent_module=parent_module,
            leaf_name=leaf_name,
        )
        for node in ast.walk(tree)
    )


def _matches_module_import(
    node: ast.AST,
    *,
    module_name: str,
    parent_module: str,
    leaf_name: str,
) -> bool:
    """Return whether one AST node imports the selected module."""
    if isinstance(node, ast.Import):
        return any(
            alias.name == module_name or alias.name.startswith(f"{module_name}.")
            for alias in node.names
        )
    return isinstance(node, ast.ImportFrom) and (
        node.module == module_name
        or (
            node.module == parent_module
            and any(alias.name == leaf_name for alias in node.names)
        )
    )


def _load_json_object(raw: str, *, label: str) -> dict[str, Any]:
    """Parse a JSON object and reject every other JSON type."""
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return cast(dict[str, Any], payload)


def _decision_map(matrix: dict[str, Any]) -> dict[str, Any]:
    """Return the decisions mapping from a classifier matrix."""
    decisions = matrix.get("decisions", matrix)
    if not isinstance(decisions, dict):
        raise ValueError("decision matrix decisions must be a mapping")
    return cast(dict[str, Any], decisions)


def _env_or_text(value: str, *, from_env: bool) -> str:
    """Return the value itself or the named environment variable."""
    if from_env:
        if value not in os.environ:
            raise ValueError(f"environment variable {value} is missing")
        return os.environ[value]
    return value


def _build_command(args: argparse.Namespace) -> int:
    """Write the gate result map for one decision matrix."""
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
    """Fail when a required owner step did not succeed."""
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
    """Print pytest targets for the changed files."""
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
    try:
        dependencies = None
        all_tests = False
        if {"pyproject.toml", "uv.lock"} & set(changed):
            from scripts.engineering.ci._python_dependency_changes import (
                changed_dependencies,
                pytest_configuration_changed,
                removed_dependencies,
            )

            all_tests = pytest_configuration_changed(
                args.repo_root, args.base_sha, args.head_sha
            )
            dependencies = changed_dependencies(
                args.repo_root,
                args.base_sha,
                args.head_sha,
                allow_configuration=all_tests,
            )
            all_tests = all_tests or removed_dependencies(
                args.repo_root, args.base_sha, args.head_sha
            )
        targets = affected_pytest_targets(
            changed,
            repo_root=args.repo_root,
            changed_python_dependencies=dependencies,
            require_all_python_tests=all_tests,
        )
    except (ValueError, OSError) as error:
        print(f"tests gate selection failed: {error}", file=sys.stderr)
        return 1
    if not targets:
        print("tests gate has no affected pytest target", file=sys.stderr)
        return 1
    print("\n".join(targets))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the lane-results command parser."""
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
    """Parse one owner=result argument into a pair."""
    job_name, separator, result = raw.partition("=")
    if not separator or not job_name or not result:
        raise argparse.ArgumentTypeError("expected name=result")
    return job_name, result


def main(argv: list[str] | None = None) -> int:
    """Run the selected lane-results command."""
    args = build_parser().parse_args(argv)
    return cast(int, args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
