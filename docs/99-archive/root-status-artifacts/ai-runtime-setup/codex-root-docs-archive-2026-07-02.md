# Codex Root Docs Archive 2026-07-02

This note records the retirement of legacy/root Codex and WSL setup documents
from the live repository root and flat `docs/` surface.

## Retired Live Files

| Retired file | Previous role | Canonical successor |
| --- | --- | --- |
| `CODEX_SETUP.txt` | root setup quick reference | `docs/05-operations/tooling/scripts-ops/CODEX_SETUP.md` |
| `CODEX_WSL_SETUP.md` | root WSL setup guide | `docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md` |
| `CODEX_WSL_USAGE.md` | root usage quick start | `scripts/ai/codex/QUICKSTART_WSL.md` |
| `CODEX_WSL_CONFIGURED.md` | root completion/status note | this archive folder |
| `CODEX_SANDBOX_TROUBLESHOOT.txt` | root sandbox troubleshooting note | `docs/05-operations/runbooks/codex-wsl-docker-sandbox-troubleshooting.md` |
| `docs/CODEX_QUICK_START.md` | flat legacy MCP quick start | `docs/05-operations/tooling/scripts-ops/CODEX_SETUP.md` |
| `docs/CODEX_WSL_SETUP.md` | flat legacy WSL setup guide | `docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md` |

## Reason

The retired files were historical setup/status carryovers that no longer
belonged in live root or flat documentation surfaces. Root-governance now keeps
active Codex/WSL guidance under `docs/05-operations/**` and runtime-specific
launcher guidance under `scripts/ai/codex/**`.
