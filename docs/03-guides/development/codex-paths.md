______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-05'

______________________________________________________________________

# Codex Launcher Paths

Reference map for the maintained Codex launchers and support scripts in this
repository. Use this page when updating launcher docs, MCP setup guidance, or
scripts inventory references.

## Primary Launchers

| Surface | Path | Purpose |
| --- | --- | --- |
| WSL shell | `scripts/ops/launchers/codex/codex.sh` | Canonical interactive launcher for WSL/Linux shells. |
| WSL shell exec | `scripts/ops/launchers/codex/codex-exec.sh` | Canonical full-auto launcher for WSL/Linux shells. |
| Windows shell | `scripts/ops/launchers/codex/codex.bat` | Windows launcher that routes into the WSL Codex flow. |
| Windows shell exec | `scripts/ops/launchers/codex/codex-exec.bat` | Windows full-auto launcher that routes into the WSL Codex flow. |
| Windows WSL helper | `scripts/ops/launchers/codex/codex-wsl.bat` | Compatibility WSL launcher retained during launcher consolidation. |

## Legacy And Compatibility Surfaces

| Surface | Path | Purpose |
| --- | --- | --- |
| AI Codex shell entrypoint | `scripts/ai/codex/run-codex.sh` | Older WSL launcher entrypoint retained for compatibility and setup checks. |
| AI Codex PowerShell entrypoint | `scripts/ai/codex/run-codex.ps1` | PowerShell transport for the older AI Codex launcher flow. |
| Implementation helper | `scripts/ai/codex/helper/run-codex-impl.sh` | Final shell executor used by the compatibility launcher flow. |
| Non-interactive helper | `scripts/ai/codex/helper/run-codex-wsl-noninteractive.sh` | Non-interactive WSL wrapper for scripted Codex runs. |
| MCP sync helper | `scripts/ai/codex/helper/ensure-mcp.sh` | Synchronizes workspace and user-level Codex MCP config before launch. |
| MCP setup backend | `scripts/ai/codex/setup_mcp.py` | Canonical Python backend for generated MCP runtime config files. |

## WSL Runtime Support

| Surface | Path | Purpose |
| --- | --- | --- |
| WSL proxy launcher | `scripts/ops/runtime/wsl/start-wsl-proxy.bat` | Starts the Windows-side proxy for WSL network access when needed. |
| WSL proxy server | `scripts/ops/runtime/wsl/wsl_proxy.py` | Minimal proxy implementation used by the WSL launcher flow. |

## Supported Setup Command

Use the repository router for MCP setup:

```bash
python -m scripts.engineering.dev setup-mcp
```

The setup backend writes the tracked workspace MCP files and can update the
user-level Codex config when the caller does not pass `--skip-codex-config`.
Machine-local `.env` files are intentionally out of scope for this guide.

## Related Docs

- `docs/03-guides/development/codex-wsl2-setup.md`
- `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`
- `docs/05-operations/runbooks/codex-wsl-docker-sandbox-troubleshooting.md`
