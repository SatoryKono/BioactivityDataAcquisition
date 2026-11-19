"""Exercise orb hooks without installing dependencies or exposing credentials."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[6]
BASH = (
    str(Path("C:/Program Files/Git/bin/bash.exe"))
    if os.name == "nt" and Path("C:/Program Files/Git/bin/bash.exe").is_file()
    else shutil.which("bash")
    if os.name != "nt"
    else None
)
pytestmark = [
    pytest.mark.unit,
    pytest.mark.repo_backed,
    pytest.mark.skipif(BASH is None, reason="Bash is required to exercise orb hooks"),
]


@dataclass
class Sandbox:
    env: dict[str, str]
    home: Path
    scratch: Path
    calls: Path


def _shell_path(path: Path) -> str:
    if os.name == "nt":
        return "/" + path.drive[0].lower() + "/" + path.as_posix()[3:]
    return str(path)


def _command(directory: Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text("#!/bin/sh\nset -eu\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)


def _environment(tmp_path: Path, system: str, architecture: str) -> Sandbox:
    commands = tmp_path / "bin"
    commands.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    _command(commands, "uv", 'printf "uv\\n" >> "$AMP_TEST_CALLS"')
    _command(commands, "npm", 'printf "npm\\n" >> "$AMP_TEST_CALLS"')
    _command(commands, "npx", 'printf "npx\\n" >> "$AMP_TEST_CALLS"')
    _command(commands, "gh", 'printf "gh\\n" >> "$AMP_TEST_CALLS"; exit 1')
    _command(
        commands,
        "uname",
        'case "$1" in -s) printf "%s\\n" "$AMP_TEST_SYSTEM";; '
        '-m) printf "%s\\n" "$AMP_TEST_ARCH";; *) exit 1;; esac',
    )
    _command(
        commands,
        "curl",
        'printf "curl\\n" >> "$AMP_TEST_CALLS"\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  if [ "$1" = "--output" ]; then\n'
        '    printf "untrusted archive" > "$2"\n'
        "    exit 0\n"
        "  fi\n"
        "  shift\n"
        "done\nexit 1",
    )
    env = {
        "PATH": f"{_shell_path(commands)}:/usr/bin:/bin",
        "HOME": _shell_path(home),
        "TMPDIR": _shell_path(scratch),
        "LC_ALL": "C",
        "BIOETL_REPO_ENV_LOADED": "1",
        "AMP_TEST_CALLS": _shell_path(tmp_path / "calls"),
        "AMP_TEST_SYSTEM": system,
        "AMP_TEST_ARCH": architecture,
    }
    # Git Bash prepends its system directories during startup. Restore the
    # fixture command path before running hooks so no host tools are installed.
    startup = tmp_path / "bash-startup"
    startup.write_text('export PATH="$AMP_TEST_PATH"\n', encoding="utf-8")
    env["BASH_ENV"] = _shell_path(startup)
    env["AMP_TEST_PATH"] = env["PATH"]
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return Sandbox(env, home, scratch, tmp_path / "calls")


@pytest.mark.parametrize("architecture", ["x86_64", "aarch64"])
def test_setup_rejects_corrupt_archive_without_replacing_binary(
    tmp_path: Path, architecture: str
) -> None:
    sandbox = _environment(tmp_path, "Linux", architecture)
    env = sandbox.env
    binary = sandbox.home / "tools/bin/github-mcp-server"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"existing binary must survive a bad download")
    before = binary.read_bytes()

    result = subprocess.run(
        [BASH, _shell_path(ROOT / ".agents/setup")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode != 0
    assert "checksum" in result.stderr.lower()
    assert binary.read_bytes() == before
    assert sandbox.calls.read_text().splitlines() == ["uv", "npm", "npx", "curl"]
    assert not list(sandbox.scratch.iterdir())


@pytest.mark.parametrize(
    ("system", "architecture"), [("Darwin", "arm64"), ("Linux", "mips")]
)
def test_setup_refuses_unsupported_platform_before_download(
    tmp_path: Path, system: str, architecture: str
) -> None:
    sandbox = _environment(tmp_path, system, architecture)
    env = sandbox.env
    result = subprocess.run(
        [BASH, _shell_path(ROOT / ".agents/setup")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 64
    assert "unsupported GitHub MCP platform" in result.stderr
    assert sandbox.calls.read_text().splitlines() == ["uv", "npm", "npx"]
    assert not (sandbox.home / "tools").exists()


def test_resume_warns_without_installing_dependencies_or_blocking(
    tmp_path: Path,
) -> None:
    sandbox = _environment(tmp_path, "Linux", "x86_64")
    env = sandbox.env
    result = subprocess.run(
        [BASH, _shell_path(ROOT / ".agents/resume")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "gh is not authenticated" in result.stderr
    assert sandbox.calls.read_text().splitlines() == ["gh"]


def test_amp_github_launch_keeps_read_only_policy_and_scrubs_other_secrets(
    tmp_path: Path,
) -> None:
    sandbox = _environment(tmp_path, "Linux", "x86_64")
    env = sandbox.env
    config = json.loads((ROOT / ".amp/settings.json").read_text())
    github = config["amp.mcpServers"]["github"]
    env.update(github["env"])
    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_" + "x" * 40
    env["OPENAI_API_KEY"] = "unrelated-fixture-credential"
    # Exercise developer-config isolation without creating any .env file.
    foreign = tmp_path / "developer-bin"
    foreign.mkdir()
    _command(foreign, "foreign-github", "exit 97")
    settings = tmp_path / "developer-settings.txt"
    settings.write_text(
        "BIOETL_GITHUB_MCP_SERVER=" + _shell_path(foreign / "foreign-github") + "\n",
        encoding="utf-8",
    )
    env["BIOETL_ENV_FILE"] = _shell_path(settings)
    commands = sandbox.home / "tools/bin"
    commands.mkdir(parents=True)
    _command(
        commands,
        "github-mcp-server",
        'test -z "${OPENAI_API_KEY:-}"\nprintf "%s\\n" "$@"',
    )

    result = subprocess.run(
        [BASH, *github["args"]],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    arguments = result.stdout.splitlines()
    assert arguments[0] == "stdio"
    assert "--read-only" in arguments
    assert "--lockdown-mode" in arguments
    excluded = set(arguments[arguments.index("--exclude-tools") + 1].split(","))
    assert {
        "create_or_update_file",
        "push_files",
        "delete_file",
        "fork_repository",
        "create_repository",
        "merge_pull_request",
        "actions_run_trigger",
    } <= excluded
