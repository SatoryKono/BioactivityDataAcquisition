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


def _run_launcher(
    tmp_path: Path,
    *args: str,
    api_key: str | None = "test-api-key",
    auth_status_exit: int = 0,
    login_exit: int = 0,
    doctor_exit: int = 0,
    config_exit: int = 0,
    review_exit: int = 0,
    review_event: str = "complete",
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture_path = tmp_path / "coderabbit-commands.txt"

    _write_executable(
        bin_dir / "git",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == *"rev-parse --show-toplevel"* ]]; then
  printf '%s\n' "$FAKE_REPO_ROOT"
elif [[ "$*" == *"rev-parse -q --verify"* || "$*" == *"rev-parse HEAD"* ]]; then
  printf '%s\n' "$FAKE_BASE_COMMIT"
elif [[ "$*" == *"status --short"* || "$*" == *"diff --binary"* ]]; then
  exit 0
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
if [[ "${1:-}" == "auth" && "${2:-}" == "status" ]]; then
  exit "$CODERABBIT_AUTH_STATUS_EXIT"
fi
if [[ "${1:-}" == "auth" && "${2:-}" == "login" ]]; then
  exit "$CODERABBIT_LOGIN_EXIT"
fi
case "${1:-}" in
  doctor) exit "$CODERABBIT_DOCTOR_EXIT" ;;
  config) exit "$CODERABBIT_CONFIG_EXIT" ;;
  review)
    printf '{"type":"%s","status":"%s"}\n' "$CODERABBIT_REVIEW_EVENT" "$CODERABBIT_REVIEW_EVENT"
    exit "$CODERABBIT_REVIEW_EXIT"
    ;;
esac
""",
    )

    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "CODERABBIT_CAPTURE": str(capture_path),
        "CODERABBIT_AUTH_STATUS_EXIT": str(auth_status_exit),
        "CODERABBIT_LOGIN_EXIT": str(login_exit),
        "CODERABBIT_DOCTOR_EXIT": str(doctor_exit),
        "CODERABBIT_CONFIG_EXIT": str(config_exit),
        "CODERABBIT_REVIEW_EXIT": str(review_exit),
        "CODERABBIT_REVIEW_EVENT": review_event,
        "FAKE_REPO_ROOT": str(tmp_path),
        "FAKE_BASE_COMMIT": FAKE_BASE_COMMIT,
    }
    if api_key is None:
        env.pop("CODERABBIT_API_KEY", None)
    else:
        env["CODERABBIT_API_KEY"] = api_key
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
        "--version",
        "auth login --api-key test-api-key",
        "doctor",
        f"config validate {tmp_path}/.coderabbit.yaml",
        f"review --agent --base-commit={FAKE_BASE_COMMIT} -c {tmp_path}/AGENTS.md {tmp_path}/.coderabbit.yaml",
    ]


def test_cached_credentials_are_accepted_without_api_key(tmp_path: Path) -> None:
    result = _run_launcher(
        tmp_path,
        "1",
        "--base=origin/main",
        "--coderabbit-only",
        "--log-dir",
        str(tmp_path / "logs"),
        api_key=None,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert _captured_commands(tmp_path) == [
        "--version",
        "auth status --agent",
        "doctor",
        f"config validate {tmp_path}/.coderabbit.yaml",
        f"review --agent --base-commit={FAKE_BASE_COMMIT} -c {tmp_path}/AGENTS.md {tmp_path}/.coderabbit.yaml",
    ]


def test_absent_api_key_and_invalid_cache_abort_before_review(tmp_path: Path) -> None:
    result = _run_launcher(
        tmp_path,
        "1",
        "--base=origin/main",
        "--coderabbit-only",
        "--log-dir",
        str(tmp_path / "logs"),
        api_key=None,
        auth_status_exit=1,
    )

    assert result.returncode == 1
    assert "No CodeRabbit credentials" in result.stderr
    assert _captured_commands(tmp_path) == ["--version", "auth status --agent"]


@pytest.mark.parametrize("failure", ["login_exit", "doctor_exit", "config_exit"])
def test_failed_preflight_prevents_review(tmp_path: Path, failure: str) -> None:
    result = _run_launcher(tmp_path, "changes", "--base=HEAD", **{failure: 1})
    assert result.returncode == 1
    assert not any(cmd.startswith("review ") for cmd in _captured_commands(tmp_path))


def test_preflight_only_does_not_start_review(tmp_path: Path) -> None:
    result = _run_launcher(tmp_path, "--preflight")
    assert result.returncode == 0, result.stderr
    assert not any(cmd.startswith("review ") for cmd in _captured_commands(tmp_path))


def test_review_failure_survives_tee_and_preserves_log(tmp_path: Path) -> None:
    result = _run_launcher(
        tmp_path,
        "changes",
        "--base=HEAD",
        "--uncommitted",
        "--dir",
        "src/bioetl",
        review_exit=7,
        review_event="error",
    )
    assert result.returncode == 7
    assert "Done:" not in result.stdout
    review = _captured_commands(tmp_path)[-1]
    assert "--uncommitted --dir src/bioetl" in review
    logs = list((tmp_path / "reports/quality/coderabbit/local").glob("*.jsonl"))
    assert len(logs) == 1
    assert '"type":"error"' in logs[0].read_text()


@pytest.mark.parametrize("event", ["error", "heartbeat"])
def test_zero_exit_without_completed_review_is_not_success(
    tmp_path: Path,
    event: str,
) -> None:
    result = _run_launcher(tmp_path, "changes", "--base=HEAD", review_event=event)
    assert result.returncode != 0
    assert "Done:" not in result.stdout


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
    # Script writes errors to stderr, not stdout
    assert "[ERROR]" in result.stderr or "[ERROR]" in result.stdout


def test_long_help_option_exits_without_starting_review(tmp_path: Path) -> None:
    result = _run_launcher(tmp_path, "--help")

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert not (tmp_path / "coderabbit-commands.txt").exists()
