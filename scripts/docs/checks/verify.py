#!/usr/bin/env python3
"""Run the canonical docs verification chain."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tempfile


_MISSING_DOCS_EXTRA = (
    "[docs-verify] ERROR: mkdocs is not installed. "
    "Install extra `docs`: `uv sync --extra docs` "
    r"(Windows: .\.venv-win\Scripts\python.exe -m uv sync --extra docs). "
    "A missing extra produces this error instead of a cryptic mkdocs traceback."
)


def _run_step(label: str, argv: list[str]) -> int:
    print(f"[docs-verify] {label}: {' '.join(argv)}", flush=True)
    result = subprocess.run(argv, check=False)
    return result.returncode


def _require_docs_extra() -> int:
    if importlib.util.find_spec("mkdocs") is not None:
        return 0
    print(_MISSING_DOCS_EXTRA, file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-links", action="store_true", help="Skip link/spec/config checks"
    )
    parser.add_argument("--skip-drift", action="store_true", help="Skip drift checks")
    parser.add_argument(
        "--skip-docstrings",
        action="store_true",
        help="Skip docstring inventory checks",
    )
    parser.add_argument(
        "--skip-cleanup-inventory",
        action="store_true",
        help="Skip documentation cleanup inventory drift check",
    )
    parser.add_argument(
        "--skip-normalization-matrix",
        action="store_true",
        help="Skip pipeline normalization field-matrix --check",
    )
    parser.add_argument(
        "--skip-build", action="store_true", help="Skip strict MkDocs build"
    )
    args = parser.parse_args(argv)

    steps: list[tuple[str, list[str]]] = []
    if not args.skip_links:
        # Full check-links suite (unflagged = all runners). Partial
        # --links/--specs/--configs alone is insufficient for docs governance.
        steps.append(
            (
                "check-links",
                [
                    sys.executable,
                    "-m",
                    "scripts.docs.checks.check_links",
                ],
            )
        )
    if not args.skip_drift:
        steps.append(
            (
                "check-drift",
                [
                    sys.executable,
                    "-m",
                    "scripts.docs.checks.check_drift",
                    "--ports",
                    "--classes",
                    "--runtime-mirrors",
                    "--freshness",
                    "--modules",
                ],
            )
        )
    if not args.skip_docstrings:
        steps.append(
            (
                "check-docstrings",
                [
                    sys.executable,
                    "-m",
                    "scripts.docs.checks.check_docstrings",
                    "--summary",
                ],
            )
        )
    if not args.skip_cleanup_inventory:
        steps.append(
            (
                "generate-cleanup-inventory",
                [
                    sys.executable,
                    "-m",
                    "scripts.docs.checks.documentation_cleanup_inventory",
                    "--check",
                ],
            )
        )
    if not args.skip_normalization_matrix:
        steps.append(
            (
                "generate-pipeline-normalization-matrix",
                [
                    sys.executable,
                    "-m",
                    "scripts.docs",
                    "generate-pipeline-normalization-matrix",
                    "--check",
                ],
            )
        )

    for label, argv in steps:
        exit_code = _run_step(label, argv)
        if exit_code != 0:
            return exit_code

    if not args.skip_build:
        extra_status = _require_docs_extra()
        if extra_status != 0:
            return extra_status
        with tempfile.TemporaryDirectory(prefix="bioetl-mkdocs-site-") as site_dir:
            exit_code = _run_step(
                "strict-build",
                [
                    sys.executable,
                    "-m",
                    "mkdocs",
                    "build",
                    "--strict",
                    "--clean",
                    "--site-dir",
                    site_dir,
                ],
            )
            if exit_code != 0:
                return exit_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
