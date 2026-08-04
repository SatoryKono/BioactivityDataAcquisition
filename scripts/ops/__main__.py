#!/usr/bin/env python3
"""Unified entry point for scripts/ops commands.

Usage:
    python -m scripts.ops <command> [args...]
    python -m scripts.ops --help

Stable commands:
    salt-rotate        Rotate PII hashing salt
    check-observability-ports
                       Compare published observability endpoints with container health
    rerender-grafana   Rerender Grafana dashboard screenshots
    render-grafana-matrix
                       Render the standard, full-page, kiosk, and repeat matrix
    audit-live-grafana Run reviewed live Grafana datasource/frame audit
    check-grafana-audit-preflight
                       Check local stack readiness for a full Grafana dashboard audit
    check-bioetl-prometheus-scrape
                       Fail-closed smoke: BioETL Prometheus scrape target must be UP
    ensure-quarantine-explorer
                       REMOVED stub (exit 2): Quarantine Explorer UI no longer shipped
    run-grafana-audit-cycle
                       Run preflight, screenshot refresh, and live Grafana audit
    wsl-proxy          Start WSL proxy helper
    codex              Launch Codex via repo-local bootstrap adapter (shell)
    codex-exec         Launch Codex full-auto via repo-local bootstrap adapter (shell)
    codex-headless     Launch Codex without MCP servers (canonical shell)
    diagnose-codex-wsl Run Codex WSL diagnostics (canonical shell)
    setup-agents       Sync Codex agents (canonical shell)
    setup-plugins      Setup plugins via ops bootstrap helper (shell)
    setup-skills       Sync Codex skills (canonical shell)
    check-skills       Check AI skills layout (shell)
    check-mirror       Check skills mirror sync (shell)
    deploy             Deploy BioETL (shell)
"""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    python_command,
    shell_command,
)

_PYTHON_COMMAND_PATHS = {
    "salt-rotate": "maintenance/security/salt_rotate.py",
    "check-observability-ports": "observability/check_published_observability_endpoints.py",
    "rerender-grafana": "observability/grafana/rerender_grafana_screenshots.py",
    "render-grafana-matrix": ("observability/grafana/run_grafana_render_matrix.py"),
    "audit-live-grafana": "observability/grafana/audit_live_grafana_panels.py",
    "check-grafana-audit-preflight": (
        "observability/grafana/check_grafana_dashboard_audit_preflight.py"
    ),
    "check-bioetl-prometheus-scrape": (
        "observability/check_bioetl_prometheus_scrape.py"
    ),
    "ensure-quarantine-explorer": (
        "observability/grafana/ensure_quarantine_explorer.py"
    ),
    "run-grafana-audit-cycle": (
        "observability/grafana/run_grafana_dashboard_audit_cycle.py"
    ),
    "wsl-proxy": "runtime/wsl/wsl_proxy.py",
}
COMMAND_SPECS = {
    name: python_command(script) for name, script in _PYTHON_COMMAND_PATHS.items()
}

_SHELL_COMMAND_PATHS = {
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
}
SHELL_COMMAND_SPECS = {
    name: shell_command(script) for name, script in _SHELL_COMMAND_PATHS.items()
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
