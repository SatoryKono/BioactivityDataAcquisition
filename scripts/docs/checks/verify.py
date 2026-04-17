#!/usr/bin/env python3
"""Run the canonical docs verification chain."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

_DOCS_DIR = Path(__file__).resolve().parents[1]


def _run_step(label: str, argv: list[str]) -> int:
    print(f"[docs-verify] {label}: {' '.join(argv)}", flush=True)
    result = subprocess.run(argv, check=False)
    return result.returncode


def main() -> int:
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
        "--skip-build", action="store_true", help="Skip strict MkDocs build"
    )
    args = parser.parse_args()

    steps: list[tuple[str, list[str]]] = []
    if not args.skip_links:
        steps.append(
            (
                "check-links",
                [
                    sys.executable,
                    str(_DOCS_DIR / "check_doc_links.py"),
                    "--links",
                    "--specs",
                    "--configs",
                ],
            )
        )
    if not args.skip_drift:
        steps.append(
            (
                "check-drift",
                [
                    sys.executable,
                    str(_DOCS_DIR / "check_doc_drift.py"),
                    "--ports",
                    "--classes",
                ],
            )
        )
    if not args.skip_docstrings:
        steps.append(
            (
                "check-docstrings",
                [
                    sys.executable,
                    str(_DOCS_DIR / "check_docstring_coverage.py"),
                    "--summary",
                ],
            )
        )

    for label, argv in steps:
        exit_code = _run_step(label, argv)
        if exit_code != 0:
            return exit_code

    if not args.skip_build:
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
