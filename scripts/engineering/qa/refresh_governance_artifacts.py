"""Governance artifact refresh recipe entrypoint (architecture audit M4 #6513).

Run after write-capable changes under ``src/bioetl/**`` (and related quality
configs) to refresh inventories/baselines required by architecture gates.

Usage (repo root):

    python -m scripts.engineering.qa.refresh_governance_artifacts
    python -m scripts.engineering.qa.refresh_governance_artifacts --check

Does NOT raise tech-debt budgets. Does NOT rewrite baselines unless the
underlying source tree changed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str], *, check: bool = True) -> int:
    print("+", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def refresh(*, check_only: bool) -> None:
    """Refresh or verify governance artifacts in deterministic order."""
    if check_only:
        _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/architecture/test_module_coverage_inventory.py::"
                "test_module_coverage_inventory_source_tree_hash_is_current",
                "-q",
            ]
        )
        print("CHECK: module-coverage inventory hash is current")
        return

    # 1) Module coverage inventory source_tree_sha256 (hash-only path)
    _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_module_coverage_inventory",
            "--allow-missing-coverage-xml",
        ]
    )

    # 2) Optional root helper when present
    refresh_helper = ROOT / "_refresh_module_coverage_inventory.py"
    if refresh_helper.exists():
        _run([sys.executable, str(refresh_helper)])

    print("REFRESH complete. Recommended verification:")
    print(
        "  pytest tests/architecture/test_module_coverage_inventory.py "
        "-q --tb=no"
    )
    print(
        "  pytest tests/architecture/test_architecture_audit_closeout_gates.py "
        "-q --tb=short"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify inventory hash only (no write).",
    )
    args = parser.parse_args(argv)
    refresh(check_only=args.check)


if __name__ == "__main__":
    main()
