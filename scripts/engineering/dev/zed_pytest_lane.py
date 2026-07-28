#!/usr/bin/env python3
"""Zed-safe pytest lane runner (Windows PowerShell argv-safe).

Zed on Windows often launches tasks via ``powershell -C``, which re-tokenizes
arguments on spaces. Marker expressions such as::

    architecture and not slow and not benchmark and not memory

then become bare positional path arguments (``and``, ``not``, ...), and pytest
fails with ``file or directory not found: and``.

This helper keeps multi-word pytest markers inside Python so task ``args`` only
contain space-free tokens.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence

# Common local defaults for Zed interactive runs.
_TB_SHORT = "--tb=short"
_COMMON = (
    _TB_SHORT,
    "--no-cov",
    "-p",
    "no:benchmark",
    "--maxfail=1",
)

# Named lanes used by `.zed/tasks.json`. Values are full pytest argv tails
# (everything after ``pytest``).
LANES: dict[str, tuple[str, ...]] = {
    "smoke": ("tests/smoke/", "-v", *_COMMON),
    "unit": ("tests/unit/", "-q", *_COMMON),
    "unit-fast": (
        "tests/unit/",
        "-q",
        "-m",
        "not repo_backed and not slow and not serial and not benchmark and not memory",
        *_COMMON,
    ),
    "architecture": (
        "tests/architecture/",
        "-q",
        "-m",
        "architecture and not slow and not benchmark and not memory",
        *_COMMON,
    ),
    "integration-replay": (
        "tests/integration/",
        "-q",
        "-m",
        "not e2e and not live and not slow and not benchmark and not memory",
        *_COMMON,
    ),
    "contracts": (
        "tests/contract/",
        "tests/unit/contracts/",
        "-q",
        "-m",
        "no_api or not network",
        "-p",
        "no:xdist",
        *_COMMON,
    ),
    "security": ("tests/security/", "-q", *_COMMON),
    "e2e-smoke": ("tests/e2e/", "-m", "e2e_smoke", "-v", *_COMMON),
    "failed": (
        "tests/",
        "--lf",
        "-x",
        "-v",
        _TB_SHORT,
        "--no-cov",
        "-p",
        "no:benchmark",
    ),
    "coverage": (
        "tests/",
        # Coverage gate measures src/bioetl via unit/integration paths.
        # Architecture/e2e/contract are separate lanes (and spawn git/subprocess
        # that can hang on cloud-synced Windows worktrees under suite load).
        "--ignore=tests/e2e",
        "--ignore=tests/contract",
        "--ignore=tests/architecture",
        "-m",
        "not memory and not benchmark and not slow",
        "--cov=src/bioetl",
        "--cov-report=term-missing",
        "--cov-report=html:reports/coverage/htmlcov",
        "--cov-fail-under=85",
        "-q",
        _TB_SHORT,
    ),
}


def _usage() -> str:
    lanes = ", ".join(sorted(LANES))
    return (
        "Usage:\n"
        f"  python scripts/engineering/dev/zed_pytest_lane.py <lane>\n"
        "  python scripts/engineering/dev/zed_pytest_lane.py file <path>\n"
        "  python scripts/engineering/dev/zed_pytest_lane.py nearest <path> <symbol>\n"
        f"Lanes: {lanes}\n"
    )


def _run_pytest(argv_tail: Sequence[str]) -> int:
    # Ensure interactive Zed runs stay offline for VCR by default.
    if "VCR_RECORD_MODE" not in os.environ:
        os.environ["VCR_RECORD_MODE"] = "none"
    if "PYTHONDONTWRITEBYTECODE" not in os.environ:
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    import pytest

    return int(pytest.main(list(argv_tail)))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(_usage(), file=sys.stderr, end="")
        return 2

    mode = args[0]

    if mode == "file":
        if len(args) < 2:
            print("file lane requires a path argument", file=sys.stderr)
            return 2
        path = args[1]
        extra = args[2:]
        return _run_pytest((path, "-v", *_COMMON, *extra))

    if mode == "nearest":
        if len(args) < 3:
            print("nearest lane requires <path> <symbol>", file=sys.stderr)
            return 2
        path = args[1]
        symbol = args[2]
        extra = args[3:]
        return _run_pytest((path, "-k", symbol, "-v", *_COMMON, *extra))

    if mode not in LANES:
        print(f"Unknown lane: {mode!r}\n{_usage()}", file=sys.stderr, end="")
        return 2

    extra = args[1:]
    return _run_pytest((*LANES[mode], *extra))


if __name__ == "__main__":
    raise SystemExit(main())
