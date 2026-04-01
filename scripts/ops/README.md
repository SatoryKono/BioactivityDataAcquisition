# scripts/ops — Operational & Platform Support

Platform/ops automation, skills/tooling checks, and deployment helpers.

## Unified Entry Point

```bash
python -m scripts.ops --help
python -m scripts.ops <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `salt-rotate` | `scripts/ops/salt_rotate.py` | PII salt rotation (standard and emergency) |
| `fix-grafana` | `scripts/ops/fix_grafana_dashboards.py` | Fix Grafana dashboard configurations |
| `wsl-proxy` | `scripts/ops/wsl_proxy.py` | WSL proxy helper |
| `update-issue` | `scripts/ops/update_github_issue.sh` | Update a GitHub issue title, body, comment, and/or state via the GitHub API, with inline text or file inputs |
| `triage-issues` | `scripts/ops/triage_cleanup_issue_wave.sh` | Apply the cleanup/docs issue triage wave via GitHub API |
| `close-ge-spike` | `scripts/ops/close_great_expectations_spike_issue.sh` | Close issue `#2595` with the completed Great Expectations spike memo |
| `close-schema-drift` | `scripts/ops/close_pandera_schema_drift_issue.sh` | Close issue `#2594` with the completed Pandera schema drift gate summary |
| `setup-agents` | `scripts/ops/setup_agents.sh` | Sync project Codex agents into `CODEX_HOME` |
| `setup-plugins` | `scripts/ops/setup_plugins.sh` | Plugin setup (shell) |
| `setup-skills` | `scripts/ops/setup_skills.sh` | Skills setup (shell, also syncs paired agents by default) |
| `check-skills` | `scripts/ops/check_ai_skills_layout.sh` | Check AI skills layout (shell) |
| `check-mirror` | `scripts/ops/check_skills_mirror.sh` | Check skills mirror sync (shell) |
| `check-mcp` | `scripts/ops/check_mcp.sh` | Check MCP server configuration (shell) |
| `deploy` | `scripts/ops/deploy-bioetl.sh` | Deploy BioETL (shell) |
| `delete-branches` | `scripts/ops/delete-stale-branches.sh` | Delete stale git branches (shell) |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `salt-rotate` | Security rotation cycle; use `--verify` to check state, `--emergency` for immediate rotation after security incident | Manual, periodic security maintenance |
| `fix-grafana` | After Grafana dashboard drift; injects variables and fixes PromQL queries | Manual, infrastructure maintenance |
| `wsl-proxy` | When WSL2 networking needs proxy configuration | Manual, developer utility |
| `update-issue` | When a maintainer needs a reusable shell utility to edit GitHub issues from WSL/bash | Manual, maintainer utility |
| `triage-issues` | When the cleanup/docs GitHub issue wave must be applied from WSL with a PAT | Manual, maintainer utility |
| `close-ge-spike` | When issue `#2595` should be closed after the spike memo is committed or ready for reference | Manual, maintainer utility |
| `close-schema-drift` | When issue `#2594` should be closed after the representative Pandera schema drift gate is merged or ready for reference | Manual, maintainer utility |
| `setup-agents` | After cloning repo or updating `.codex/agents/` profiles | Manual, initial setup |
| `setup-plugins` | After cloning repo or updating local pytest/pre-commit tooling | Manual, initial setup |
| `setup-skills` | After cloning repo or updating skills configuration; keeps `agents/` in sync unless `--skills-only` is passed | Manual, initial setup |
| `check-skills` | Before PR touching `.claude/skills/`; validates layout consistency | CI gate (`skills-consistency.yml`) |
| `check-mirror` | Before PR touching skills; validates mirror sync | CI gate (`skills-consistency.yml`) |
| `check-mcp` | After modifying MCP server configuration | Manual, validation |
| `deploy` | When deploying BioETL to target environment | Manual, deployment |
| `delete-branches` | Periodic repo hygiene; removes stale remote branches | Manual, maintenance |

## Other Files

| File | Description |
|------|-------------|
| `scripts/ops/close_superseded_prs.sh` | Close superseded PRs |
| `scripts/ops/close_duplicate_prs_wave2.sh` | Close duplicate PRs (wave 2) |
| `scripts/ops/close_duplicate_prs_wave3.sh` | Close duplicate PRs (wave 3) |
| `scripts/ops/codex.bat` | Windows Codex launcher |
| `scripts/ops/codex-exec.bat` | Windows Codex exec launcher |
| `scripts/ops/update_github_issue.sh` | Generic issue edit helper for comment/title/body/state updates |
| `scripts/ops/close_great_expectations_spike_issue.sh` | Close issue `#2595` with a standard comment |
| `scripts/ops/close_pandera_schema_drift_issue.sh` | Close issue `#2594` with a standard comment |
| `scripts/ops/start-wsl-proxy.bat` | Start WSL proxy (Windows) |
| `scripts/ops/setup_copilot_codex_mcp.ps1` | PowerShell Copilot/Codex MCP setup |
