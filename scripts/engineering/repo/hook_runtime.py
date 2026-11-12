"""Owned Git hook entrypoint; protected guards precede framework and foreign code."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from scripts.engineering.repo import hook_installation as installation
from scripts.engineering.repo.operation_guards import is_env_target
from scripts.engineering.repo.process_deadline import run_owned

DEADLINES = {"pre-commit": 30, "pre-push": 180, "commit-msg": 10}
PHASE_CODES = {"tree": 11, "budgets": 12, "foreign": 13, "framework": 14}
CONTROLLED_REASONS = {
    2: "installation_or_protocol_unqualified",
    11: "full_tree_check_failed",
    12: "debt_guard_failed",
    13: "foreign_callback_failed",
    14: "configured_check_failed",
    20: "check_execution_unavailable",
    21: "env_change_requires_separate_host_authorization",
    22: "required_check_dependency_or_evidence_unavailable",
}


class ProtectedOperation(ValueError):
    """A controlled refusal that cannot be overridden by caller arguments."""


def git_shell() -> str | None:
    """Native Windows Git's shell need not be exported on the desktop PATH."""
    shell = shutil.which("sh")
    if shell is not None:
        return shell
    git = shutil.which("git")
    if os.name == "nt" and git is not None:
        candidate = Path(git).resolve().parent.parent / "bin/sh.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def _push_tips(payload: bytes) -> list[str]:
    tips = []
    for line in payload.decode("utf-8").splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise ValueError("invalid pre-push protocol")
        local, remote = fields[1], fields[3]
        if not all(
            re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha) for sha in (local, remote)
        ):
            raise ValueError("invalid push object identity")
        if set(local) != {"0"}:
            tips.append(local)
    return tips


def _guard_commands(
    repo: Path, kind: str, payload: bytes
) -> list[tuple[str, list[str]]]:
    prefix = [sys.executable, "-I", "-B"]
    modules = Path(__file__).parent
    tips = _push_tips(payload) if kind == "pre-push" else ["HEAD"]
    commands: list[tuple[str, list[str]]] = []
    if kind == "commit-msg":
        return commands
    for tip in tips:
        diff = ["--cached"] if kind == "pre-commit" else ["origin/main", tip]
        paths = installation._git(
            repo,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--name-only",
            "--no-renames",
            "-z",
            *diff,
        )
        if any(is_env_target(path) for path in paths.split("\0") if path):
            raise ProtectedOperation("env changes require explicit host authorization")
        full_tree = [
            str(modules / "check_no_partial_tree.py"),
            "--repo",
            str(repo),
            "--base",
            "origin/main",
            "--tip",
            tip,
        ]
        budgets = [
            str(modules / "budget_guard.py"),
            "--repo-root",
            str(repo),
            "--base",
            "origin/main",
        ]
        if kind == "pre-commit":
            full_tree.append("--check-index")
        else:
            budgets.extend(["--tip", tip])
        commands.extend([("tree", prefix + full_tree), ("budgets", prefix + budgets)])
    return commands


def run(kind: str, hooks: Path, args: list[str], payload: bytes = b"") -> int:
    if kind not in DEADLINES or len(payload) > 8 * 1024 * 1024:
        return 2
    start = time.monotonic()
    try:
        repo = Path(installation._git(Path.cwd(), "rev-parse", "--show-toplevel"))
        _, effective_hooks = installation.locations(repo)
        if effective_hooks != hooks.resolve():
            raise ValueError("hook path no longer effective")
        state = installation._state(hooks)
        if installation.inspect_installation(repo)["status"] != "PASS":
            raise ValueError("installation changed")
        commands = _guard_commands(repo, kind, payload)
        item = state["hooks"][kind]
        if item["chain_foreign"]:
            backup = hooks / item["backup"]
            if installation._hash(installation._read(backup)) != item["backup_sha256"]:
                raise ValueError("foreign callback changed")
            if os.name == "nt":
                shell = git_shell()
                if shell is None:
                    raise ValueError("foreign callback interpreter unavailable")
                foreign = [shell, "-c", 'exec "$0" "$@"', backup.as_posix(), *args]
            else:
                foreign = [str(backup), *args]
            commands.append(("foreign", foreign))
        framework = Path(__file__).with_name("offline_precommit.py")
        commands.append(
            (
                "framework",
                [sys.executable, "-I", "-B", str(framework), kind, str(hooks), *args],
            )
        )
        # Local system hooks use this interpreter explicitly; no silent system fallback.
        env = dict(
            os.environ,
            BIOETL_HOOK_PROJECT_PYTHON=sys.executable,
            PRE_COMMIT_HOME=state["pre_commit_home"],
        )
        for phase, command in commands:
            remaining = DEADLINES[kind] - (time.monotonic() - start)
            if remaining <= 0:
                return 2
            result = run_owned(
                command,
                cwd=repo,
                state_dir=hooks,
                timeout=remaining,
                input_bytes=payload,
                env=env,
            )
            if result.status != "PASS":
                sys.stderr.write(
                    f"BioETL hook {result.status}: {result.reason}; run the scoped check explicitly for details.\n"
                )
                if result.status == "ERROR":
                    return 20
                if phase != "foreign" and result.returncode != 1:
                    return 22
                return PHASE_CODES[phase]
        return 0
    except ProtectedOperation:
        return 21
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        subprocess.SubprocessError,
    ):
        sys.stderr.write(
            "BioETL hook ERROR: protected operation or installation evidence unavailable.\n"
        )
        return 2


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--owned-child":
        if len(args) < 3:
            return 2
        kind = args[1]
        payload = (
            sys.stdin.buffer.read(8 * 1024 * 1024 + 1) if kind == "pre-push" else b""
        )
        return run(kind, Path(args[2]), args[3:], payload)
    if len(args) < 2 or args[0] not in DEADLINES:
        return 2
    # The outer watchdog covers protocol reads, Git discovery and every callback.
    # Child imports only the already verified immutable deployment bundle.
    bundle = Path(__file__).resolve().parents[3]
    entry = (
        "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.engineering.repo.hook_runtime',run_name='__main__')"
    )
    result = run_owned(
        [sys.executable, "-I", "-B", "-c", entry, str(bundle), "--owned-child", *args],
        cwd=Path.cwd(),
        state_dir=Path(args[1]),
        timeout=DEADLINES[args[0]],
        input_stream=sys.stdin.buffer if args[0] == "pre-push" else None,
    )
    if result.status != "PASS":
        reason = (
            CONTROLLED_REASONS.get(result.returncode, result.reason)
            if result.returncode is not None
            else result.reason
        )
        status = "ERROR" if result.returncode in {2, 20, 21, 22} else result.status
        sys.stderr.write(
            f"BioETL hook {status}: {reason}; inspect with hook doctor and scoped checks.\n"
        )
    if result.status == "PASS":
        return 0
    return 2 if result.status == "ERROR" or result.returncode in {2, 20, 21, 22} else 1


if __name__ == "__main__":
    raise SystemExit(main())
