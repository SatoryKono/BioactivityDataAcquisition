"""Local presubmit gate for Ruff and strict mypy before push."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.engineering.ci.pr_gate import (
    load_catalog,
    classify_changes,
)


def build_parser() -> argparse.ArgumentParser:
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


import re


def resolve_ref(ref: str) -> str:
    """Resolve a git ref to a complete SHA-1 hash."""
    if not re.match(r"^[a-zA-Z0-9_./-]+$", ref):
        print(f"::error::Invalid characters in ref {ref!r}", file=sys.stderr)
        sys.exit(1)
    try:
        process = subprocess.run(
            ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
            check=True,
            capture_output=True,
            text=True,
        )
        return process.stdout.strip()
    except subprocess.CalledProcessError as err:
        print(
            f"::error::Failed to resolve ref {ref!r}: {err.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(1)


def collect_changed_files(base_sha: str, head_sha: str) -> list[str]:
    """Collect the exact list of changed files between base and head."""
    try:
        process = subprocess.run(
            ["git", "diff", "--name-only", "-z", f"{base_sha}...{head_sha}"],
            check=True,
            capture_output=True,
        )
        if not process.stdout:
            return []

        tokens = process.stdout.split(b"\0")
        if tokens and tokens[-1] == b"":
            tokens.pop()
        import os

        return [os.fsdecode(t) for t in tokens]
    except subprocess.CalledProcessError as err:
        print(
            f"::error::Failed to compute diff between {base_sha} and {head_sha}",
            file=sys.stderr,
        )
        sys.exit(1)


def run_ruff() -> bool:
    """Run ruff check and ruff format on src tests scripts."""
    print("Running ruff check src tests scripts...", flush=True)
    check_run = subprocess.run(
        ["uv", "run", "ruff", "check", "src", "tests", "scripts"],
        capture_output=False,
    )
    if check_run.returncode != 0:
        print("::error::Ruff check failed.", file=sys.stderr)
        return False

    print("Running ruff format --check src tests scripts...", flush=True)
    format_run = subprocess.run(
        ["uv", "run", "ruff", "format", "--check", "src", "tests", "scripts"],
        capture_output=False,
    )
    if format_run.returncode != 0:
        print("::error::Ruff format failed.", file=sys.stderr)
        return False

    return True


def run_mypy() -> bool:
    """Run strict incremental mypy on src/bioetl and src/memory."""
    print("Running strict mypy gate on src/bioetl + src/memory...", flush=True)
    mypy_run = subprocess.run(
        [
            "uv",
            "run",
            "mypy",
            "--config-file",
            "pyproject.toml",
            "--strict",
            "--incremental",
            "src/bioetl",
            "src/memory",
        ],
        capture_output=False,
    )
    if mypy_run.returncode != 0:
        print("::error::Mypy strict gate failed.", file=sys.stderr)
        return False
    return True


def evaluate_fast_architecture(matrix: dict[str, Any]) -> bool:
    """Evaluate fast architecture checks if required."""
    print(
        "Classifying fast architecture checks based on decision matrix...", flush=True
    )
    success = True

    # Check if fast architecture checks are required based on decision matrix
    if matrix.get("lint-arch") == "required":
        print("Running audit root cleanliness...", flush=True)
        repo_run = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "scripts.engineering.repo",
                "check-cleanliness",
            ],
            capture_output=False,
        )
        if repo_run.returncode != 0:
            print("::error::Audit root cleanliness failed.", file=sys.stderr)
            success = False

    # affected tests validation
    if matrix.get("tests") == "required":
        # Just simulating affected tests for now or checking we reached here
        print("Tests are required based on changed files.", flush=True)
    return success


def is_python_scope(changed_files: list[str]) -> bool:
    """Return True if any python file was modified."""
    return any(f.endswith(".py") or f.endswith(".pyi") for f in changed_files)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # 1. Resolve exact SHAs
    base_sha = resolve_ref(args.base)
    head_sha = resolve_ref(args.head)

    print(f"Presubmit check: base={base_sha}, head={head_sha}", flush=True)

    # 2. Collect diff
    changed_files = collect_changed_files(base_sha, head_sha)

    # If no files changed, exit early?
    if not changed_files:
        print("No files changed. Presubmit successful.", flush=True)
        return 0

    python_scope = is_python_scope(changed_files)

    success = True

    # 3. Ruff check/format
    if not run_ruff():
        success = False

    # 4. Strict mypy
    if python_scope:
        if not run_mypy():
            success = False

    # 5. Classify & affected tests
    try:
        catalog = load_catalog(args.catalog)
        matrix = classify_changes(catalog, changed_files, head_sha=head_sha)

        if not evaluate_fast_architecture(matrix):
            success = False

    except Exception as err:
        print(f"::error::Classification failed: {err}", file=sys.stderr)
        success = False

    if not success:
        print("::error::Presubmit checks failed.", file=sys.stderr)
        sys.exit(1)

    print("Presubmit checks passed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
