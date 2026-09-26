"""Isolated git fixture repos that cannot inherit host GPG, hooks, or prompts.

Windows ``git commit`` with inherited stdin and ``capture_output=True`` PIPEs
hangs when the host git config, GPG pinentry, a hook, or Git Credential Manager
waits on a TTY. pytest-timeout then dumps reader threads after 60s without
killing the child. Fixture commits must use a stripped env, ``stdin=DEVNULL``,
``--no-gpg-sign --no-verify``, a hard subprocess timeout, and file-backed
stdio so ``TimeoutExpired`` cannot deadlock in ``communicate()``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_GIT_TIMEOUT_SECONDS = 20.0
_AUTHOR_NAME = "Proof Test"
_AUTHOR_EMAIL = "proof@example.invalid"


def isolated_git_env(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return an env that cannot see host GIT_* config, prompts, or GPG sockets."""
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(
        {
            "GIT_AUTHOR_NAME": _AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL": _AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": _AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": _AUTHOR_EMAIL,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GCM_INTERACTIVE": "never",
        }
    )
    if extra:
        env.update(extra)
    return env


def _windows_creation_flags() -> int:
    if sys.platform != "win32":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def run_isolated_git(
    repo: Path,
    *args: str,
    timeout: float = DEFAULT_GIT_TIMEOUT_SECONDS,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one git command in ``repo`` without inheriting host git/GPG state."""
    resolved = Path(repo)
    hooks_dir = resolved / ".git-isolated-hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "git",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "tag.gpgsign=false",
        "-c",
        "core.hooksPath=" + str(hooks_dir),
        "-c",
        "init.templateDir=",
        "-C",
        str(resolved),
        *args,
    ]
    merged_env = isolated_git_env() if env is None else env
    with tempfile.TemporaryDirectory(prefix="bioetl_git_") as temp_dir:
        stdout_path = Path(temp_dir) / "stdout.txt"
        stderr_path = Path(temp_dir) / "stderr.txt"
        try:
            with (
                stdout_path.open(
                    "w", encoding="utf-8", errors="replace"
                ) as stdout_file,
                stderr_path.open(
                    "w", encoding="utf-8", errors="replace"
                ) as stderr_file,
            ):
                completed = subprocess.run(
                    command,
                    cwd=resolved,
                    env=merged_env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=timeout,
                    creationflags=_windows_creation_flags(),
                )
            return subprocess.CompletedProcess(
                args=command,
                returncode=completed.returncode,
                stdout=stdout_path.read_text(encoding="utf-8", errors="replace"),
                stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
            )
        except subprocess.TimeoutExpired as exc:
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=exc.timeout,
                output=stdout_path.read_text(encoding="utf-8", errors="replace"),
                stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
            ) from None


def init_tracked_fixture_repo(
    repo: Path,
    *,
    filename: str = "tracked.py",
    content: str = "VALUE = 1\n",
    message: str = "test fixture",
) -> Path:
    """Create a tiny local git repo with one tracked commit and no host signing."""
    resolved = Path(repo)
    resolved.mkdir(parents=True, exist_ok=True)
    empty_config = resolved.parent / "isolated.gitconfig"
    empty_config.write_text("", encoding="utf-8")
    gnupg_home = resolved.parent / "isolated-gnupg"
    gnupg_home.mkdir(parents=True, exist_ok=True)
    env = isolated_git_env(
        extra={
            "GIT_CONFIG_GLOBAL": str(empty_config),
            "GIT_CONFIG_SYSTEM": str(empty_config),
            "GNUPGHOME": str(gnupg_home),
        }
    )

    def _checked(*args: str) -> None:
        completed = run_isolated_git(resolved, *args, env=env)
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise AssertionError(
                f"git {' '.join(args)} failed ({completed.returncode}): {detail}"
            )

    _checked("init", "-q", "-b", "main")
    _checked("config", "user.email", _AUTHOR_EMAIL)
    _checked("config", "user.name", _AUTHOR_NAME)
    _checked("config", "commit.gpgsign", "false")
    (resolved / filename).write_text(content, encoding="utf-8")
    _checked("add", "--", filename)
    _checked("commit", "--no-gpg-sign", "--no-verify", "-qm", message)
    return resolved
