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
| `salt-rotate` | `salt_rotate.py` | PII salt rotation (standard and emergency) |
| `fix-grafana` | `fix_grafana_dashboards.py` | Fix Grafana dashboard configurations |
| `wsl-proxy` | `wsl_proxy.py` | WSL proxy helper |
| `setup-plugins` | `setup_plugins.sh` | Plugin setup (shell) |
| `setup-skills` | `setup_skills.sh` | Skills setup (shell) |
| `check-skills` | `check_ai_skills_layout.sh` | Check AI skills layout (shell) |
| `check-mirror` | `check_skills_mirror.sh` | Check skills mirror sync (shell) |
| `check-mcp` | `check_mcp.sh` | Check MCP server configuration (shell) |
| `deploy` | `deploy-bioetl.sh` | Deploy BioETL (shell) |
| `delete-branches` | `delete-stale-branches.sh` | Delete stale git branches (shell) |

## Other Files

| File | Description |
|------|-------------|
| `close_superseded_prs.sh` | Close superseded PRs |
| `close_duplicate_prs_wave2.sh` | Close duplicate PRs (wave 2) |
| `close_duplicate_prs_wave3.sh` | Close duplicate PRs (wave 3) |
| `codex.bat` | Windows Codex launcher |
| `codex-exec.bat` | Windows Codex exec launcher |
| `start-wsl-proxy.bat` | Start WSL proxy (Windows) |
| `setup_copilot_codex_mcp.ps1` | PowerShell Copilot/Codex MCP setup |
