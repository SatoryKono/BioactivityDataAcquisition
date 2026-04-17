#!/usr/bin/env python3
"""Unified entry point for scripts/ops commands.

Usage:
    python -m scripts.ops <command> [args...]
    python -m scripts.ops --help

Stable commands:
    salt-rotate        Rotate PII hashing salt
    fix-grafana        Fix Grafana dashboard configurations
    wsl-proxy          Start WSL proxy helper
    setup-agents       Sync Codex agents into CODEX_HOME
    setup-plugins      Setup plugins (shell)
    setup-skills       Setup skills (shell)
    check-skills       Check AI skills layout (shell)
    check-mirror       Check skills mirror sync (shell)
    deploy             Deploy BioETL (shell)
    delete-branches    Delete stale git branches (shell)

Legacy maintenance commands:
    update-issue       Update a GitHub issue title/body/comment/state (shell)
    triage-issues      Triage cleanup/docs issue wave (shell)
    close-ge-spike     Close issue #2595 with the completed spike memo (shell)
    close-schema-drift Close issue #2594 with the completed Pandera drift gate (shell)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "salt-rotate": "salt_rotate.py",
    "fix-grafana": "fix_grafana_dashboards.py",
    "wsl-proxy": "wsl_proxy.py",
}

SHELL_COMMANDS: dict[str, str] = {
    "update-issue": "maintenance/update_github_issue.sh",
    "triage-issues": "maintenance/triage_cleanup_issue_wave.sh",
    "close-ge-spike": "maintenance/close_great_expectations_spike_issue.sh",
    "close-schema-drift": "maintenance/close_pandera_schema_drift_issue.sh",
    "setup-agents": "setup_agents.sh",
    "setup-plugins": "setup_plugins.sh",
    "setup-skills": "setup_skills.sh",
    "check-skills": "check_ai_skills_layout.sh",
    "check-mirror": "check_skills_mirror.sh",
    "deploy": "deploy-bioetl.sh",
    "delete-branches": "delete-stale-branches.sh",
}

_DIR = Path(__file__).parent


def _run_script(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run([sys.executable, str(script), *argv], check=False)
    return result.returncode


def _run_shell(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run(["bash", str(script), *argv], check=False)
    return result.returncode


def _print_help() -> None:
    print(__doc__ or "", end="")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]

    if cmd in COMMANDS:
        return _run_script(COMMANDS[cmd], rest)

    if cmd in SHELL_COMMANDS:
        return _run_shell(SHELL_COMMANDS[cmd], rest)

    all_cmds = sorted([*COMMANDS, *SHELL_COMMANDS])
    print(f"Unknown command: {cmd}", file=sys.stderr)
    print(f"Available: {', '.join(all_cmds)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
