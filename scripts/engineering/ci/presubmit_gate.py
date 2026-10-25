"""Local presubmit gate for Ruff, strict mypy, affected tests, and fast architecture.

The command resolves refs to exact SHAs, then reuses the canonical classify and
affected-test seams. An unknown path or an empty test selection fails closed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.engineering.ci.pr_gate import (
    CatalogError,
    classify_changes,
    collect_changed_files,
    load_catalog,
)
from scripts.engineering.common.repo_paths import ensure_safe_cli_argv
from scripts.engineering.repo.check_no_partial_tree import resolve_revision

_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_RUFF_TREES = ("src", "tests", "scripts")
_MYPY_TREES = ("src/bioetl", "src/memory", "scripts/engineering/quality")
_FAST_ARCHITECTURE_MARK = "not slow and not benchmark and not memory"
_AFFECTED_REPORT = "reports/quality/affected-test-partition.json"
_SELECT_TIMEOUT_SECONDS = 300


def build_parser() -> argparse.ArgumentParser:
    """Build the presubmit CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base ref (e.g. origin/main)")
    parser.add_argument("--head", required=True, help="Head ref (e.g. HEAD)")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("configs/quality/github_required_checks.yaml"),
        help="Path to the required-check catalog",
    )
    return parser


def resolve_ref(ref: str, *, repo: Path | None = None) -> str:
    """Resolve a git ref to a commit SHA after rejecting flag injection.

    ``resolve_revision`` stops the process with ``SystemExit`` when the token
    is not a safe revision. That termination is intentional and is not wrapped.
    """
    resolved = resolve_revision(repo or Path.cwd(), ref)
    matched = _SHA_RE.fullmatch(resolved)
    if matched is None:
        raise ValueError(f"git ref did not resolve to a commit SHA: {ref!r}")
    return matched.group(0)


def _run(command: list[str]) -> int:
    """Run a static argv command and return its exit code."""
    return subprocess.run(command, check=False).returncode


def _capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a sanitized argv command and capture text output.

    A stuck affected-test selector must fail the gate instead of blocking
    presubmit. The command list is already passed through
    ``ensure_safe_cli_argv``.
    """
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=_SELECT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            command,
            124,
            stdout="",
            stderr=f"affected-test selection timed out: {exc}",
        )


def run_ruff() -> bool:
    """Run ruff check and format on the same trees as CI."""
    print("Running ruff check src tests scripts...", flush=True)
    check_command = [
        "uv",
        "run",
        "--frozen",
        "--no-build",
        "ruff",
        "check",
        *_RUFF_TREES,
    ]
    if _run(check_command) != 0:
        print("::error::Ruff check failed.", file=sys.stderr)
        return False
    print("Running ruff format --check src tests scripts...", flush=True)
    format_command = [
        "uv",
        "run",
        "--frozen",
        "--no-build",
        "ruff",
        "format",
        "--check",
        *_RUFF_TREES,
    ]
    if _run(format_command) != 0:
        print("::error::Ruff format failed.", file=sys.stderr)
        return False
    return True


def run_mypy() -> bool:
    """Run strict incremental mypy on src/bioetl and src/memory."""
    print("Running strict mypy gate on " + " + ".join(_MYPY_TREES) + "...", flush=True)
    command = [
        "uv",
        "run",
        "--frozen",
        "--no-build",
        "mypy",
        "--config-file",
        "pyproject.toml",
        "--strict",
        "--incremental",
        *_MYPY_TREES,
    ]
    if _run(command) != 0:
        print("::error::Mypy strict gate failed.", file=sys.stderr)
        return False
    return True


def affected_tests_command(
    base_sha: str,
    head_sha: str,
    changed: list[str],
) -> list[str]:
    """Build the canonical affected-test selector command for one diff."""
    command = [
        sys.executable,
        "-m",
        "scripts.engineering.ci",
        "pr-lane-results",
        "affected-tests",
        "--repo-root",
        ".",
        "--base-sha",
        base_sha,
        "--head-sha",
        head_sha,
    ]
    for path in changed:
        if path.startswith("-"):
            raise ValueError(f"unsafe changed path: {path!r}")
        command.extend(["--changed-file", path])
    return ensure_safe_cli_argv(command)


def _pytest_command(targets: list[str]) -> list[str]:
    """Run selected tests through the CI generated-artifact scheduler."""
    return ensure_safe_cli_argv(
        [
            "uv",
            "run",
            "--frozen",
            "--no-build",
            "python",
            "-m",
            "scripts.engineering.ci.generated_artifact_checks",
            "ci",
            "--report",
            _AFFECTED_REPORT,
            "--",
            *targets,
            "-q",
            "--tb=line",
        ]
    )


def run_affected_tests(base_sha: str, head_sha: str, changed: list[str]) -> bool:
    """Select affected tests with the canonical CLI and fail on an empty set."""
    select = _capture(affected_tests_command(base_sha, head_sha, changed))
    if select.returncode != 0:
        detail = (select.stderr or select.stdout).strip()
        print(f"::error::affected-test selection failed: {detail}", file=sys.stderr)
        return False
    targets = [line.strip() for line in select.stdout.splitlines() if line.strip()]
    if not targets:
        print("::error::tests gate has no affected pytest target", file=sys.stderr)
        return False
    print("Running affected pytest targets...", flush=True)
    if _run(_pytest_command(targets)) != 0:
        print("::error::Affected pytest failed.", file=sys.stderr)
        return False
    return True


def fast_architecture_command() -> list[str]:
    """Return the class-lane fast architecture pytest command."""
    return [
        "uv",
        "run",
        "--frozen",
        "--no-build",
        "pytest",
        "tests/architecture",
        "-m",
        _FAST_ARCHITECTURE_MARK,
        "-q",
        "--tb=line",
    ]


def run_fast_architecture() -> bool:
    """Run the fast architecture slice used by the class lane."""
    print("Running fast architecture checks...", flush=True)
    if _run(fast_architecture_command()) != 0:
        print("::error::Fast architecture checks failed.", file=sys.stderr)
        return False
    return True


def _python_scope(changed: list[str]) -> bool:
    """Return True when the diff contains Python sources."""
    return any(path.endswith((".py", ".pyi")) for path in changed)


def _required(matrix: dict[str, Any], gate_id: str) -> bool:
    """Return whether one classified gate is required."""
    decisions = matrix.get("decisions")
    if not isinstance(decisions, dict):
        raise CatalogError("decision matrix decisions must be a mapping")
    decision = decisions.get(gate_id)
    if not isinstance(decision, dict):
        raise CatalogError(f"missing decision for {gate_id}")
    kind = decision.get("decision")
    if kind == "required":
        return True
    if kind == "not_applicable":
        return False
    raise CatalogError(f"{gate_id}: unknown decision={kind!r}")


def main(argv: list[str] | None = None) -> int:
    """Run the presubmit contract and return a process exit code."""
    args = build_parser().parse_args(argv)
    try:
        base_sha = resolve_ref(args.base)
        head_sha = resolve_ref(args.head)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    print(f"Presubmit check: base={base_sha}, head={head_sha}", flush=True)
    try:
        changed = collect_changed_files(
            event_name="pull_request",
            base_sha=base_sha,
            before_sha="",
            head_sha=head_sha,
        )
    except (subprocess.CalledProcessError, CatalogError, OSError) as exc:
        print(f"::error::Failed to compute diff: {exc}", file=sys.stderr)
        return 1

    success = run_ruff()
    if _python_scope(changed) and not run_mypy():
        success = False
    try:
        catalog = load_catalog(args.catalog)
        matrix = classify_changes(catalog, changed, head_sha=head_sha)
        if _required(matrix, "tests") and not run_affected_tests(
            base_sha, head_sha, changed
        ):
            success = False
        if _required(matrix, "lint-arch") and not run_fast_architecture():
            success = False
    except (CatalogError, OSError, ValueError) as exc:
        print(f"::error::Classification failed: {exc}", file=sys.stderr)
        return 1
    if not success:
        print("::error::Presubmit checks failed.", file=sys.stderr)
        return 1
    print("Presubmit checks passed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
