"""Architecture guardrails against hardcoded mounted-worktree skip debt."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_MARKERS = (
    "Network drive timeout",
    "E:\\g-drive",
)


def test_tests_do_not_reintroduce_hardcoded_network_drive_skips() -> None:
    offenders: list[str] = []
    this_file = Path(__file__).resolve()
    # Exclude token validation helpers which legitimately skip on Windows
    excluded_file = (
        "tests/unit/repo_backed/scripts/ai/mcp/test_token_validation_helpers.py"
    )

    # Search index blobs in one process so cloud-backed worktree files are not
    # opened and hydrated one by one on Windows.
    result = subprocess.run(
        [
            "git",
            "grep",
            "--cached",
            "-n",
            "-F",
            *(argument for marker in FORBIDDEN_MARKERS for argument in ("-e", marker)),
            "--",
            ":(glob)tests/**/test_*.py",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        encoding="utf-8",
    )
    assert result.returncode in (0, 1), result.stderr

    this_file_relative = this_file.relative_to(ROOT).as_posix()
    for match in result.stdout.splitlines():
        relative_path, _line_number, content = match.split(":", maxsplit=2)
        if relative_path == this_file_relative:
            continue
        if relative_path == excluded_file:
            continue
        for marker in FORBIDDEN_MARKERS:
            if marker in content:
                offenders.append(f"{relative_path}: {marker}")

    assert not offenders, (
        "Retire hardcoded mounted-worktree skip debt and use local-temp fixtures "
        "or capability bootstrap instead. Offenders:\n"
        + "\n".join(f"  - {offender}" for offender in offenders)
    )
