#!/usr/bin/env python3

"""Zed-safe pytest lane runner (Windows PowerShell argv-safe).

Zed on Windows often launches tasks via ``powershell -C``, which re-tokenizes
arguments on spaces. Marker expressions such as::

    architecture and not slow and not benchmark and not memory

then become bare positional path arguments (``and``, ``not``, ...), and pytest
fails with ``file or directory not found: and``.

This helper keeps multi-word pytest markers inside Python so task ``args`` only
contain space-free tokens.

Canonical lane membership for CI/telemetry lives in
``configs/quality/test_matrix.yaml``. The mappings below are the maintained
local Zed projections of those lanes (see
``tests/unit/repo_backed/scripts/test_zed_workspace_config.py``).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.engineering.dev.zed_env_doctor import ensure_ready

# Common local defaults for Zed interactive runs (not merge-gate authority).
_TB_SHORT = "--tb=short"
_TESTS_ROOT = "tests/"
_VCR_RECORD_NONE = "--vcr-record=none"
_COMMON = (
    _TB_SHORT,
    "--no-cov",
    "-p",
    "no:benchmark",
    "--maxfail=1",
)

# Explicit mapping from Zed lane keys to canonical suite_name values in
# configs/quality/test_matrix.yaml. Keys without an entry are local-only UX.
CANONICAL_SUITE_BY_LANE: dict[str, str] = {
    "smoke": "smoke",
    "unit-fast": "unit-fast",
    "architecture-fast": "architecture-fast-boundary",
    "integration-replay": "integration-replay",
    "contracts": "contracts",
    "security": "security",
    "e2e-smoke": "e2e-smoke",
    # coverage-local intentionally has NO suite mapping: advisory only.
}

# Named lanes used by `.zed/tasks.json`. Values are full pytest argv tails
# (everything after ``pytest``). Path/marker membership for canonical keys
# must stay parity-tested against test_matrix.yaml.
LANES: dict[str, tuple[str, ...]] = {
    "smoke": (
        "tests/smoke/",
        "-m",
        "not benchmark and not memory",
        "-v",
        *_COMMON,
    ),
    "unit": (
        # Local convenience over full unit tree; not a named matrix suite.
        "tests/unit/",
        "-q",
        *_COMMON,
    ),
    "unit-fast": (
        "tests/unit/",
        "--ignore=tests/unit/scripts",
        "--ignore=tests/unit/repo_backed",
        "-q",
        "-m",
        (
            "not fs_contract and not repo_backed and not subprocess_backed "
            "and not slow and not benchmark and not memory"
        ),
        *_COMMON,
    ),
    "architecture-fast": (
        "tests/architecture/",
        "-q",
        "-m",
        "architecture and not slow and not benchmark and not memory",
        *_COMMON,
    ),
    # Backward-compatible alias used by older docs/keybindings.
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
        "not slow and not benchmark and not memory",
        _VCR_RECORD_NONE,
        *_COMMON,
    ),
    "contracts": (
        "tests/contract/",
        "tests/unit/contracts/",
        "-q",
        "-m",
        "not slow and not benchmark and not memory",
        # Local Windows stability: avoid xdist on contract paths.
        "-p",
        "no:xdist",
        *_COMMON,
    ),
    "security": (
        "tests/security/",
        "-q",
        "-m",
        "security and not benchmark and not memory",
        *_COMMON,
    ),
    "e2e-smoke": (
        "tests/e2e/test_chembl_activity_e2e.py",
        "tests/e2e/test_pipeline_matrix_e2e.py",
        "-m",
        "e2e_smoke and not benchmark and not memory",
        "-v",
        *_COMMON,
    ),
    "failed": (
        _TESTS_ROOT,
        "--lf",
        "-x",
        "-v",
        _TB_SHORT,
        "--no-cov",
        "-p",
        "no:benchmark",
    ),
    # Advisory local coverage estimate — NOT the canonical coverage-verify gate.
    "coverage-local": (
        _TESTS_ROOT,
        "--ignore=tests/e2e",
        "--ignore=tests/contract",
        "--ignore=tests/architecture",
        # Script/tooling tests have a dedicated serial CI lane and can exceed the
        # Windows per-test timeout when instrumented inside this product estimate.
        "--ignore=tests/unit/scripts",
        # Memory proof tests spawn git ls-files; under coverage they exceed the
        # pytest-timeout and do not cover src/bioetl.
        "--ignore=tests/unit/memory",
        "--ignore=tests/integration/memory",
        # Repo-backed tests spawn PowerShell/WSL/docker children; under coverage
        # they stall the 98-99% Zed tail and do not cover src/bioetl.
        "--ignore=tests/unit/repo_backed",
        "-m",
        "not memory and not benchmark and not slow",
        "--cov=src/bioetl",
        # term-missing dumps every uncovered line for ~2500 modules and can
        # kill the Zed/Windows capture after tests have already passed.
        # htmlcov for the full src/bioetl tree hangs the same way on Windows.
        "--cov-report=term:skip-covered",
        "--cov-fail-under=85",
        "-q",
        _TB_SHORT,
    ),
    # Legacy alias kept so older task labels still resolve during migration.
    "coverage": (
        "tests/",
        "--ignore=tests/e2e",
        "--ignore=tests/contract",
        "--ignore=tests/architecture",
        "--ignore=tests/unit/scripts",
        "--ignore=tests/unit/memory",
        "--ignore=tests/integration/memory",
        "--ignore=tests/unit/repo_backed",
        "-m",
        "not memory and not benchmark and not slow",
        "--cov=src/bioetl",
        "--cov-report=term:skip-covered",
        "--cov-fail-under=85",
        "-q",
        _TB_SHORT,
    ),
}


def _consume_lane_token(
    tokens: list[str], index: int
) -> tuple[int, str | None, str | None, str | None, bool]:
    token = tokens[index]
    if token == "-m" and index + 1 < len(tokens):
        return index + 2, None, None, tokens[index + 1], False
    if token.startswith("--ignore="):
        return index + 1, None, token.split("=", 1)[1], None, False
    if token == "--ignore" and index + 1 < len(tokens):
        return index + 2, None, tokens[index + 1], None, False
    if token == _VCR_RECORD_NONE:
        return index + 1, None, None, None, True
    if token == "--vcr-record" and index + 1 < len(tokens):
        return index + 2, None, None, None, tokens[index + 1] == "none"
    if token.startswith("-"):
        return index + 1, None, None, None, False
    path = token if token.startswith(_TESTS_ROOT) or token.endswith(".py") else None
    return index + 1, path, None, None, False


def extract_lane_membership(argv_tail: Sequence[str]) -> dict[str, Any]:
    """Extract paths, marker, ignores, and vcr flags from a lane argv tail.

    Used by repo-backed parity tests against ``test_matrix.yaml``.
    """
    paths: list[str] = []
    ignores: list[str] = []
    marker: str | None = None
    has_vcr_none = False
    tokens = list(argv_tail)
    index = 0
    while index < len(tokens):
        index, path, ignore, parsed_marker, records_none = _consume_lane_token(
            tokens, index
        )
        if path is not None:
            paths.append(path)
        if ignore is not None:
            ignores.append(ignore)
        if parsed_marker is not None:
            marker = parsed_marker
        has_vcr_none = has_vcr_none or records_none
    return {
        "paths": paths,
        "ignores": ignores,
        "marker": marker,
        "vcr_record_none": has_vcr_none,
    }


def canonical_lane_specs() -> Mapping[str, dict[str, Any]]:
    """Return membership specs for parity-tested Zed lanes."""
    specs: dict[str, dict[str, Any]] = {}
    for lane_key, suite_name in CANONICAL_SUITE_BY_LANE.items():
        membership = extract_lane_membership(LANES[lane_key])
        membership["suite_name"] = suite_name
        specs[lane_key] = membership
    return specs


def _usage() -> str:
    lanes = ", ".join(sorted(LANES))
    return (
        "Usage:\n"
        f"  python scripts/engineering/dev/zed_pytest_lane.py <lane>\n"
        "  python scripts/engineering/dev/zed_pytest_lane.py file <path>\n"
        "  python scripts/engineering/dev/zed_pytest_lane.py nearest <path> <symbol>\n"
        f"Lanes: {lanes}\n"
        "Note: coverage-local is an advisory estimate, not coverage-verify.\n"
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
    ensure_ready(modules=("pytest",))

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
