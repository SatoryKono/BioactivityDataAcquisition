"""CLI regression coverage for the bounded CodeRabbit review launcher."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="CodeRabbit launcher is a POSIX shell entrypoint",
    ),
]

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "ops" / "run-coderabbit-reviews.sh"
FAKE_BASE_COMMIT = "a8ec3a21509397da58f5d8457a64a2024edb12ea"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _run_launcher(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture_path = tmp_path / "coderabbit-commands.txt"

    _write_executable(
        bin_dir / "git",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"rev-parse --show-toplevel"* ]]; then
  printf '%s\n' "$FAKE_REPO_ROOT"
elif [[ "$*" == *"rev-parse -q --verify"* ]]; then
  printf '%s\n' "$FAKE_BASE_COMMIT"
else
  exit 1
fi
""",
    )
    _write_executable(
        bin_dir / "coderabbit",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$CODERABBIT_CAPTURE"
""",
    )

    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "CODERABBIT_API_KEY": "test-api-key",
        "CODERABBIT_CAPTURE": str(capture_path),
        "FAKE_REPO_ROOT": str(ROOT),
        "FAKE_BASE_COMMIT": FAKE_BASE_COMMIT,
    }
    env.pop("CODERABBIT_BASE_COMMIT", None)
    env.pop("CODERABBIT_REVIEW_LOG_DIR", None)

    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def _captured_commands(tmp_path: Path) -> list[str]:
    capture_path = tmp_path / "coderabbit-commands.txt"
    return capture_path.read_text(encoding="utf-8").splitlines()


def test_options_are_preserved_when_topic_is_omitted(tmp_path: Path) -> None:
    result = _run_launcher(
        tmp_path,
        "--base",
        "origin/main",
        "--coderabbit-only",
        "--log-dir",
        str(tmp_path / "logs"),
    )

    assert result.returncode == 0, result.stderr or result.stdout
    commands = _captured_commands(tmp_path)
    assert sum(command.startswith("review ") for command in commands) == 5
    assert all(
        f"--base-commit={FAKE_BASE_COMMIT}" in command
        for command in commands
        if command.startswith("review ")
    )


def test_base_ref_is_normalized_in_generated_review_command(tmp_path: Path) -> None:
    result = _run_launcher(
        tmp_path,
        "1",
        "--base=origin/main",
        "--coderabbit-only",
        "--log-dir",
        str(tmp_path / "logs"),
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert _captured_commands(tmp_path) == [
        "auth login --api-key test-api-key",
        f"review --base-commit={FAKE_BASE_COMMIT}",
    ]


@pytest.mark.parametrize(
    "args",
    [
        ("1", "--base"),
        ("1", "--base="),
        ("1", "--base", ""),
        ("1", "--base", "--coderabbit-only"),
        ("1", "--log-dir"),
        ("1", "--log-dir="),
        ("1", "--log-dir", ""),
        ("1", "--log-dir", "--coderabbit-only"),
    ],
)
def test_required_option_values_reject_missing_empty_or_option_tokens(
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    result = _run_launcher(tmp_path, *args)

    assert result.returncode == 1
    assert "[ERROR]" in result.stdout


def test_long_help_option_exits_without_starting_review(tmp_path: Path) -> None:
    result = _run_launcher(tmp_path, "--help")

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert not (tmp_path / "coderabbit-commands.txt").exists()
