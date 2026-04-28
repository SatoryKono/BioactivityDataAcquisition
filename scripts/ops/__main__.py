#!/usr/bin/env python3
"""Unified entry point for scripts/ops commands.

Usage:
    python -m scripts.ops <command> [args...]
    python -m scripts.ops --help

Stable commands:
    salt-rotate        Rotate PII hashing salt
    fix-grafana        Fix Grafana dashboard configurations
    rerender-grafana   Rerender Grafana dashboard screenshots
    wsl-proxy          Start WSL proxy helper
    codex              Launch Codex interactive mode (shell)
    codex-exec         Launch Codex full-auto mode (shell)
    codex-headless     Launch Codex without MCP servers (shell)
    diagnose-codex-wsl Run Codex WSL diagnostic checks (shell)
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

from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    python_command,
    shell_command,
)

COMMAND_SPECS = {
    "salt-rotate": "maintenance/security/salt_rotate.py",
    "fix-grafana": "observability/grafana/fix_grafana_dashboards.py",
    "rerender-grafana": "observability/grafana/rerender_grafana_screenshots.py",
    "wsl-proxy": "runtime/wsl/wsl_proxy.py",
}
COMMAND_SPECS = {name: python_command(script) for name, script in COMMAND_SPECS.items()}

SHELL_COMMAND_SPECS = {
    "update-issue": "maintenance/github/update_github_issue.sh",
    "triage-issues": "maintenance/github/triage_cleanup_issue_wave.sh",
    "close-ge-spike": "maintenance/github/close_great_expectations_spike_issue.sh",
    "close-schema-drift": "maintenance/github/close_pandera_schema_drift_issue.sh",
    "codex": "launchers/codex/codex.sh",
    "codex-exec": "launchers/codex/codex-exec.sh",
    "codex-headless": "../ai/codex/headless.sh",
    "diagnose-codex-wsl": "../ai/codex/diagnose_wsl.sh",
    "setup-agents": "../ai/codex/setup_agents.sh",
    "setup-plugins": "launchers/codex/setup_plugins.sh",
    "setup-skills": "../ai/codex/setup_skills.sh",
    "check-skills": "support/skills/check_ai_skills_layout.sh",
    "check-mirror": "support/skills/check_skills_mirror.sh",
    "deploy": "runtime/deploy/deploy-bioetl.sh",
    "delete-branches": "maintenance/git/delete-stale-branches.sh",
}
SHELL_COMMAND_SPECS = {
    name: shell_command(script) for name, script in SHELL_COMMAND_SPECS.items()
}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands={**COMMAND_SPECS, **SHELL_COMMAND_SPECS},
        base_dir=_DIR,
        sort_available=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
