# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guardrails against hardcoded mounted-worktree skip debt."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_MARKERS = (
    "Network drive timeout",
    "E:\\g-drive",
)
# Full-suite coverage runs can keep git busy on cloud-synced checkouts; keep a
# hard ceiling so this guard cannot hang the coverage gate.
_GIT_GREP_TIMEOUT_SECONDS = 30.0


def _hidden_windows_subprocess_kwargs() -> dict[str, int]:
    if os.name != "nt":
        return {}
    create_no_window = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"creationflags": create_no_window} if create_no_window else {}


def test_tests_do_not_reintroduce_hardcoded_network_drive_skips() -> None:
    offenders: list[str] = []
    this_file = Path(__file__).resolve()
    # Exclude token validation helpers which legitimately skip on Windows
    excluded_file = (
        "tests/unit/repo_backed/scripts/ai/mcp/test_token_validation_helpers.py"
    )

    # Search index blobs in one process so cloud-backed worktree files are not
    # opened and hydrated one by one on Windows.
    try:
        result = subprocess.run(
            [
                "git",
                "grep",
                "--cached",
                "-n",
                "-F",
                *(
                    argument
                    for marker in FORBIDDEN_MARKERS
                    for argument in ("-e", marker)
                ),
                "--",
                ":(glob)tests/**/test_*.py",
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_GREP_TIMEOUT_SECONDS,
            **_hidden_windows_subprocess_kwargs(),
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            f"git grep for mounted-worktree skip markers timed out after "
            f"{_GIT_GREP_TIMEOUT_SECONDS:.0f}s (cwd={ROOT}). "
            "Re-run tests/architecture separately; avoid coverage lane load on "
            f"cloud-synced worktrees. partial_stdout={exc.stdout!r}"
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
